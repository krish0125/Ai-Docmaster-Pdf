"""PDF Editing Routes — Phase 3 (Blueprint: edit_bp at /edit)."""

import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity

from config import Config
from database.models import save_file_record, save_history
from services.edit_service import (
    add_text, add_image, highlight_area,
    add_header_footer, add_page_numbers, whiteout,
)

edit_bp = Blueprint('edit', __name__)
UPLOAD_FOLDER = Config.UPLOAD_FOLDER


def _uid(): return get_jwt_identity()
def _ext(fn): return fn.rsplit('.', 1)[-1].lower() if '.' in fn else ''
def _rec(user_id, fname, orig, ftype, fpath, action, meta=None):
    sz = os.path.getsize(fpath)
    r = save_file_record(user_id=user_id, filename=fname, original_name=orig,
                         file_type=ftype, file_path=fpath, size=sz)
    save_history(user_id, str(r['_id']) if r else '', action, 'success', meta or {})
    return sz
def _dl(fn): return f'/edit/download/{fn}'
def _save(file):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    p = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{file.filename}")
    file.save(p); return p


@edit_bp.route('/download/<path:filename>')
def download(filename):
    try: return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
    except FileNotFoundError: return jsonify({'error': 'File not found'}), 404


@edit_bp.route('/add-text', methods=['POST'])
@jwt_required()
def route_add_text():
    user_id = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    if _ext(file.filename) != 'pdf': return jsonify({'error': 'PDF only'}), 400
    text       = request.form.get('text', 'Sample Text')
    x          = float(request.form.get('x', 10))
    y          = float(request.form.get('y', 10))
    font_size  = int(request.form.get('font_size', 14))
    color      = request.form.get('color', '#000000')
    pages_str  = request.form.get('pages', '')
    pages      = [int(p) for p in pages_str.split(',') if p.strip()] if pages_str else None
    try:
        src = _save(file)
        fname, fpath = add_text(src, text, x, y, font_size, color, pages, UPLOAD_FOLDER)
        sz = _rec(user_id, fname, f'text_{file.filename}', 'pdf', fpath, 'add_text')
        return jsonify({'message': 'Text added', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@edit_bp.route('/add-image', methods=['POST'])
@jwt_required()
def route_add_image():
    user_id = _uid()
    if 'file' not in request.files or 'image' not in request.files:
        return jsonify({'error': 'Both PDF (file) and image (image) required'}), 400
    file  = request.files['file']
    img   = request.files['image']
    x     = float(request.form.get('x', 70))
    y     = float(request.form.get('y', 70))
    w_pct = float(request.form.get('width', 20))
    pages_str = request.form.get('pages', '')
    pages = [int(p) for p in pages_str.split(',') if p.strip()] if pages_str else None
    try:
        src      = _save(file)
        img_path = _save(img)
        fname, fpath = add_image(src, img_path, x, y, w_pct, pages, UPLOAD_FOLDER)
        sz = _rec(user_id, fname, f'img_{file.filename}', 'pdf', fpath, 'add_image')
        return jsonify({'message': 'Image added', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@edit_bp.route('/highlight', methods=['POST'])
@jwt_required()
def route_highlight():
    user_id = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file    = request.files['file']
    x       = float(request.form.get('x', 10))
    y       = float(request.form.get('y', 40))
    w_pct   = float(request.form.get('width', 80))
    h_pct   = float(request.form.get('height', 10))
    color   = request.form.get('color', '#FFFF00')
    opacity = float(request.form.get('opacity', 0.4))
    pages_str = request.form.get('pages', '')
    pages = [int(p) for p in pages_str.split(',') if p.strip()] if pages_str else None
    try:
        src = _save(file)
        fname, fpath = highlight_area(src, x, y, w_pct, h_pct, color, opacity, pages, UPLOAD_FOLDER)
        sz = _rec(user_id, fname, f'highlighted_{file.filename}', 'pdf', fpath, 'highlight')
        return jsonify({'message': 'Area highlighted', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@edit_bp.route('/header-footer', methods=['POST'])
@jwt_required()
def route_header_footer():
    user_id   = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file      = request.files['file']
    header    = request.form.get('header', '')
    footer    = request.form.get('footer', '')
    font_size = int(request.form.get('font_size', 10))
    try:
        src = _save(file)
        fname, fpath = add_header_footer(src, header, footer, font_size, UPLOAD_FOLDER)
        sz = _rec(user_id, fname, f'hf_{file.filename}', 'pdf', fpath, 'header_footer')
        return jsonify({'message': 'Header/footer added', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@edit_bp.route('/page-numbers', methods=['POST'])
@jwt_required()
def route_page_numbers():
    user_id   = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file      = request.files['file']
    position  = request.form.get('position', 'bottom-center')
    font_size = int(request.form.get('font_size', 10))
    start     = int(request.form.get('start', 1))
    try:
        src = _save(file)
        fname, fpath = add_page_numbers(src, position, font_size, start, UPLOAD_FOLDER)
        sz = _rec(user_id, fname, f'numbered_{file.filename}', 'pdf', fpath, 'page_numbers')
        return jsonify({'message': 'Page numbers added', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@edit_bp.route('/whiteout', methods=['POST'])
@jwt_required()
def route_whiteout():
    user_id = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file  = request.files['file']
    x     = float(request.form.get('x', 10))
    y     = float(request.form.get('y', 40))
    w_pct = float(request.form.get('width', 30))
    h_pct = float(request.form.get('height', 10))
    pages_str = request.form.get('pages', '')
    pages = [int(p) for p in pages_str.split(',') if p.strip()] if pages_str else None
    try:
        src = _save(file)
        fname, fpath = whiteout(src, x, y, w_pct, h_pct, pages, UPLOAD_FOLDER)
        sz = _rec(user_id, fname, f'whiteout_{file.filename}', 'pdf', fpath, 'whiteout')
        return jsonify({'message': 'Area whited out', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@edit_bp.route('/edit-pdf-text', methods=['POST'])
@jwt_required()
def route_edit_pdf_text():
    import json
    import fitz
    user_id = _uid()
    if 'file' not in request.files:
        return jsonify({'error': 'No PDF file provided'}), 400
    file = request.files['file']
    if _ext(file.filename) != 'pdf':
        return jsonify({'error': 'Only PDF files accepted'}), 400
        
    edits_str = request.form.get('edits', '[]')
    try:
        edits = json.loads(edits_str)
    except Exception as e:
        return jsonify({'error': f'Invalid edits JSON: {str(e)}'}), 400

    try:
        src = _save(file)
        doc = fitz.open(src)
        
        # Mapping standard font family choices to PyMuPDF built-in fonts
        def map_font(family, bold, italic):
            family = (family or "helvetica").lower()
            if "times" in family:
                base = "Times"
            elif "cour" in family:
                base = "Courier"
            else:
                base = "Helvetica"
                
            if bold and italic:
                suffix = "-BoldOblique" if base in ("Helvetica", "Courier") else "-BoldItalic"
            elif bold:
                suffix = "-Bold"
            elif italic:
                suffix = "-Oblique" if base in ("Helvetica", "Courier") else "-Italic"
            else:
                suffix = ""
                
            if base == "Times" and suffix == "":
                return "Times-Roman"
            return base + suffix

        # Apply edits page by page
        for edit in edits:
            page_index = int(edit.get('page_index', 0))
            if page_index < 0 or page_index >= len(doc):
                continue
            
            page = doc[page_index]
            page_width = page.rect.width
            page_height = page.rect.height
            
            # Convert percentage coordinates to PDF points
            x = float(edit.get('x', 0)) * page_width
            y = float(edit.get('y', 0)) * page_height
            w = float(edit.get('width', 0)) * page_width
            h = float(edit.get('height', 0)) * page_height
            
            rect = fitz.Rect(x, y, x + w, y + h)
            edit_type = edit.get('type', 'edit')
            
            # 1. For replacements, white out the original bounding box
            if edit_type == 'edit':
                # Overlay a white rectangle to erase original text run
                page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1), width=0)
            
            # 2. Draw the new text inside the bounding box
            text = edit.get('text', '')
            font_family = edit.get('font_family', 'Helvetica')
            font_size = float(edit.get('font_size', 12))
            bold = bool(edit.get('bold', False))
            italic = bool(edit.get('italic', False))
            font_name = map_font(font_family, bold, italic)
            
            # Color conversion from Hex to RGB Tuple
            hex_color = edit.get('color', '#000000').lstrip('#')
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16) / 255.0
                g = int(hex_color[2:4], 16) / 255.0
                b = int(hex_color[4:6], 16) / 255.0
                color = (r, g, b)
            else:
                color = (0, 0, 0)
                
            # Alignment mapping (0=left, 1=center, 2=right)
            align_str = edit.get('align', 'left').lower()
            align_code = 0
            if align_str == 'center':
                align_code = 1
            elif align_str == 'right':
                align_code = 2
                
            if text:
                # Add text box inside rect
                page.insert_textbox(rect, text, fontsize=font_size, fontname=font_name, color=color, align=align_code)
                
        # Save output PDF
        out_name = f"edited_text_{uuid.uuid4().hex}.pdf"
        out_path = os.path.join(UPLOAD_FOLDER, out_name)
        doc.save(out_path)
        doc.close()
        
        sz = _rec(user_id, out_name, f'edited_{file.filename}', 'pdf', out_path, 'edit_pdf_text')
        return jsonify({
            'message': 'PDF text edited successfully',
            'download_url': _dl(out_name),
            'size': sz
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
