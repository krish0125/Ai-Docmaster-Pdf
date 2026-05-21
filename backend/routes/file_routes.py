"""File management routes — list, download, delete, stats."""

import os
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from config import Config
from services.file_service import delete_file, get_file_size_formatted
from database.models import (
    get_user_files,
    get_file_by_id,
    delete_file_record,
    get_user_history,
)

file_bp = Blueprint('files', __name__)

UPLOAD_FOLDER = Config.UPLOAD_FOLDER


# ---------------------------------------------------------------------------
# List user files
# ---------------------------------------------------------------------------

@file_bp.route('/list', methods=['GET'])
@jwt_required()
def list_files():
    """Return a list of the authenticated user's uploaded files."""
    try:
        user_id = get_jwt_identity()
        files = get_user_files(user_id)

        file_list = []
        for f in files:
            file_list.append({
                'id': str(f['_id']),
                'filename': f.get('filename', ''),
                'original_name': f.get('original_name', ''),
                'file_type': f.get('file_type', ''),
                'size': f.get('size', 0),
                'size_formatted': get_file_size_formatted(f.get('size', 0)),
                'created_at': str(f.get('created_at', '')),
            })

        return jsonify({
            'files': file_list,
            'total': len(file_list),
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to list files: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Download by file_id
# ---------------------------------------------------------------------------

@file_bp.route('/download/<file_id>', methods=['GET'])
@jwt_required()
def download_file(file_id):
    """Download a file by its database ID (only owner can download)."""
    try:
        user_id = get_jwt_identity()
        record = get_file_by_id(file_id)

        if record is None:
            return jsonify({'error': 'File not found'}), 404

        if record.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403

        file_path = record.get('file_path', '')
        if not os.path.isfile(file_path):
            return jsonify({'error': 'File no longer exists on disk'}), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=record.get('original_name', record.get('filename', 'file')),
        )

    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@file_bp.route('/<file_id>', methods=['DELETE'])
@jwt_required()
def delete(file_id):
    """Delete a file from disk and database (only owner can delete)."""
    try:
        user_id = get_jwt_identity()
        record = get_file_by_id(file_id)

        if record is None:
            return jsonify({'error': 'File not found'}), 404

        if record.get('user_id') != user_id:
            return jsonify({'error': 'Access denied'}), 403

        # Delete from disk
        file_path = record.get('file_path', '')
        delete_file(file_path)

        # Delete from DB
        delete_file_record(file_id)

        return jsonify({'message': 'File deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': f'Delete failed: {str(e)}'}), 500


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@file_bp.route('/stats', methods=['GET'])
@jwt_required()
def stats():
    """Return usage statistics for the authenticated user."""
    try:
        user_id = get_jwt_identity()

        files = get_user_files(user_id)
        history = get_user_history(user_id, limit=1000)

        total_files = len(files)
        total_size = sum(f.get('size', 0) for f in files)
        operations_count = len(history)

        # Count by operation type
        op_counts: dict[str, int] = {}
        for h in history:
            op = h.get('operation', 'unknown')
            op_counts[op] = op_counts.get(op, 0) + 1

        return jsonify({
            'stats': {
                'total_files': total_files,
                'total_size': total_size,
                'total_size_formatted': get_file_size_formatted(total_size),
                'operations_count': operations_count,
                'operations_breakdown': op_counts,
            },
        }), 200

    except Exception as e:
        return jsonify({'error': f'Failed to fetch stats: {str(e)}'}), 500
