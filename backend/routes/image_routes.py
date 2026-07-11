"""Image Tool Routes — Phase 7 (Blueprint: image_bp at /image)."""

import os, uuid
from flask import Blueprint, request, jsonify, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity

from config import Config
from database.models import save_file_record, save_history
from services.image_service import (
    resize_image, create_thumbnail, convert_format, apply_filter,
    remove_background, upscale_image, crop_image,
    rotate_image, flip_image, add_text_watermark,
)

image_bp = Blueprint('image', __name__)
UPLOAD_FOLDER = Config.UPLOAD_FOLDER
IMG_EXT = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif', 'webp', 'gif'}


def _uid(): return get_jwt_identity()
def _ext(fn): return fn.rsplit('.', 1)[-1].lower() if '.' in fn else ''
def _rec(uid, fname, orig, ftype, fpath, action, meta=None):
    sz = os.path.getsize(fpath)
    r = save_file_record(user_id=uid, filename=fname, original_name=orig,
                         file_type=ftype, file_path=fpath, size=sz)
    save_history(uid, str(r['_id']) if r else '', action, 'success', meta or {})
    return sz
def _dl(fn): return f'/image/download/{fn}'
def _save(file):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    p = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{file.filename}")
    file.save(p); return p


@image_bp.route('/download/<path:filename>')
@jwt_required()
def download(filename):
    try: return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
    except FileNotFoundError: return jsonify({'error': 'File not found'}), 404


@image_bp.route('/resize', methods=['POST'])
@jwt_required()
def route_resize():
    uid = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file  = request.files['file']
    if _ext(file.filename) not in IMG_EXT: return jsonify({'error': 'Image file required'}), 400
    w     = int(request.form.get('width', 800))
    h     = int(request.form.get('height', 600))
    ratio = request.form.get('keep_ratio', 'true').lower() == 'true'
    try:
        src = _save(file)
        fname, fpath = resize_image(src, w, h, ratio, UPLOAD_FOLDER)
        sz = _rec(uid, fname, f'resized_{file.filename}', _ext(fname), fpath, 'resize_image',
                  {'width': w, 'height': h})
        return jsonify({'message': f'Resized to {w}×{h}', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500


@image_bp.route('/thumbnail', methods=['POST'])
@jwt_required()
def route_thumbnail():
    uid = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    if _ext(file.filename) not in IMG_EXT: return jsonify({'error': 'Image file required'}), 400
    size = int(request.form.get('size', 200))
    try:
        src = _save(file)
        fname, fpath = create_thumbnail(src, size, UPLOAD_FOLDER)
        sz = _rec(uid, fname, f'thumb_{file.filename}', 'jpg', fpath, 'thumbnail')
        return jsonify({'message': 'Thumbnail created', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500


@image_bp.route('/convert-format', methods=['POST'])
@jwt_required()
def route_convert_format():
    uid = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file   = request.files['file']
    if _ext(file.filename) not in IMG_EXT: return jsonify({'error': 'Image file required'}), 400
    target = request.form.get('format', 'png').lower()
    try:
        src = _save(file)
        fname, fpath = convert_format(src, target, UPLOAD_FOLDER)
        sz = _rec(uid, fname, f'{target}_{file.filename}', target, fpath, 'convert_format')
        return jsonify({'message': f'Converted to {target.upper()}', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500


@image_bp.route('/filter', methods=['POST'])
@jwt_required()
def route_filter():
    uid = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file       = request.files['file']
    if _ext(file.filename) not in IMG_EXT: return jsonify({'error': 'Image file required'}), 400
    filter_name = request.form.get('filter', 'grayscale')
    try:
        src = _save(file)
        fname, fpath = apply_filter(src, filter_name, UPLOAD_FOLDER)
        sz = _rec(uid, fname, f'{filter_name}_{file.filename}', 'png', fpath, 'image_filter',
                  {'filter': filter_name})
        return jsonify({'message': f'Filter applied: {filter_name}', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500


@image_bp.route('/remove-background', methods=['POST'])
@jwt_required()
def route_remove_background():
    uid = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    if _ext(file.filename) not in IMG_EXT: return jsonify({'error': 'Image file required'}), 400
    try:
        src = _save(file)
        fname, fpath = remove_background(src, UPLOAD_FOLDER)
        sz = _rec(uid, fname, f'nobg_{file.filename}', 'png', fpath, 'remove_background')
        return jsonify({'message': 'Background removed', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500


@image_bp.route('/upscale', methods=['POST'])
@jwt_required()
def route_upscale():
    uid   = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file  = request.files['file']
    if _ext(file.filename) not in IMG_EXT: return jsonify({'error': 'Image file required'}), 400
    scale = int(request.form.get('scale', 2))
    if scale not in (2, 3, 4): return jsonify({'error': 'Scale must be 2, 3, or 4'}), 400
    try:
        src = _save(file)
        fname, fpath = upscale_image(src, scale, UPLOAD_FOLDER)
        sz = _rec(uid, fname, f'upscaled_{file.filename}', 'png', fpath, 'upscale',
                  {'scale': scale})
        return jsonify({'message': f'Upscaled {scale}×', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500


@image_bp.route('/crop', methods=['POST'])
@jwt_required()
def route_crop():
    uid  = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    if _ext(file.filename) not in IMG_EXT: return jsonify({'error': 'Image file required'}), 400
    left   = int(request.form.get('left', 0))
    top    = int(request.form.get('top', 0))
    right  = int(request.form.get('right', 800))
    bottom = int(request.form.get('bottom', 600))
    try:
        src = _save(file)
        fname, fpath = crop_image(src, left, top, right, bottom, UPLOAD_FOLDER)
        sz = _rec(uid, fname, f'cropped_{file.filename}', 'png', fpath, 'crop_image')
        return jsonify({'message': 'Image cropped', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500


@image_bp.route('/rotate', methods=['POST'])
@jwt_required()
def route_rotate():
    uid   = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file  = request.files['file']
    if _ext(file.filename) not in IMG_EXT: return jsonify({'error': 'Image file required'}), 400
    angle = int(request.form.get('angle', 90))
    try:
        src = _save(file)
        fname, fpath = rotate_image(src, angle, UPLOAD_FOLDER)
        sz = _rec(uid, fname, f'rotated_{file.filename}', 'png', fpath, 'rotate_image',
                  {'angle': angle})
        return jsonify({'message': f'Rotated {angle}°', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500


@image_bp.route('/flip', methods=['POST'])
@jwt_required()
def route_flip():
    uid  = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    if _ext(file.filename) not in IMG_EXT: return jsonify({'error': 'Image file required'}), 400
    direction = request.form.get('direction', 'h')
    try:
        src = _save(file)
        fname, fpath = flip_image(src, direction, UPLOAD_FOLDER)
        sz = _rec(uid, fname, f'flipped_{file.filename}', 'png', fpath, 'flip_image')
        return jsonify({'message': 'Image flipped', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500


@image_bp.route('/watermark', methods=['POST'])
@jwt_required()
def route_watermark():
    uid     = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file    = request.files['file']
    if _ext(file.filename) not in IMG_EXT: return jsonify({'error': 'Image file required'}), 400
    text    = request.form.get('text', 'WATERMARK')
    raw_opacity = request.form.get('opacity', '0.3')
    try:
        op_val = float(raw_opacity)
        # Accept 0.0-1.0 (float) or 0-255 (int) — normalise to 0-255
        opacity = int(op_val * 255) if op_val <= 1.0 else int(op_val)
        opacity = max(0, min(255, opacity))
    except (ValueError, TypeError):
        opacity = 80
    try:
        src = _save(file)
        fname, fpath = add_text_watermark(src, text, opacity, UPLOAD_FOLDER)
        sz = _rec(uid, fname, f'wm_{file.filename}', 'png', fpath, 'image_watermark')
        return jsonify({'message': 'Watermark added', 'download_url': _dl(fname), 'size': sz}), 200
    except Exception as e: return jsonify({'error': str(e)}), 500
