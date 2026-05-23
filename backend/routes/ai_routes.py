"""AI routes — summarisation, chat-with-PDF, resume analysis, study notes."""

import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from config import Config
from services.file_service import save_upload, allowed_file
from services.pdf_service import extract_text
from ai_modules.summarizer import generate_summary
from ai_modules.chat_engine import chat_with_pdf
from ai_modules.resume_analyzer import analyze_resume
from ai_modules.flashcard_engine import generate_flashcards
from database.models import (
    get_file_by_id,
    save_history,
    save_chat,
    get_chat_by_file,
    update_chat_messages,
)

ai_bp = Blueprint('ai', __name__)

UPLOAD_FOLDER = Config.UPLOAD_FOLDER


def _ensure_upload_dir():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def _get_pdf_text(file=None, file_id=None) -> tuple[str, str | None]:
    """Extract text from either an uploaded file or an existing file_id.

    Returns ``(text, error_message)``.
    """
    if file is not None and file.filename:
        if not allowed_file(file.filename, {'pdf'}):
            return '', 'Only PDF files are allowed'
        info = save_upload(file, UPLOAD_FOLDER)
        text = extract_text(info['file_path'])
        return text, None

    if file_id:
        record = get_file_by_id(file_id)
        if record is None:
            return '', 'File not found'
        file_path = record.get('file_path', '')
        if not os.path.isfile(file_path):
            return '', 'File no longer exists on disk'
        text = extract_text(file_path)
        return text, None

    return '', 'No file or file_id provided'


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@ai_bp.route('/summary', methods=['POST'])
@jwt_required()
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

    except Exception as e:
        return jsonify({'error': f'Summary generation failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Chat with PDF
# ---------------------------------------------------------------------------

@ai_bp.route('/chat', methods=['POST'])
@jwt_required()
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

    except Exception as e:
        return jsonify({'error': f'Chat failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Resume analysis
# ---------------------------------------------------------------------------

@ai_bp.route('/resume-analyze', methods=['POST'])
@jwt_required()
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

    except Exception as e:
        return jsonify({'error': f'Resume analysis failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Study notes
# ---------------------------------------------------------------------------

@ai_bp.route('/notes', methods=['POST'])
@jwt_required()
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

    except Exception as e:
        return jsonify({'error': f'Notes generation failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Flashcards
# ---------------------------------------------------------------------------

@ai_bp.route('/flashcards', methods=['POST'])
@jwt_required()
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
