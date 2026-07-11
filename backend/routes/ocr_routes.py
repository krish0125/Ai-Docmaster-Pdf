"""OCR routes — extract text from images and scanned PDFs."""

import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from config import Config
from services.file_service import save_upload, allowed_file
from ai_modules.ocr_engine import extract_text_from_image, extract_text_from_pdf_image
from database.models import save_history

ocr_bp = Blueprint('ocr', __name__)

UPLOAD_FOLDER = Config.UPLOAD_FOLDER
IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}


def _ensure_upload_dir():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------------------------------------------------------------------
# Single image OCR
# ---------------------------------------------------------------------------

@ocr_bp.route('/extract', methods=['POST'])
@jwt_required()
def extract():
    """Extract text from a single image using OCR."""
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()

        if 'file' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename, IMAGE_EXTENSIONS):
            return jsonify({
                'error': 'Invalid file type. Supported: PNG, JPG, JPEG, GIF, BMP, TIFF',
            }), 400

        file_info = save_upload(file, UPLOAD_FOLDER)
        result = extract_text_from_image(file_info['file_path'])

        save_history(user_id, '', 'ocr_extract', 'success',
                     {'original_name': file_info['original_name'],
                      'word_count': result.get('word_count', 0)})

        return jsonify({
            'message': 'Text extracted successfully',
            'result': result,
        }), 200

    except Exception as e:
        return jsonify({'error': f'OCR extraction failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Batch image OCR
# ---------------------------------------------------------------------------

@ocr_bp.route('/batch', methods=['POST'])
@jwt_required()
def batch_extract():
    """Extract text from multiple images."""
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()

        if 'files' not in request.files:
            return jsonify({'error': 'No image files provided'}), 400

        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files selected'}), 400

        results = []
        for file in files:
            if not allowed_file(file.filename, IMAGE_EXTENSIONS):
                results.append({
                    'filename': file.filename,
                    'error': 'Unsupported file type',
                    'text': '',
                    'confidence': 0,
                    'word_count': 0,
                })
                continue

            file_info = save_upload(file, UPLOAD_FOLDER)
            result = extract_text_from_image(file_info['file_path'])
            result['filename'] = file_info['original_name']
            results.append(result)

        total_words = sum(r.get('word_count', 0) for r in results)
        save_history(user_id, '', 'ocr_batch', 'success',
                     {'file_count': len(files), 'total_words': total_words})

        return jsonify({
            'message': f'Processed {len(results)} images',
            'results': results,
            'total_word_count': total_words,
        }), 200

    except Exception as e:
        return jsonify({'error': f'Batch OCR failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Scanned PDF OCR
# ---------------------------------------------------------------------------

@ocr_bp.route('/pdf-ocr', methods=['POST'])
@jwt_required()
def pdf_ocr():
    """Extract text from a scanned PDF (image-based pages)."""
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()

        if 'file' not in request.files:
            return jsonify({'error': 'No PDF file provided'}), 400

        file = request.files['file']
        if not allowed_file(file.filename, {'pdf'}):
            return jsonify({'error': 'Only PDF files are allowed'}), 400

        file_info = save_upload(file, UPLOAD_FOLDER)
        extracted_text = extract_text_from_pdf_image(file_info['file_path'])

        word_count = len(extracted_text.split()) if extracted_text else 0

        save_history(user_id, '', 'pdf_ocr', 'success',
                     {'original_name': file_info['original_name'],
                      'word_count': word_count})

        return jsonify({
            'message': 'PDF OCR completed',
            'result': {
                'text': extracted_text,
                'word_count': word_count,
                'filename': file_info['original_name'],
            },
        }), 200

    except Exception as e:
        return jsonify({'error': f'PDF OCR failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Phase 5 — Handwriting OCR (Gemini vision)
# ---------------------------------------------------------------------------

@ocr_bp.route('/handwriting', methods=['POST'])
@jwt_required()
def handwriting():
    """Transcribe handwritten text from an image using Gemini vision."""
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()
        if 'file' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        file = request.files['file']
        if not allowed_file(file.filename, IMAGE_EXTENSIONS):
            return jsonify({'error': 'Image files only (PNG, JPG, etc.)'}), 400

        from ai_modules.ocr_engine import handwriting_ocr
        file_info = save_upload(file, UPLOAD_FOLDER)
        result    = handwriting_ocr(file_info['file_path'])
        save_history(user_id, '', 'handwriting_ocr', 'success',
                     {'word_count': result.get('word_count', 0)})
        return jsonify({'message': 'Handwriting transcribed', 'result': result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Phase 5 — Extract Tables from PDF
# ---------------------------------------------------------------------------

@ocr_bp.route('/extract-tables', methods=['POST'])
@jwt_required()
def extract_tables():
    """Extract all tables from a PDF into a structured JSON response."""
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()
        if 'file' not in request.files:
            return jsonify({'error': 'No PDF file provided'}), 400
        file = request.files['file']
        if not allowed_file(file.filename, {'pdf'}):
            return jsonify({'error': 'Only PDF files allowed'}), 400

        from ai_modules.ocr_engine import extract_tables_from_pdf
        file_info = save_upload(file, UPLOAD_FOLDER)
        tables    = extract_tables_from_pdf(file_info['file_path'])
        save_history(user_id, '', 'extract_tables', 'success',
                     {'table_count': len(tables)})
        return jsonify({'message': f'{len(tables)} table(s) found', 'tables': tables}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ---------------------------------------------------------------------------
# Phase 5 — Extract Images from PDF
# ---------------------------------------------------------------------------

@ocr_bp.route('/extract-images', methods=['POST'])
@jwt_required()
def extract_images():
    """Extract all embedded images from a PDF."""
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()
        if 'file' not in request.files:
            return jsonify({'error': 'No PDF file provided'}), 400
        file = request.files['file']
        if not allowed_file(file.filename, {'pdf'}):
            return jsonify({'error': 'Only PDF files allowed'}), 400

        from ai_modules.ocr_engine import extract_images_from_pdf
        file_info = save_upload(file, UPLOAD_FOLDER)
        images    = extract_images_from_pdf(file_info['file_path'], UPLOAD_FOLDER)

        # Build download URLs
        for img in images:
            if 'filename' in img:
                img['download_url'] = f'/ocr/download/{img["filename"]}'

        save_history(user_id, '', 'extract_images', 'success',
                     {'image_count': len(images)})
        return jsonify({'message': f'{len(images)} image(s) extracted', 'images': images}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ocr_bp.route('/download/<path:filename>')
@jwt_required()
def download(filename):
    from flask import send_from_directory
    try:
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404


# ---------------------------------------------------------------------------
# Phase 5 — Multi-language OCR
# ---------------------------------------------------------------------------

@ocr_bp.route('/multilang-ocr', methods=['POST'])
@jwt_required()
def multilang():
    """Run OCR with a specified language (Tesseract lang code)."""
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()
        if 'file' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        file = request.files['file']
        lang = request.form.get('lang', 'eng')
        if not allowed_file(file.filename, IMAGE_EXTENSIONS | {'pdf'}):
            return jsonify({'error': 'Image or PDF files only'}), 400

        from ai_modules.ocr_engine import multilang_ocr
        file_info = save_upload(file, UPLOAD_FOLDER)
        result    = multilang_ocr(file_info['file_path'], lang=lang)
        save_history(user_id, '', 'multilang_ocr', 'success',
                     {'lang': lang, 'word_count': result.get('word_count', 0)})
        return jsonify({'message': f'OCR complete ({lang})', 'result': result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
