"""Authentication routes — signup, login, profile."""

import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
import bcrypt

from database.models import create_user, find_user_by_email, find_user_by_id, update_user, create_oauth_user

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

        # Create JWT — identity is the user's ID as a string
        access_token = create_access_token(identity=str(user['_id']))

        return jsonify({
            'message': 'Login successful',
            'token': access_token,
            'user': {
                'id': str(user['_id']),
                'name': user['name'],
                'email': user['email'],
                'role': user.get('role', 'user'),
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
                'role': user.get('role', 'user'),
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


# ---------------------------------------------------------------------------
# OAuth Integration
# ---------------------------------------------------------------------------
import os
import json
import urllib.parse
from flask import redirect, current_app
from authlib.integrations.flask_client import OAuth

def _get_oauth():
    """Create and return a configured OAuth registry bound to the current Flask app."""
    oauth = OAuth(current_app._get_current_object())

    google_id = os.getenv('GOOGLE_CLIENT_ID')
    google_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    if google_id and google_secret:
        oauth.register(
            name='google',
            client_id=google_id,
            client_secret=google_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )

    github_id = os.getenv('GITHUB_CLIENT_ID')
    github_secret = os.getenv('GITHUB_CLIENT_SECRET')
    if github_id and github_secret:
        oauth.register(
            name='github',
            client_id=github_id,
            client_secret=github_secret,
            access_token_url='https://github.com/login/oauth/access_token',
            authorize_url='https://github.com/login/oauth/authorize',
            api_base_url='https://api.github.com/',
            client_kwargs={'scope': 'user:email'},
        )
    return oauth


@auth_bp.route('/google/login')
def google_login():
    google_id = os.getenv('GOOGLE_CLIENT_ID')
    google_secret = os.getenv('GOOGLE_CLIENT_SECRET')
    if not (google_id and google_secret):
        return jsonify({'error': 'Google OAuth is not configured on this server'}), 503

    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')
    if not redirect_uri:
        return jsonify({'error': 'Google Redirect URI is not configured on this server'}), 503

    oauth = _get_oauth()
    return oauth.google.authorize_redirect(redirect_uri)



@auth_bp.route('/google/callback')
def google_callback():
    if not (os.getenv('GOOGLE_CLIENT_ID') and os.getenv('GOOGLE_CLIENT_SECRET')):
        return jsonify({'error': 'Google OAuth is not configured on this server'}), 503

    oauth = _get_oauth()
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        if not user_info:
            # Fallback to fetching userinfo endpoint manually if token doesn't have it
            user_info = oauth.google.get('https://www.googleapis.com/oauth2/v2/userinfo', token=token).json()
        
        email = user_info.get('email')
        name = user_info.get('name') or user_info.get('given_name') or (email.split('@')[0] if email else 'Google User')
        avatar_url = user_info.get('picture')
        
        if not email:
            return jsonify({'error': 'Failed to retrieve email from Google'}), 400
            
        user = create_oauth_user(name, email, 'google', avatar_url)
        if user is None:
            return jsonify({'error': 'Database error creating or updating user'}), 500
            
        # Issue JWT access token
        access_token = create_access_token(identity=str(user['_id']))
        
        user_data = {
            'id': str(user['_id']),
            'name': user['name'],
            'email': user['email'],
            'role': user.get('role', 'user'),
            'avatar_url': user.get('avatar_url')
        }
        
        fragment = f"token={access_token}&user={urllib.parse.quote(json.dumps(user_data))}"
        redirect_url = f"http://localhost:5500/dashboard.html#{fragment}"
        return redirect(redirect_url)
        
    except Exception as e:
        return jsonify({'error': f'Google login failed: {str(e)}'}), 400


@auth_bp.route('/github/login')
def github_login():
    github_id = os.getenv('GITHUB_CLIENT_ID')
    github_secret = os.getenv('GITHUB_CLIENT_SECRET')
    if not (github_id and github_secret):
        return jsonify({'error': 'GitHub OAuth is not configured on this server'}), 503

    redirect_uri = os.getenv('GITHUB_REDIRECT_URI')
    if not redirect_uri:
        return jsonify({'error': 'GitHub Redirect URI is not configured on this server'}), 503

    oauth = _get_oauth()
    return oauth.github.authorize_redirect(redirect_uri)


@auth_bp.route('/github/callback')
def github_callback():
    if not (os.getenv('GITHUB_CLIENT_ID') and os.getenv('GITHUB_CLIENT_SECRET')):
        return jsonify({'error': 'GitHub OAuth is not configured on this server'}), 503

    oauth = _get_oauth()
    try:
        token = oauth.github.authorize_access_token()
        
        # Get user details
        resp = oauth.github.get('user')
        user_info = resp.json()
        
        # Get user email (including private ones)
        email = user_info.get('email')
        if not email:
            emails_resp = oauth.github.get('user/emails')
            if emails_resp.status_code == 200:
                emails_data = emails_resp.json()
                for entry in emails_data:
                    if entry.get('primary') and entry.get('verified'):
                        email = entry.get('email')
                        break
                if not email and emails_data:
                    email = emails_data[0].get('email')
                    
        if not email:
            return jsonify({'error': 'Failed to retrieve email from GitHub'}), 400
            
        name = user_info.get('name') or user_info.get('login') or email.split('@')[0]
        avatar_url = user_info.get('avatar_url')
        
        user = create_oauth_user(name, email, 'github', avatar_url)
        if user is None:
            return jsonify({'error': 'Database error creating or updating user'}), 500
            
        # Issue JWT access token
        access_token = create_access_token(identity=str(user['_id']))
        
        user_data = {
            'id': str(user['_id']),
            'name': user['name'],
            'email': user['email'],
            'role': user.get('role', 'user'),
            'avatar_url': user.get('avatar_url')
        }
        
        fragment = f"token={access_token}&user={urllib.parse.quote(json.dumps(user_data))}"
        redirect_url = f"http://localhost:5500/dashboard.html#{fragment}"
        return redirect(redirect_url)
        
    except Exception as e:
        return jsonify({'error': f'GitHub login failed: {str(e)}'}), 400
