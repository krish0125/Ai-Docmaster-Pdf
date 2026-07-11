"""PDF Security Routes — Phase 4 (Blueprint: security_bp at /security)."""

import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity

from config import Config
from database.models import save_file_record, save_history
from services.security_service import (
    lock_pdf, unlock_pdf, add_watermark, flatten_pdf,
    remove_metadata, add_signature_stamp, redact_area,
)

security_bp = Blueprint('security', __name__)
UPLOAD_FOLDER = Config.UPLOAD_FOLDER


def _uid(): return get_jwt_identity()
def _ext(fn): return fn.rsplit('.', 1)[-1].lower() if '.' in fn else ''
def _rec(uid, fname, orig, ftype, fpath, action, meta=None):
    sz = os.path.getsize(fpath)
    r = save_file_record(user_id=uid, filename=fname, original_name=orig,
                         file_type=ftype, file_path=fpath, size=sz)
    save_history(uid, str(r['_id']) if r else '', action, 'success', meta or {})
    return sz
def _dl(fn): return f'/security/download/{fn}'
def _save(file):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    p = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{file.filename}")
    file.save(p); return p


@security_bp.route('/download/<path:filename>')
def download(filename):
    try: return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
    except FileNotFoundError: return jsonify({'error': 'File not found'}), 404


@security_bp.route('/lock', methods=['POST'])
@jwt_required()
def route_lock():
    user_id  = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file     = request.files['file']
    password = request.form.get('password', '')
    if not password: return jsonify({'error': 'password is required'}), 400
    try:
        src = _save(file)
        fname, fpath = lock_pdf(src, password, UPLOAD_FOLDER)
        sz = _rec(user_id, fname, f'locked_{file.filename}', 'pdf', fpath, 'lock')
        return jsonify({'message': 'PDF locked with password', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@security_bp.route('/unlock', methods=['POST'])
@jwt_required()
def route_unlock():
    user_id  = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file     = request.files['file']
    password = request.form.get('password', '')
    try:
        src = _save(file)
        fname, fpath = unlock_pdf(src, password, UPLOAD_FOLDER)
        sz = _rec(user_id, fname, f'unlocked_{file.filename}', 'pdf', fpath, 'unlock')
        return jsonify({'message': 'PDF unlocked', 'download_url': _dl(fname), 'size': sz}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@security_bp.route('/watermark', methods=['POST'])
@jwt_required()
def route_watermark():
    user_id   = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file      = request.files['file']
    text      = request.form.get('text', 'CONFIDENTIAL')
    opacity   = float(request.form.get('opacity', 0.15))
    font_size = int(request.form.get('font_size', 48))
    color     = request.form.get('color', '#888888')
    try:
        src = _save(file)
        fname, fpath = add_watermark(src, text, opacity, font_size, color, UPLOAD_FOLDER)
        sz = _rec(user_id, fname, f'watermarked_{file.filename}', 'pdf', fpath, 'watermark')
        return jsonify({'message': 'Watermark added', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@security_bp.route('/flatten', methods=['POST'])
@jwt_required()
def route_flatten():
    user_id = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file    = request.files['file']
    try:
        src = _save(file)
        fname, fpath = flatten_pdf(src, UPLOAD_FOLDER)
        sz = _rec(user_id, fname, f'flat_{file.filename}', 'pdf', fpath, 'flatten')
        return jsonify({'message': 'PDF flattened', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@security_bp.route('/remove-metadata', methods=['POST'])
@jwt_required()
def route_remove_metadata():
    user_id = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file    = request.files['file']
    try:
        src = _save(file)
        fname, fpath = remove_metadata(src, UPLOAD_FOLDER)
        sz = _rec(user_id, fname, f'nometa_{file.filename}', 'pdf', fpath, 'remove_metadata')
        return jsonify({'message': 'Metadata removed', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@security_bp.route('/sign', methods=['POST'])
@jwt_required()
def route_sign():
    user_id     = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file        = request.files['file']
    signer      = request.form.get('signer_name', 'Signer')
    date_str    = request.form.get('date', '')
    page_num    = int(request.form.get('page', 1))
    if not date_str:
        from datetime import date
        date_str = date.today().strftime('%Y-%m-%d')
    try:
        src = _save(file)
        fname, fpath = add_signature_stamp(src, signer, date_str, page_num, UPLOAD_FOLDER)
        sz = _rec(user_id, fname, f'signed_{file.filename}', 'pdf', fpath, 'sign',
                  {'signer': signer, 'date': date_str})
        return jsonify({'message': 'Signature stamp added', 'download_url': _dl(fname), 'size': sz,
                        'note': 'Visual stamp only — not a cryptographic signature'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@security_bp.route('/redact', methods=['POST'])
@jwt_required()
def route_redact():
    user_id   = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file      = request.files['file']
    x         = float(request.form.get('x', 10))
    y         = float(request.form.get('y', 40))
    w_pct     = float(request.form.get('width', 30))
    h_pct     = float(request.form.get('height', 5))
    pages_str = request.form.get('pages', '')
    pages     = [int(p) for p in pages_str.split(',') if p.strip()] if pages_str else None
    try:
        src = _save(file)
        fname, fpath = redact_area(src, x, y, w_pct, h_pct, pages, UPLOAD_FOLDER)
        sz = _rec(user_id, fname, f'redacted_{file.filename}', 'pdf', fpath, 'redact')
        return jsonify({'message': 'Area redacted', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
