"""AI routes — summarisation, chat-with-PDF, resume analysis, study notes."""

import os
import time
from functools import wraps
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from config import Config
from services.file_service import save_upload, allowed_file
from services.pdf_service import extract_text
from ai_modules.summarizer import generate_summary
from ai_modules.chat_engine import chat_with_pdf
from ai_modules.resume_analyzer import analyze_resume
from ai_modules.flashcard_engine import generate_flashcards
from ai_modules.exceptions import GeminiAPIError
from database.models import (
    get_file_by_id,
    save_history,
    save_chat,
    get_chat_by_file,
    update_chat_messages,
)

ai_bp = Blueprint('ai', __name__)

# Simple in-memory per-user rate limit: 20 requests / hour per user
USER_RATE_LIMITS = {}

def rate_limit_ai(limit=50, period=3600):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            try:
                user_id = get_jwt_identity()
            except Exception:
                user_id = None
            if not user_id:
                return f(*args, **kwargs)
            
            rate_key = (user_id, f.__name__)
            now = time.time()
            timestamps = USER_RATE_LIMITS.setdefault(rate_key, [])
            timestamps[:] = [t for t in timestamps if now - t < period]
            
            if len(timestamps) >= limit:
                return jsonify({
                    'error': f'Rate limit exceeded. Maximum {limit} requests per hour for this specific AI tool. Please wait before trying this tool again.'
                }), 429
                
            timestamps.append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator

UPLOAD_FOLDER = Config.UPLOAD_FOLDER


def _ensure_upload_dir():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def _get_pdf_text(file=None, file_id=None) -> tuple[str, str | None]:
    """Extract text from either an uploaded file or an existing file_id.
    Automatically falls back to OCR if standard text extraction yields nothing (scanned PDFs).
    """
    file_path = None
    
    if file is not None and file.filename:
        if not allowed_file(file.filename, {'pdf'}):
            return '', 'Only PDF files are allowed'
        info = save_upload(file, UPLOAD_FOLDER)
        file_path = info['file_path']
    elif file_id:
        record = get_file_by_id(file_id)
        if record is None:
            return '', 'File not found'
        path = record.get('file_path', '')
        if not os.path.isfile(path):
            return '', 'File no longer exists on disk'
        file_path = path

    if not file_path:
        return '', 'No file or file_id provided'

    # Try standard digital text extraction first
    text = extract_text(file_path)
    
    # If the text is empty or very short, it's likely a scanned PDF image! Fallback to Tesseract OCR!
    if len(text.strip()) < 20:
        print(f"[AI Routes] Standard text extraction yielded too little text ({len(text.strip())} chars). Trying OCR fallback...")
        from ai_modules.ocr_engine import extract_text_from_pdf_image
        ocr_text = extract_text_from_pdf_image(file_path)
        if ocr_text and not ocr_text.startswith('[OCR unavailable]') and not ocr_text.startswith('OCR extraction failed'):
            text = ocr_text
            
    return text, None


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@ai_bp.route('/summary', methods=['POST'])
@jwt_required()
@rate_limit_ai()
def summary():
    """Generate a summary of a PDF file."""
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()

        file = request.files.get('file')
        file_id = request.form.get('file_id', '')
        mode = request.form.get('mode', 'brief')

        if mode not in ('brief', 'detailed', 'bullets', 'exam_notes'):
            mode = 'brief'

        text, error = _get_pdf_text(file=file, file_id=file_id)
        if error:
            return jsonify({'error': error}), 400

        if not text.strip():
            return jsonify({
                'error': 'No text could be extracted from this PDF. It may be a scanned document — try OCR first.',
            }), 400

        result = generate_summary(text, mode=mode)

        save_history(user_id, file_id or '', 'summary', 'success',
                     {'mode': mode, 'word_count': result.get('word_count', 0)})

        return jsonify({
            'message': 'Summary generated',
            'result': result,
        }), 200

    except GeminiAPIError as e:
        return jsonify({'error': e.message, 'error_type': e.error_type}), e.status_code
    except Exception as e:
        return jsonify({'error': f'Summary generation failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Chat with PDF
# ---------------------------------------------------------------------------

@ai_bp.route('/chat', methods=['POST'])
@jwt_required()
@rate_limit_ai()
def chat():
    """Chat / ask questions about a PDF document."""
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()

        data = request.get_json(silent=True)
        if not data:
            # Try form data as fallback
            data = {
                'file_id': request.form.get('file_id', ''),
                'question': request.form.get('question', ''),
            }

        file_id = data.get('file_id', '')
        question = (data.get('question') or '').strip()

        if not question:
            return jsonify({'error': 'A question is required'}), 400

        if not file_id:
            return jsonify({'error': 'file_id is required'}), 400

        text, error = _get_pdf_text(file_id=file_id)
        if error:
            return jsonify({'error': error}), 400

        if not text.strip():
            return jsonify({
                'error': 'No text could be extracted from this PDF.',
            }), 400

        # Load existing chat history
        existing_chat = get_chat_by_file(user_id, file_id)
        chat_history = existing_chat['messages'] if existing_chat else []

        # Get AI response
        answer = chat_with_pdf(text, question, chat_history=chat_history)

        # Update chat history
        new_messages = chat_history + [
            {'role': 'user', 'content': question},
            {'role': 'assistant', 'content': answer},
        ]

        if existing_chat:
            update_chat_messages(str(existing_chat['_id']), new_messages)
            chat_id = str(existing_chat['_id'])
        else:
            chat_doc = save_chat(user_id, file_id, new_messages)
            chat_id = str(chat_doc['_id']) if chat_doc else None

        save_history(user_id, file_id, 'chat', 'success', {'question': question[:200]})

        return jsonify({
            'message': 'Response generated',
            'answer': answer,
            'chat_id': chat_id,
        }), 200

    except GeminiAPIError as e:
        return jsonify({'error': e.message, 'error_type': e.error_type}), e.status_code
    except Exception as e:
        return jsonify({'error': f'Chat failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Resume analysis
# ---------------------------------------------------------------------------

@ai_bp.route('/resume-analyze', methods=['POST'])
@jwt_required()
@rate_limit_ai()
def resume_analyze():
    """Analyze a resume PDF for ATS compatibility."""
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()

        if 'file' not in request.files:
            return jsonify({'error': 'No resume PDF provided'}), 400

        file = request.files['file']
        target_role = request.form.get('target_role', '')

        text, error = _get_pdf_text(file=file)
        if error:
            return jsonify({'error': error}), 400

        if not text.strip():
            return jsonify({
                'error': 'No text could be extracted from this resume.',
            }), 400

        analysis = analyze_resume(text, target_role=target_role)

        save_history(user_id, '', 'resume_analyze', 'success',
                     {'ats_score': analysis.get('ats_score', 0)})

        return jsonify({
            'message': 'Resume analysis complete',
            'result': analysis,
        }), 200

    except GeminiAPIError as e:
        return jsonify({'error': e.message, 'error_type': e.error_type}), e.status_code
    except Exception as e:
        return jsonify({'error': f'Resume analysis failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Study notes
# ---------------------------------------------------------------------------

@ai_bp.route('/notes', methods=['POST'])
@jwt_required()
@rate_limit_ai()
def notes():
    """Generate study / exam notes from a PDF."""
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()

        file = request.files.get('file')
        file_id = request.form.get('file_id', '')

        text, error = _get_pdf_text(file=file, file_id=file_id)
        if error:
            return jsonify({'error': error}), 400

        if not text.strip():
            return jsonify({
                'error': 'No text could be extracted from this PDF.',
            }), 400

        result = generate_summary(text, mode='exam_notes')

        save_history(user_id, file_id or '', 'notes', 'success',
                     {'word_count': result.get('word_count', 0)})

        return jsonify({
            'message': 'Study notes generated',
            'result': result,
        }), 200

    except GeminiAPIError as e:
        return jsonify({'error': e.message, 'error_type': e.error_type}), e.status_code
    except Exception as e:
        return jsonify({'error': f'Notes generation failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Flashcards
# ---------------------------------------------------------------------------

@ai_bp.route('/flashcards', methods=['POST'])
@jwt_required()
@rate_limit_ai()
def flashcards():
    """Generate study flashcards from a PDF."""
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()

        file = request.files.get('file')
        file_id = request.form.get('file_id', '')

        text, error = _get_pdf_text(file=file, file_id=file_id)
        if error:
            return jsonify({'error': error}), 400

        if not text.strip():
            return jsonify({
                'error': 'No text could be extracted from this PDF.',
            }), 400

        cards = generate_flashcards(text)

        save_history(user_id, file_id or '', 'flashcards', 'success',
                     {'card_count': len(cards)})

        return jsonify({
            'message': 'Flashcards generated successfully',
            'cards': cards,
        }), 200

    except GeminiAPIError as e:
        return jsonify({'error': e.message, 'error_type': e.error_type}), e.status_code
    except Exception as e:
        return jsonify({'error': f'Flashcard generation failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------

@ai_bp.route('/chat-history/<file_id>', methods=['GET'])
@jwt_required()
def chat_history(file_id):
    """Return chat messages for a given file."""
    try:
        user_id = get_jwt_identity()
        chat = get_chat_by_file(user_id, file_id)

        if chat is None:
            return jsonify({
                'messages': [],
                'chat_id': None,
            }), 200

        return jsonify({
            'messages': chat.get('messages', []),
            'chat_id': str(chat['_id']),
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch chat history: {str(e)}'}), 500


# ═══════════════════════════════════════════════════════════════════
# PHASE 6 — AI Tools (writing, QA, quiz, business, student)
# ═══════════════════════════════════════════════════════════════════

from ai_modules.ai_engines import (
    explain_pdf, answer_question, extract_keywords,
    generate_quiz, generate_mcq,
    check_grammar, improve_writing, translate_text, rewrite_text,
    change_tone, proofread,
    analyze_contract, read_invoice, analyze_financial, review_legal,
    assignment_helper, research_assistant, cite_sources,
    generate_cover_letter, generate_interview_questions,
)


def _p6_route(action_fn, action_name, extra_args=None):
    """Shared handler for simple PDF-text → AI-result routes."""
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()
        
        # In-memory per-user rate limit check (20 requests / hour per user)
        now = time.time()
        timestamps = USER_RATE_LIMITS.setdefault(user_id, [])
        timestamps[:] = [t for t in timestamps if now - t < 3600]
        if len(timestamps) >= 20:
            return jsonify({'error': 'Rate limit exceeded. Maximum 20 requests per hour for AI features.'}), 429
        timestamps.append(now)

        file    = request.files.get('file')
        file_id = request.form.get('file_id', '')
        text, error = _get_pdf_text(file=file, file_id=file_id)
        if error:
            return jsonify({'error': error}), 400
        if not text.strip():
            return jsonify({'error': 'No text could be extracted from this PDF.'}), 400
        kwargs = extra_args() if extra_args else {}
        result = action_fn(text, **kwargs)
        save_history(user_id, file_id or '', action_name, 'success', {})
        return jsonify({'message': f'{action_name} complete', 'result': result}), 200
    except GeminiAPIError as e:
        return jsonify({'error': e.message, 'error_type': e.error_type}), e.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/explain', methods=['POST'])
@jwt_required()
def route_explain():
    return _p6_route(explain_pdf, 'explain')


@ai_bp.route('/answer-question', methods=['POST'])
@jwt_required()
@rate_limit_ai()
def route_answer_question():
    try:
        _ensure_upload_dir()
        user_id  = get_jwt_identity()
        question = request.form.get('question', '').strip()
        if not question:
            return jsonify({'error': 'question is required'}), 400
        file    = request.files.get('file')
        file_id = request.form.get('file_id', '')
        text, error = _get_pdf_text(file=file, file_id=file_id)
        if error:
            return jsonify({'error': error}), 400
        result = answer_question(text, question)
        save_history(user_id, file_id or '', 'answer_question', 'success', {'q': question[:100]})
        return jsonify({'message': 'Question answered', 'result': result}), 200
    except GeminiAPIError as e:
        return jsonify({'error': e.message, 'error_type': e.error_type}), e.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/keywords', methods=['POST'])
@jwt_required()
def route_keywords():
    return _p6_route(extract_keywords, 'keywords')


@ai_bp.route('/quiz', methods=['POST'])
@jwt_required()
def route_quiz():
    return _p6_route(generate_quiz, 'quiz',
                     extra_args=lambda: {'count': int(request.form.get('count', 10))})


@ai_bp.route('/mcq', methods=['POST'])
@jwt_required()
def route_mcq():
    return _p6_route(generate_mcq, 'mcq',
                     extra_args=lambda: {'count': int(request.form.get('count', 10))})


@ai_bp.route('/check-grammar', methods=['POST'])
@jwt_required()
@rate_limit_ai()
def route_check_grammar():
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()
        # Accept either a PDF or raw text
        raw_text = request.form.get('text', '')
        if raw_text:
            text = raw_text
        else:
            file    = request.files.get('file')
            file_id = request.form.get('file_id', '')
            text, error = _get_pdf_text(file=file, file_id=file_id)
            if error:
                return jsonify({'error': error}), 400
        result = check_grammar(text)
        save_history(user_id, '', 'check_grammar', 'success', {})
        return jsonify({'message': 'Grammar checked', 'result': result}), 200
    except GeminiAPIError as e:
        return jsonify({'error': e.message, 'error_type': e.error_type}), e.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/improve-writing', methods=['POST'])
@jwt_required()
@rate_limit_ai()
def route_improve_writing():
    try:
        _ensure_upload_dir()
        user_id  = get_jwt_identity()
        raw_text = request.form.get('text', '')
        if raw_text:
            text = raw_text
        else:
            file    = request.files.get('file')
            file_id = request.form.get('file_id', '')
            text, error = _get_pdf_text(file=file, file_id=file_id)
            if error:
                return jsonify({'error': error}), 400
        result = improve_writing(text)
        save_history(user_id, '', 'improve_writing', 'success', {})
        return jsonify({'message': 'Writing improved', 'result': result}), 200
    except GeminiAPIError as e:
        return jsonify({'error': e.message, 'error_type': e.error_type}), e.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/translate', methods=['POST'])
@jwt_required()
@rate_limit_ai()
def route_translate():
    try:
        _ensure_upload_dir()
        user_id     = get_jwt_identity()
        target_lang = request.form.get('lang', 'Spanish')
        raw_text    = request.form.get('text', '')
        if raw_text:
            text = raw_text
        else:
            file    = request.files.get('file')
            file_id = request.form.get('file_id', '')
            text, error = _get_pdf_text(file=file, file_id=file_id)
            if error:
                return jsonify({'error': error}), 400
        result = translate_text(text, target_lang)
        save_history(user_id, '', 'translate', 'success', {'lang': target_lang})
        return jsonify({'message': f'Translated to {target_lang}', 'result': result}), 200
    except GeminiAPIError as e:
        return jsonify({'error': e.message, 'error_type': e.error_type}), e.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/rewrite', methods=['POST'])
@jwt_required()
@rate_limit_ai()
def route_rewrite():
    try:
        _ensure_upload_dir()
        user_id  = get_jwt_identity()
        style    = request.form.get('style', 'formal')
        raw_text = request.form.get('text', '')
        if raw_text:
            text = raw_text
        else:
            file    = request.files.get('file')
            file_id = request.form.get('file_id', '')
            text, error = _get_pdf_text(file=file, file_id=file_id)
            if error:
                return jsonify({'error': error}), 400
        result = rewrite_text(text, style)
        save_history(user_id, '', 'rewrite', 'success', {'style': style})
        return jsonify({'message': 'Rewritten', 'result': result}), 200
    except GeminiAPIError as e:
        return jsonify({'error': e.message, 'error_type': e.error_type}), e.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/change-tone', methods=['POST'])
@jwt_required()
@rate_limit_ai()
def route_change_tone():
    try:
        _ensure_upload_dir()
        user_id  = get_jwt_identity()
        tone     = request.form.get('tone', 'professional')
        raw_text = request.form.get('text', '')
        if raw_text:
            text = raw_text
        else:
            file    = request.files.get('file')
            file_id = request.form.get('file_id', '')
            text, error = _get_pdf_text(file=file, file_id=file_id)
            if error:
                return jsonify({'error': error}), 400
        result = change_tone(text, tone)
        save_history(user_id, '', 'change_tone', 'success', {'tone': tone})
        return jsonify({'message': 'Tone changed', 'result': result}), 200
    except GeminiAPIError as e:
        return jsonify({'error': e.message, 'error_type': e.error_type}), e.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/proofread', methods=['POST'])
@jwt_required()
@rate_limit_ai()
def route_proofread():
    try:
        _ensure_upload_dir()
        user_id  = get_jwt_identity()
        raw_text = request.form.get('text', '')
        if raw_text:
            text = raw_text
        else:
            file    = request.files.get('file')
            file_id = request.form.get('file_id', '')
            text, error = _get_pdf_text(file=file, file_id=file_id)
            if error:
                return jsonify({'error': error}), 400
        result = proofread(text)
        save_history(user_id, '', 'proofread', 'success', {})
        return jsonify({'message': 'Proofreading complete', 'result': result}), 200
    except GeminiAPIError as e:
        return jsonify({'error': e.message, 'error_type': e.error_type}), e.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/analyze-contract', methods=['POST'])
@jwt_required()
def route_analyze_contract():
    return _p6_route(analyze_contract, 'analyze_contract')


@ai_bp.route('/read-invoice', methods=['POST'])
@jwt_required()
def route_read_invoice():
    return _p6_route(read_invoice, 'read_invoice')


@ai_bp.route('/analyze-financial', methods=['POST'])
@jwt_required()
def route_analyze_financial():
    return _p6_route(analyze_financial, 'analyze_financial')


@ai_bp.route('/review-legal', methods=['POST'])
@jwt_required()
def route_review_legal():
    return _p6_route(review_legal, 'review_legal')


@ai_bp.route('/assignment-helper', methods=['POST'])
@jwt_required()
@rate_limit_ai()
def route_assignment_helper():
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()
        task    = request.form.get('task', '').strip()
        file    = request.files.get('file')
        file_id = request.form.get('file_id', '')
        text, error = _get_pdf_text(file=file, file_id=file_id)
        if error:
            return jsonify({'error': error}), 400
        result = assignment_helper(text, task)
        save_history(user_id, file_id or '', 'assignment_helper', 'success', {'task': task[:100]})
        return jsonify({'message': 'Assignment help ready', 'result': result}), 200
    except GeminiAPIError as e:
        return jsonify({'error': e.message, 'error_type': e.error_type}), e.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/research-assistant', methods=['POST'])
@jwt_required()
@rate_limit_ai()
def route_research_assistant():
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()
        topic   = request.form.get('topic', '')
        file    = request.files.get('file')
        file_id = request.form.get('file_id', '')
        text, error = _get_pdf_text(file=file, file_id=file_id)
        if error:
            return jsonify({'error': error}), 400
        result = research_assistant(text, topic)
        save_history(user_id, file_id or '', 'research_assistant', 'success', {'topic': topic[:100]})
        return jsonify({'message': 'Research summary ready', 'result': result}), 200
    except GeminiAPIError as e:
        return jsonify({'error': e.message, 'error_type': e.error_type}), e.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/cite-sources', methods=['POST'])
@jwt_required()
@rate_limit_ai()
def route_cite_sources():
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()
        style   = request.form.get('style', 'APA')
        file    = request.files.get('file')
        file_id = request.form.get('file_id', '')
        text, error = _get_pdf_text(file=file, file_id=file_id)
        if error:
            return jsonify({'error': error}), 400
        result = cite_sources(text, style)
        save_history(user_id, file_id or '', 'cite_sources', 'success', {'style': style})
        return jsonify({'message': f'Citations formatted ({style})', 'result': result}), 200
    except GeminiAPIError as e:
        return jsonify({'error': e.message, 'error_type': e.error_type}), e.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/cover-letter', methods=['POST'])
@jwt_required()
@rate_limit_ai()
def route_cover_letter():
    try:
        _ensure_upload_dir()
        user_id     = get_jwt_identity()
        job_desc    = request.form.get('job_description', '')
        file        = request.files.get('file')
        file_id     = request.form.get('file_id', '')
        text, error = _get_pdf_text(file=file, file_id=file_id)
        if error:
            return jsonify({'error': error}), 400
        result = generate_cover_letter(text, job_desc)
        save_history(user_id, file_id or '', 'cover_letter', 'success', {})
        return jsonify({'message': 'Cover letter generated', 'result': result}), 200
    except GeminiAPIError as e:
        return jsonify({'error': e.message, 'error_type': e.error_type}), e.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/interview-questions', methods=['POST'])
@jwt_required()
def route_interview_questions():
    return _p6_route(generate_interview_questions, 'interview_questions')

