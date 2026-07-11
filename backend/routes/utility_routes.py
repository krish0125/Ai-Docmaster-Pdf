"""Utility Routes — Phase 8 (Blueprint: utility_bp at /utils)."""

import os, uuid
from flask import Blueprint, request, jsonify, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity

from config import Config
from database.models import save_history
from services.utility_service import (
    generate_qr, generate_barcode, get_pdf_metadata, set_pdf_metadata,
    count_words, generate_password, web_to_pdf,
    base64_encode, base64_decode, get_color_info,
)

utility_bp = Blueprint('utils', __name__)
UPLOAD_FOLDER = Config.UPLOAD_FOLDER


def _uid(): return get_jwt_identity()
def _save(file):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    p = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{file.filename}")
    file.save(p); return p
def _dl(fn): return f'/utils/download/{fn}'


@utility_bp.route('/download/<path:filename>')
@jwt_required()
def download(filename):
    try: return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
    except FileNotFoundError: return jsonify({'error': 'File not found'}), 404


# ── QR Code ──────────────────────────────────────────────────────────────────

@utility_bp.route('/qr', methods=['POST'])
@jwt_required()
def route_qr():
    uid  = _uid()
    data = (request.json or {}).get('data') or request.form.get('data', '')
    if not data: return jsonify({'error': 'data is required'}), 400
    size = int((request.json or {}).get('size', request.form.get('size', 300)))
    try:
        fname, fpath = generate_qr(data, size, UPLOAD_FOLDER)
        save_history(uid, '', 'generate_qr', 'success', {'data': data[:80]})
        return jsonify({'message': 'QR code generated', 'download_url': _dl(fname)}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500


# ── Barcode ───────────────────────────────────────────────────────────────────

@utility_bp.route('/barcode', methods=['POST'])
@jwt_required()
def route_barcode():
    uid      = _uid()
    body     = request.json or {}
    data     = body.get('data') or request.form.get('data', '')
    bc_type  = body.get('type') or request.form.get('type', 'code128')
    if not data: return jsonify({'error': 'data is required'}), 400
    try:
        fname, fpath = generate_barcode(data, bc_type, UPLOAD_FOLDER)
        save_history(uid, '', 'generate_barcode', 'success', {'type': bc_type})
        return jsonify({'message': 'Barcode generated', 'download_url': _dl(fname)}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500


# ── PDF Metadata ──────────────────────────────────────────────────────────────

@utility_bp.route('/pdf-metadata', methods=['POST'])
@jwt_required()
def route_get_metadata():
    uid = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    try:
        src  = _save(file)
        meta = get_pdf_metadata(src)
        save_history(uid, '', 'pdf_metadata', 'success', {})
        return jsonify({'message': 'Metadata extracted', 'metadata': meta}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500


@utility_bp.route('/set-metadata', methods=['POST'])
@jwt_required()
def route_set_metadata():
    uid     = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file    = request.files['file']
    title   = request.form.get('title', '')
    author  = request.form.get('author', '')
    subject = request.form.get('subject', '')
    kw      = request.form.get('keywords', '')
    try:
        src = _save(file)
        fname, fpath = set_pdf_metadata(src, title, author, subject, kw, UPLOAD_FOLDER)
        save_history(uid, '', 'set_metadata', 'success', {'title': title})
        return jsonify({'message': 'Metadata updated', 'download_url': _dl(fname)}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500


# ── Word Count ────────────────────────────────────────────────────────────────

@utility_bp.route('/word-count', methods=['POST'])
@jwt_required()
def route_word_count():
    uid  = _uid()
    body = request.json or {}
    text = body.get('text') or request.form.get('text', '')
    if not text:
        # Accept PDF upload
        if 'file' in request.files:
            file = request.files['file']
            src  = _save(file)
            import pdfplumber
            lines = []
            with pdfplumber.open(src) as pdf:
                for p in pdf.pages:
                    t = p.extract_text()
                    if t: lines.append(t)
            text = '\n'.join(lines)
    if not text: return jsonify({'error': 'text or PDF file required'}), 400
    stats = count_words(text)
    save_history(uid, '', 'word_count', 'success', {})
    return jsonify({'message': 'Word count complete', 'stats': stats}), 200


# ── Password Generator ────────────────────────────────────────────────────────

@utility_bp.route('/password', methods=['POST'])
@jwt_required()
def route_password():
    uid     = _uid()
    body    = request.json or {}
    length  = int(body.get('length', request.form.get('length', 16)))
    upper   = str(body.get('upper',   request.form.get('upper',   'true'))).lower() == 'true'
    lower   = str(body.get('lower',   request.form.get('lower',   'true'))).lower() == 'true'
    digits  = str(body.get('digits',  request.form.get('digits',  'true'))).lower() == 'true'
    special = str(body.get('special', request.form.get('special', 'true'))).lower() == 'true'
    result  = generate_password(length, upper, lower, digits, special)
    save_history(uid, '', 'generate_password', 'success', {'length': length})
    return jsonify({'message': 'Password generated', 'result': result}), 200


# ── Web to PDF ────────────────────────────────────────────────────────────────

@utility_bp.route('/web-to-pdf', methods=['POST'])
@jwt_required()
def route_web_to_pdf():
    uid  = _uid()
    body = request.json or {}
    url  = body.get('url') or request.form.get('url', '')
    if not url: return jsonify({'error': 'url is required'}), 400
    try:
        fname, fpath = web_to_pdf(url, UPLOAD_FOLDER)
        save_history(uid, '', 'web_to_pdf', 'success', {'url': url[:200]})
        return jsonify({'message': 'URL converted to PDF', 'download_url': _dl(fname)}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500


# ── Base64 ────────────────────────────────────────────────────────────────────

@utility_bp.route('/base64-encode', methods=['POST'])
@jwt_required()
def route_b64_encode():
    body = request.json or {}
    text = body.get('text') or request.form.get('text', '')
    if not text: return jsonify({'error': 'text required'}), 400
    return jsonify({'result': base64_encode(text)}), 200


@utility_bp.route('/base64-decode', methods=['POST'])
@jwt_required()
def route_b64_decode():
    body = request.json or {}
    data = body.get('data') or request.form.get('data', '')
    if not data: return jsonify({'error': 'data required'}), 400
    try:
        return jsonify({'result': base64_decode(data)}), 200
    except Exception as e:
        return jsonify({'error': f'Decode failed: {e}'}), 400


# ── Color Info ────────────────────────────────────────────────────────────────

@utility_bp.route('/color-info', methods=['POST'])
@jwt_required()
def route_color_info():
    body  = request.json or {}
    color = body.get('color') or request.form.get('color', '#6C63FF')
    try:
        info = get_color_info(color)
        return jsonify({'result': info}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
