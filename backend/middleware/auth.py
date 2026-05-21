"""Authentication middleware helpers.

flask-jwt-extended already provides @jwt_required() so this module
adds thin convenience wrappers used across route files.
"""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from database.models import find_user_by_id


def get_current_user_id() -> str | None:
    """Return the current authenticated user's ID string (from JWT identity)."""
    try:
        identity = get_jwt_identity()
        return identity
    except Exception:
        return None


def get_current_user() -> dict | None:
    """Fetch the full user document for the current JWT identity."""
    user_id = get_current_user_id()
    if user_id is None:
        return None
    return find_user_by_id(user_id)


def admin_required(fn):
    """Decorator that requires the current user to have role == 'admin'.
    Must be used AFTER @jwt_required().
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = get_current_user()
        if user is None:
            return jsonify({'error': 'User not found'}), 404
        if user.get('role') != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
        return fn(*args, **kwargs)
    return wrapper
