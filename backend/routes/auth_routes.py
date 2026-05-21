"""Authentication routes — signup, login, profile."""

import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
import bcrypt

from database.models import create_user, find_user_by_email, find_user_by_id, update_user

auth_bp = Blueprint('auth', __name__)

# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def _validate_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """Register a new user account."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        name = (data.get('name') or '').strip()
        email = (data.get('email') or '').strip()
        password = data.get('password') or ''

        # --- Validation ---
        errors: list[str] = []
        if not name:
            errors.append('Name is required')
        if not email:
            errors.append('Email is required')
        elif not _validate_email(email):
            errors.append('Invalid email format')
        if not password:
            errors.append('Password is required')
        elif len(password) < 6:
            errors.append('Password must be at least 6 characters')

        if errors:
            return jsonify({'error': errors[0], 'errors': errors}), 400

        # --- Check uniqueness ---
        existing = find_user_by_email(email)
        if existing is not None:
            return jsonify({'error': 'An account with this email already exists'}), 409

        # --- Hash password ---
        password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt(),
        ).decode('utf-8')

        # --- Create user ---
        user = create_user(name, email, password_hash)
        if user is None:
            return jsonify({
                'error': 'Could not create user. Database may be unavailable.',
            }), 503

        return jsonify({
            'message': 'Account created successfully',
            'user': {
                'id': str(user['_id']),
                'name': user['name'],
                'email': user['email'],
            },
        }), 201

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate and return a JWT token."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        email = (data.get('email') or '').strip()
        password = data.get('password') or ''

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        user = find_user_by_email(email)
        if user is None:
            return jsonify({'error': 'Invalid email or password'}), 401

        # Verify password
        if not bcrypt.checkpw(
            password.encode('utf-8'),
            user['password'].encode('utf-8'),
        ):
            return jsonify({'error': 'Invalid email or password'}), 401

        # Create JWT — identity is the user's ObjectId as a string
        access_token = create_access_token(identity=str(user['_id']))

        return jsonify({
            'message': 'Login successful',
            'token': access_token,
            'user': {
                'id': str(user['_id']),
                'name': user['name'],
                'email': user['email'],
            },
        }), 200

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Return the current user's profile (excludes password)."""
    try:
        user_id = get_jwt_identity()
        user = find_user_by_id(user_id)
        if user is None:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user': {
                'id': str(user['_id']),
                'name': user.get('name', ''),
                'email': user.get('email', ''),
                'created_at': str(user.get('created_at', '')),
            },
        }), 200

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update the current user's name."""
    try:
        user_id = get_jwt_identity()
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'Name is required'}), 400

        success = update_user(user_id, {'name': name})
        if not success:
            return jsonify({'error': 'Could not update profile'}), 500

        user = find_user_by_id(user_id)
        return jsonify({
            'message': 'Profile updated',
            'user': {
                'id': str(user['_id']),
                'name': user['name'],
                'email': user['email'],
            },
        }), 200

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500
