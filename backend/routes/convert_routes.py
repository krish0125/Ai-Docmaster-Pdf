"""PDF Conversion Routes — Phase 2.

Blueprint: convert_bp  registered at /convert in app.py.
"""

import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity

from config import Config
from database.models import save_file_record, save_history

# Import all converter functions (each wraps missing-library errors)
from services.convert_service import (
    pdf_to_word, word_to_pdf,
    pdf_to_excel, excel_to_pdf,
    pdf_to_pptx, pptx_to_pdf,
    pdf_to_images, images_to_pdf,
    pdf_to_html, html_to_pdf,
    pdf_to_text, text_to_pdf,
    pdf_to_epub, epub_to_pdf,
)

convert_bp = Blueprint('convert', __name__)

UPLOAD_FOLDER     = Config.UPLOAD_FOLDER
ALLOWED_PDF       = {'pdf'}
ALLOWED_DOCX      = {'docx', 'doc'}
ALLOWED_XLSX      = {'xlsx', 'xls'}
ALLOWED_PPTX      = {'pptx', 'ppt'}
ALLOWED_IMG       = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif', 'gif'}
ALLOWED_HTML      = {'html', 'htm'}
ALLOWED_TXT       = {'txt'}
ALLOWED_EPUB      = {'epub'}


def _ext(filename: str) -> str:
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


def _ensure_dir():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)


from services.file_service import upload_to_r2

def _save_upload(file) -> str:
    """Save uploaded file; return full path."""
    _ensure_dir()
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    path = os.path.join(UPLOAD_FOLDER, safe_name)
    file.save(path)
    # R2 integration for input files
    if upload_to_r2(path, safe_name):
        try:
            os.remove(path)
        except Exception:
            pass
    return path


def _make_record(user_id, filename, original_name, file_type, file_path, action, meta=None):
    size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    # Upload output to R2
    if upload_to_r2(file_path, filename):
        try:
            os.remove(file_path)
        except Exception:
            pass
            
    record = save_file_record(
        user_id=user_id, filename=filename,
        original_name=original_name, file_type=file_type,
        file_path=file_path, size=size,
    )
    save_history(user_id, str(record['_id']) if record else '', action, 'success', meta or {})
    return size


def _dl_url(filename: str) -> str:
    return f'/convert/download/{filename}'


# ── Download ────────────────────────────────────────────────────────────────

@convert_bp.route('/download/<path:filename>')
def download(filename):
    try:
        return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404


# ── PDF → Word ───────────────────────────────────────────────────────────────

@convert_bp.route('/pdf-to-word', methods=['POST'])
@jwt_required()
def route_pdf_to_word():
    user_id = get_jwt_identity()
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if _ext(file.filename) not in ALLOWED_PDF:
        return jsonify({'error': 'Only PDF files accepted'}), 400
    try:
        src = _save_upload(file)
        fname, fpath = pdf_to_word(src, UPLOAD_FOLDER)
        size = _make_record(user_id, fname, f"word_{file.filename}", 'docx', fpath, 'pdf_to_word')
        return jsonify({'message': 'PDF converted to Word', 'download_url': _dl_url(fname),
                        'filename': fname, 'size': size}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Word → PDF ───────────────────────────────────────────────────────────────

@convert_bp.route('/word-to-pdf', methods=['POST'])
@jwt_required()
def route_word_to_pdf():
    user_id = get_jwt_identity()
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if _ext(file.filename) not in ALLOWED_DOCX:
        return jsonify({'error': 'Only DOCX/DOC files accepted'}), 400
    try:
        src = _save_upload(file)
        fname, fpath = word_to_pdf(src, UPLOAD_FOLDER)
        size = _make_record(user_id, fname, f"pdf_{file.filename}", 'pdf', fpath, 'word_to_pdf')
        return jsonify({'message': 'Word converted to PDF', 'download_url': _dl_url(fname),
                        'filename': fname, 'size': size}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── PDF → Excel ──────────────────────────────────────────────────────────────

@convert_bp.route('/pdf-to-excel', methods=['POST'])
@jwt_required()
def route_pdf_to_excel():
    user_id = get_jwt_identity()
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if _ext(file.filename) not in ALLOWED_PDF:
        return jsonify({'error': 'Only PDF files accepted'}), 400
    try:
        src = _save_upload(file)
        fname, fpath = pdf_to_excel(src, UPLOAD_FOLDER)
        size = _make_record(user_id, fname, f"excel_{file.filename}", 'xlsx', fpath, 'pdf_to_excel')
        return jsonify({'message': 'Tables extracted to Excel', 'download_url': _dl_url(fname),
                        'filename': fname, 'size': size}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Excel → PDF ──────────────────────────────────────────────────────────────

@convert_bp.route('/excel-to-pdf', methods=['POST'])
@jwt_required()
def route_excel_to_pdf():
    user_id = get_jwt_identity()
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if _ext(file.filename) not in ALLOWED_XLSX:
        return jsonify({'error': 'Only XLSX/XLS files accepted'}), 400
    try:
        src = _save_upload(file)
        fname, fpath = excel_to_pdf(src, UPLOAD_FOLDER)
        size = _make_record(user_id, fname, f"pdf_{file.filename}", 'pdf', fpath, 'excel_to_pdf')
        return jsonify({'message': 'Excel converted to PDF', 'download_url': _dl_url(fname),
                        'filename': fname, 'size': size}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── PDF → PowerPoint ─────────────────────────────────────────────────────────

@convert_bp.route('/pdf-to-pptx', methods=['POST'])
@jwt_required()
def route_pdf_to_pptx():
    user_id = get_jwt_identity()
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if _ext(file.filename) not in ALLOWED_PDF:
        return jsonify({'error': 'Only PDF files accepted'}), 400
    try:
        src = _save_upload(file)
        fname, fpath = pdf_to_pptx(src, UPLOAD_FOLDER)
        size = _make_record(user_id, fname, f"pptx_{file.filename}", 'pptx', fpath, 'pdf_to_pptx')
        return jsonify({'message': 'PDF converted to PowerPoint', 'download_url': _dl_url(fname),
                        'filename': fname, 'size': size}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── PowerPoint → PDF ─────────────────────────────────────────────────────────

@convert_bp.route('/pptx-to-pdf', methods=['POST'])
@jwt_required()
def route_pptx_to_pdf():
    user_id = get_jwt_identity()
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if _ext(file.filename) not in ALLOWED_PPTX:
        return jsonify({'error': 'Only PPTX/PPT files accepted'}), 400
    try:
        src = _save_upload(file)
        fname, fpath = pptx_to_pdf(src, UPLOAD_FOLDER)
        size = _make_record(user_id, fname, f"pdf_{file.filename}", 'pdf', fpath, 'pptx_to_pdf')
        return jsonify({'message': 'PowerPoint converted to PDF', 'download_url': _dl_url(fname),
                        'filename': fname, 'size': size}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── PDF → Images ─────────────────────────────────────────────────────────────

@convert_bp.route('/pdf-to-image', methods=['POST'])
@jwt_required()
def route_pdf_to_image():
    user_id = get_jwt_identity()
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if _ext(file.filename) not in ALLOWED_PDF:
        return jsonify({'error': 'Only PDF files accepted'}), 400
    fmt = request.form.get('format', 'jpg').lower()
    dpi = int(request.form.get('dpi', 150))
    try:
        src = _save_upload(file)
        results = pdf_to_images(src, UPLOAD_FOLDER, fmt=fmt, dpi=dpi)
        download_urls = []
        for fname, fpath in results:
            _make_record(user_id, fname, f"img_{file.filename}", fmt, fpath, 'pdf_to_image',
                         {'format': fmt, 'dpi': dpi})
            download_urls.append(_dl_url(fname))
        return jsonify({
            'message': f'PDF converted to {len(results)} image(s)',
            'download_urls': download_urls,
            'page_count': len(results),
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Images → PDF ─────────────────────────────────────────────────────────────

@convert_bp.route('/image-to-pdf', methods=['POST'])
@jwt_required()
def route_image_to_pdf():
    user_id = get_jwt_identity()
    files = request.files.getlist('files') or request.files.getlist('file')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No image files provided'}), 400
    for f in files:
        if _ext(f.filename) not in ALLOWED_IMG:
            return jsonify({'error': f'{f.filename} is not an accepted image format'}), 400
    try:
        saved_paths = []
        for f in files:
            p = _save_upload(f)
            saved_paths.append(p)
        fname, fpath = images_to_pdf(saved_paths, UPLOAD_FOLDER)
        size = _make_record(user_id, fname, 'combined_images.pdf', 'pdf', fpath, 'image_to_pdf')
        return jsonify({'message': f'{len(files)} images merged into PDF',
                        'download_url': _dl_url(fname), 'filename': fname, 'size': size}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── PDF → HTML ────────────────────────────────────────────────────────────────

@convert_bp.route('/pdf-to-html', methods=['POST'])
@jwt_required()
def route_pdf_to_html():
    user_id = get_jwt_identity()
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if _ext(file.filename) not in ALLOWED_PDF:
        return jsonify({'error': 'Only PDF files accepted'}), 400
    try:
        src = _save_upload(file)
        fname, fpath = pdf_to_html(src, UPLOAD_FOLDER)
        size = _make_record(user_id, fname, f"html_{file.filename}", 'html', fpath, 'pdf_to_html')
        return jsonify({'message': 'PDF converted to HTML', 'download_url': _dl_url(fname),
                        'filename': fname, 'size': size}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── HTML → PDF ────────────────────────────────────────────────────────────────

@convert_bp.route('/html-to-pdf', methods=['POST'])
@jwt_required()
def route_html_to_pdf():
    user_id = get_jwt_identity()
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if _ext(file.filename) not in ALLOWED_HTML:
        return jsonify({'error': 'Only HTML/HTM files accepted'}), 400
    try:
        src = _save_upload(file)
        fname, fpath = html_to_pdf(src, UPLOAD_FOLDER)
        size = _make_record(user_id, fname, f"pdf_{file.filename}", 'pdf', fpath, 'html_to_pdf')
        return jsonify({'message': 'HTML converted to PDF', 'download_url': _dl_url(fname),
                        'filename': fname, 'size': size}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── PDF → Text ────────────────────────────────────────────────────────────────

@convert_bp.route('/pdf-to-text', methods=['POST'])
@jwt_required()
def route_pdf_to_text():
    user_id = get_jwt_identity()
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if _ext(file.filename) not in ALLOWED_PDF:
        return jsonify({'error': 'Only PDF files accepted'}), 400
    try:
        src = _save_upload(file)
        fname, fpath = pdf_to_text(src, UPLOAD_FOLDER)
        size = _make_record(user_id, fname, f"text_{file.filename}", 'txt', fpath, 'pdf_to_text')
        return jsonify({'message': 'Text extracted from PDF', 'download_url': _dl_url(fname),
                        'filename': fname, 'size': size}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Text → PDF ────────────────────────────────────────────────────────────────

@convert_bp.route('/text-to-pdf', methods=['POST'])
@jwt_required()
def route_text_to_pdf():
    user_id = get_jwt_identity()
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if _ext(file.filename) not in ALLOWED_TXT:
        return jsonify({'error': 'Only TXT files accepted'}), 400
    try:
        src = _save_upload(file)
        fname, fpath = text_to_pdf(src, UPLOAD_FOLDER)
        size = _make_record(user_id, fname, f"pdf_{file.filename}", 'pdf', fpath, 'text_to_pdf')
        return jsonify({'message': 'Text converted to PDF', 'download_url': _dl_url(fname),
                        'filename': fname, 'size': size}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── PDF → EPUB ────────────────────────────────────────────────────────────────

@convert_bp.route('/pdf-to-epub', methods=['POST'])
@jwt_required()
def route_pdf_to_epub():
    user_id = get_jwt_identity()
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if _ext(file.filename) not in ALLOWED_PDF:
        return jsonify({'error': 'Only PDF files accepted'}), 400
    try:
        src = _save_upload(file)
        fname, fpath = pdf_to_epub(src, UPLOAD_FOLDER)
        size = _make_record(user_id, fname, f"epub_{file.filename}", 'epub', fpath, 'pdf_to_epub')
        return jsonify({'message': 'PDF converted to EPUB', 'download_url': _dl_url(fname),
                        'filename': fname, 'size': size}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── EPUB → PDF ────────────────────────────────────────────────────────────────

@convert_bp.route('/epub-to-pdf', methods=['POST'])
@jwt_required()
def route_epub_to_pdf():
    user_id = get_jwt_identity()
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if _ext(file.filename) not in ALLOWED_EPUB:
        return jsonify({'error': 'Only EPUB files accepted'}), 400
    try:
        src = _save_upload(file)
        fname, fpath = epub_to_pdf(src, UPLOAD_FOLDER)
        size = _make_record(user_id, fname, f"pdf_{file.filename}", 'pdf', fpath, 'epub_to_pdf')
        return jsonify({'message': 'EPUB converted to PDF', 'download_url': _dl_url(fname),
                        'filename': fname, 'size': size}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
