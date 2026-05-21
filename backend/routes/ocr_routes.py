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
