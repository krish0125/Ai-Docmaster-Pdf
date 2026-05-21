"""PDF operation routes — upload, merge, split, compress, download."""

import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity

from config import Config
from services.file_service import save_upload, allowed_file
from services.pdf_service import (
    merge_pdfs,
    split_pdf,
    compress_pdf,
    extract_text,
    get_pdf_info,
)
from database.models import save_file_record, save_history

pdf_bp = Blueprint('pdf', __name__)

UPLOAD_FOLDER = Config.UPLOAD_FOLDER


def _ensure_upload_dir():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@pdf_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_pdf():
    """Upload a single PDF file."""
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()

        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename, {'pdf'}):
            return jsonify({'error': 'Only PDF files are allowed'}), 400

        file_info = save_upload(file, UPLOAD_FOLDER)

        # Save record in DB
        record = save_file_record(
            user_id=user_id,
            filename=file_info['filename'],
            original_name=file_info['original_name'],
            file_type='pdf',
            file_path=file_info['file_path'],
            size=file_info['size'],
        )

        pdf_info = get_pdf_info(file_info['file_path'])

        file_id = str(record['_id']) if record else None
        save_history(user_id, file_id or '', 'upload', 'success',
                     {'original_name': file_info['original_name']})

        return jsonify({
            'message': 'File uploaded successfully',
            'file_id': file_id,
            'file_info': {
                'filename': file_info['filename'],
                'original_name': file_info['original_name'],
                'size': file_info['size'],
                'page_count': pdf_info.get('page_count', 0),
                'has_text': pdf_info.get('has_text', False),
            },
        }), 201

    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------

@pdf_bp.route('/merge', methods=['POST'])
@jwt_required()
def merge():
    """Merge multiple uploaded PDF files into one."""
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()

        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400

        files = request.files.getlist('files')
        if len(files) < 2:
            return jsonify({'error': 'At least 2 PDF files are required for merging'}), 400

        saved_paths: list[str] = []
        for f in files:
            if not allowed_file(f.filename, {'pdf'}):
                return jsonify({'error': f'File "{f.filename}" is not a PDF'}), 400
            info = save_upload(f, UPLOAD_FOLDER)
            saved_paths.append(info['file_path'])

        output_name = f"merged_{uuid.uuid4().hex}.pdf"
        output_path = os.path.join(UPLOAD_FOLDER, output_name)

        merge_pdfs(saved_paths, output_path)

        result_info = get_pdf_info(output_path)
        result_size = os.path.getsize(output_path)

        # DB record
        record = save_file_record(
            user_id=user_id,
            filename=output_name,
            original_name='merged.pdf',
            file_type='pdf',
            file_path=output_path,
            size=result_size,
        )
        save_history(user_id, str(record['_id']) if record else '', 'merge', 'success',
                     {'file_count': len(files)})

        return jsonify({
            'message': f'Successfully merged {len(files)} files',
            'download_url': f'/pdf/download/{output_name}',
            'file_info': {
                'filename': output_name,
                'size': result_size,
                'page_count': result_info.get('page_count', 0),
            },
        }), 200

    except Exception as e:
        return jsonify({'error': f'Merge failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Split
# ---------------------------------------------------------------------------

@pdf_bp.route('/split', methods=['POST'])
@jwt_required()
def split():
    """Split a PDF into parts based on page ranges."""
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()

        if 'file' not in request.files:
            return jsonify({'error': 'No PDF file provided'}), 400

        file = request.files['file']
        if not allowed_file(file.filename, {'pdf'}):
            return jsonify({'error': 'Only PDF files are allowed'}), 400

        pages = request.form.get('pages', '')
        if not pages:
            return jsonify({'error': 'Page ranges are required (e.g. "1-3,5,7-10")'}), 400

        file_info = save_upload(file, UPLOAD_FOLDER)
        output_dir = os.path.join(UPLOAD_FOLDER, f"split_{uuid.uuid4().hex}")

        output_paths = split_pdf(file_info['file_path'], pages, output_dir)

        if not output_paths:
            return jsonify({'error': 'No pages matched the given ranges'}), 400

        results = []
        for path in output_paths:
            fname = os.path.basename(path)
            info = get_pdf_info(path)
            results.append({
                'filename': fname,
                'download_url': f'/pdf/download/{fname}',
                'page_count': info.get('page_count', 0),
                'size': os.path.getsize(path),
            })
            # Move split files to main upload folder for serving
            dest = os.path.join(UPLOAD_FOLDER, fname)
            if path != dest:
                os.replace(path, dest)

        save_history(user_id, '', 'split', 'success',
                     {'original': file_info['original_name'], 'parts': len(results)})

        # Clean up temp dir
        try:
            os.rmdir(output_dir)
        except OSError:
            pass

        return jsonify({
            'message': f'Split into {len(results)} parts',
            'parts': results,
        }), 200

    except Exception as e:
        return jsonify({'error': f'Split failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Compress
# ---------------------------------------------------------------------------

@pdf_bp.route('/compress', methods=['POST'])
@jwt_required()
def compress():
    """Compress a PDF file."""
    try:
        _ensure_upload_dir()
        user_id = get_jwt_identity()

        if 'file' not in request.files:
            return jsonify({'error': 'No PDF file provided'}), 400

        file = request.files['file']
        if not allowed_file(file.filename, {'pdf'}):
            return jsonify({'error': 'Only PDF files are allowed'}), 400

        file_info = save_upload(file, UPLOAD_FOLDER)
        output_name = f"compressed_{uuid.uuid4().hex}.pdf"
        output_path = os.path.join(UPLOAD_FOLDER, output_name)

        stats = compress_pdf(file_info['file_path'], output_path)

        record = save_file_record(
            user_id=user_id,
            filename=output_name,
            original_name=f"compressed_{file_info['original_name']}",
            file_type='pdf',
            file_path=output_path,
            size=stats['compressed_size'],
        )
        save_history(user_id, str(record['_id']) if record else '', 'compress', 'success',
                     stats)

        return jsonify({
            'message': 'PDF compressed successfully',
            'download_url': f'/pdf/download/{output_name}',
            'stats': {
                'original_size': stats['original_size'],
                'compressed_size': stats['compressed_size'],
                'reduction_percent': stats['reduction_percent'],
            },
        }), 200

    except Exception as e:
        return jsonify({'error': f'Compression failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

@pdf_bp.route('/download/<filename>', methods=['GET'])
def download(filename):
    """Serve a file from the uploads folder."""
    try:
        return send_from_directory(
            UPLOAD_FOLDER,
            filename,
            as_attachment=True,
        )
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500
