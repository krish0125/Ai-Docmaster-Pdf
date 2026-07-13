"""Productivity Routes — Phase 9: Cloud Storage Integrations.

Google Drive, Dropbox, OneDrive — each integration provides:
  - /auth   : return the OAuth URL for the user to visit
  - /callback: exchange code for token (saved per-user in MongoDB)
  - /upload  : upload a local file to the cloud service
  - /list    : list files in the root/app folder
  - /download: download a file from the cloud to local uploads/

Blueprint: productivity_bp  at /productivity.

NOTE: Each provider requires cloud app credentials in .env:
  GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI
  DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REDIRECT_URI
  ONEDRIVE_CLIENT_ID, ONEDRIVE_CLIENT_SECRET, ONEDRIVE_REDIRECT_URI
"""

import os, uuid
from flask import Blueprint, request, jsonify, redirect, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity

from config import Config
from database.models import save_history

productivity_bp = Blueprint('productivity', __name__)
UPLOAD_FOLDER = Config.UPLOAD_FOLDER

# ── helpers ──────────────────────────────────────────────────────────────────

def _uid(): return get_jwt_identity()
def _save(file):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    p = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{file.filename}")
    file.save(p); return p


def _get_tokens(user_id: str, provider: str) -> dict | None:
    """Retrieve stored OAuth tokens for a user/provider from TiDB."""
    try:
        from database.db import get_db
        from database.models import OAuthToken, _parse_id
        session = get_db()
        if session is None:
            return None
            
        uid = _parse_id(user_id)
        if uid is None: return None
            
        record = session.query(OAuthToken).filter(OAuthToken.user_id == uid, OAuthToken.provider == provider).first()
        return record.to_dict() if record else None
    except Exception:
        return None


def _save_tokens(user_id: str, provider: str, tokens: dict):
    try:
        from database.db import get_db
        from database.models import OAuthToken, _parse_id
        session = get_db()
        if session is None:
            return
            
        uid = _parse_id(user_id)
        if uid is None: return
            
        record = session.query(OAuthToken).filter(OAuthToken.user_id == uid, OAuthToken.provider == provider).first()
        if not record:
            record = OAuthToken(user_id=uid, provider=provider)
            session.add(record)
            
        for k, v in tokens.items():
            if hasattr(record, k):
                setattr(record, k, v)
                
        session.commit()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# GOOGLE DRIVE
# ══════════════════════════════════════════════════════════════════════════════

GDRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.file']


def _gdrive_flow():
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError:
        raise RuntimeError("Install: pip install google-auth-oauthlib google-api-python-client")

    return Flow.from_client_config(
        {
            'web': {
                'client_id':     os.getenv('GOOGLE_CLIENT_ID', ''),
                'client_secret': os.getenv('GOOGLE_CLIENT_SECRET', ''),
                'redirect_uris': [os.getenv('GOOGLE_REDIRECT_URI',
                                            'http://localhost:5001/productivity/google/callback')],
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
            }
        },
        scopes=GDRIVE_SCOPES,
        redirect_uri=os.getenv('GOOGLE_REDIRECT_URI',
                               'http://localhost:5001/productivity/google/callback'),
    )


@productivity_bp.route('/google/auth')
@jwt_required()
def google_auth():
    """Return the Google Drive OAuth URL."""
    if not os.getenv('GOOGLE_CLIENT_ID'):
        return jsonify({'error': 'GOOGLE_CLIENT_ID not configured in .env'}), 503
    try:
        flow = _gdrive_flow()
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
        return jsonify({'auth_url': auth_url}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@productivity_bp.route('/google/callback')
@jwt_required()
def google_callback():
    code = request.args.get('code', '')
    uid  = _uid()
    try:
        flow = _gdrive_flow()
        flow.fetch_token(code=code)
        creds = flow.credentials
        _save_tokens(uid, 'google', {
            'token':         creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri':     creds.token_uri,
            'client_id':     creds.client_id,
            'client_secret': creds.client_secret,
        })
        save_history(uid, '', 'google_drive_connect', 'success', {})
        return jsonify({'message': 'Google Drive connected successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@productivity_bp.route('/google/upload', methods=['POST'])
@jwt_required()
def google_upload():
    uid = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file = request.files['file']
    tokens = _get_tokens(uid, 'google')
    if not tokens: return jsonify({'error': 'Not connected to Google Drive. Visit /productivity/google/auth first'}), 401
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds = Credentials(
            token=tokens['token'], refresh_token=tokens.get('refresh_token'),
            token_uri=tokens.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=tokens.get('client_id'), client_secret=tokens.get('client_secret'),
        )
        service  = build('drive', 'v3', credentials=creds)
        src      = _save(file)
        media    = MediaFileUpload(src, resumable=True)
        metadata = {'name': file.filename}
        uploaded = service.files().create(body=metadata, media_body=media, fields='id,name,webViewLink').execute()
        save_history(uid, '', 'google_drive_upload', 'success', {'file': file.filename})
        return jsonify({'message': 'Uploaded to Google Drive', 'file': uploaded}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@productivity_bp.route('/google/list', methods=['GET'])
@jwt_required()
def google_list():
    uid    = _uid()
    tokens = _get_tokens(uid, 'google')
    if not tokens: return jsonify({'error': 'Not connected to Google Drive'}), 401
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds   = Credentials(token=tokens['token'], refresh_token=tokens.get('refresh_token'),
                               token_uri=tokens.get('token_uri', 'https://oauth2.googleapis.com/token'),
                               client_id=tokens.get('client_id'), client_secret=tokens.get('client_secret'))
        service = build('drive', 'v3', credentials=creds)
        results = service.files().list(pageSize=30,
                                       fields='files(id,name,mimeType,size,modifiedTime)').execute()
        return jsonify({'files': results.get('files', [])}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# DROPBOX
# ══════════════════════════════════════════════════════════════════════════════

@productivity_bp.route('/dropbox/auth')
@jwt_required()
def dropbox_auth():
    app_key = os.getenv('DROPBOX_APP_KEY', '')
    if not app_key: return jsonify({'error': 'DROPBOX_APP_KEY not configured in .env'}), 503
    redirect_uri = os.getenv('DROPBOX_REDIRECT_URI', 'http://localhost:5001/productivity/dropbox/callback')
    auth_url = (
        f'https://www.dropbox.com/oauth2/authorize'
        f'?client_id={app_key}&response_type=code&redirect_uri={redirect_uri}'
        f'&token_access_type=offline'
    )
    return jsonify({'auth_url': auth_url}), 200


@productivity_bp.route('/dropbox/callback')
@jwt_required()
def dropbox_callback():
    code = request.args.get('code', '')
    uid  = _uid()
    try:
        import requests
        resp = requests.post('https://api.dropboxapi.com/oauth2/token', data={
            'code': code,
            'grant_type': 'authorization_code',
            'client_id':     os.getenv('DROPBOX_APP_KEY'),
            'client_secret': os.getenv('DROPBOX_APP_SECRET'),
            'redirect_uri':  os.getenv('DROPBOX_REDIRECT_URI',
                                       'http://localhost:5001/productivity/dropbox/callback'),
        })
        data = resp.json()
        if 'access_token' not in data:
            return jsonify({'error': data.get('error_description', 'Auth failed')}), 400
        _save_tokens(uid, 'dropbox', {
            'access_token':  data['access_token'],
            'refresh_token': data.get('refresh_token', ''),
        })
        save_history(uid, '', 'dropbox_connect', 'success', {})
        return jsonify({'message': 'Dropbox connected successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@productivity_bp.route('/dropbox/upload', methods=['POST'])
@jwt_required()
def dropbox_upload():
    uid    = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file   = request.files['file']
    tokens = _get_tokens(uid, 'dropbox')
    if not tokens: return jsonify({'error': 'Not connected to Dropbox'}), 401
    try:
        import requests
        src   = _save(file)
        token = tokens['access_token']
        with open(src, 'rb') as f:
            resp = requests.post(
                'https://content.dropboxapi.com/2/files/upload',
                headers={
                    'Authorization': f'Bearer {token}',
                    'Dropbox-API-Arg': f'{{"path":"/{file.filename}","mode":"overwrite"}}',
                    'Content-Type': 'application/octet-stream',
                },
                data=f
            )
        data = resp.json()
        save_history(uid, '', 'dropbox_upload', 'success', {'file': file.filename})
        return jsonify({'message': 'Uploaded to Dropbox', 'file': data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@productivity_bp.route('/dropbox/list', methods=['GET'])
@jwt_required()
def dropbox_list():
    uid    = _uid()
    tokens = _get_tokens(uid, 'dropbox')
    if not tokens: return jsonify({'error': 'Not connected to Dropbox'}), 401
    try:
        import requests
        resp = requests.post(
            'https://api.dropboxapi.com/2/files/list_folder',
            headers={'Authorization': f'Bearer {tokens["access_token"]}',
                     'Content-Type': 'application/json'},
            json={'path': '', 'limit': 50}
        )
        return jsonify({'files': resp.json().get('entries', [])}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# ONEDRIVE (Microsoft Graph)
# ══════════════════════════════════════════════════════════════════════════════

MS_GRAPH_SCOPES = 'Files.ReadWrite offline_access'


@productivity_bp.route('/onedrive/auth')
@jwt_required()
def onedrive_auth():
    client_id    = os.getenv('ONEDRIVE_CLIENT_ID', '')
    if not client_id: return jsonify({'error': 'ONEDRIVE_CLIENT_ID not configured in .env'}), 503
    redirect_uri = os.getenv('ONEDRIVE_REDIRECT_URI',
                             'http://localhost:5001/productivity/onedrive/callback')
    auth_url = (
        f'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
        f'?client_id={client_id}&response_type=code'
        f'&redirect_uri={redirect_uri}'
        f'&scope={MS_GRAPH_SCOPES}'
    )
    return jsonify({'auth_url': auth_url}), 200


@productivity_bp.route('/onedrive/callback')
@jwt_required()
def onedrive_callback():
    code = request.args.get('code', '')
    uid  = _uid()
    try:
        import requests
        resp = requests.post(
            'https://login.microsoftonline.com/common/oauth2/v2.0/token',
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'client_id':     os.getenv('ONEDRIVE_CLIENT_ID'),
                'client_secret': os.getenv('ONEDRIVE_CLIENT_SECRET'),
                'redirect_uri':  os.getenv('ONEDRIVE_REDIRECT_URI',
                                           'http://localhost:5001/productivity/onedrive/callback'),
                'scope': MS_GRAPH_SCOPES,
            }
        )
        data = resp.json()
        if 'access_token' not in data:
            return jsonify({'error': data.get('error_description', 'Auth failed')}), 400
        _save_tokens(uid, 'onedrive', {
            'access_token':  data['access_token'],
            'refresh_token': data.get('refresh_token', ''),
        })
        save_history(uid, '', 'onedrive_connect', 'success', {})
        return jsonify({'message': 'OneDrive connected successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@productivity_bp.route('/onedrive/upload', methods=['POST'])
@jwt_required()
def onedrive_upload():
    uid    = _uid()
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    file   = request.files['file']
    tokens = _get_tokens(uid, 'onedrive')
    if not tokens: return jsonify({'error': 'Not connected to OneDrive'}), 401
    try:
        import requests
        src   = _save(file)
        token = tokens['access_token']
        with open(src, 'rb') as f:
            resp = requests.put(
                f'https://graph.microsoft.com/v1.0/me/drive/root:/{file.filename}:/content',
                headers={'Authorization': f'Bearer {token}',
                         'Content-Type': 'application/octet-stream'},
                data=f
            )
        data = resp.json()
        save_history(uid, '', 'onedrive_upload', 'success', {'file': file.filename})
        return jsonify({'message': 'Uploaded to OneDrive', 'file': data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@productivity_bp.route('/onedrive/list', methods=['GET'])
@jwt_required()
def onedrive_list():
    uid    = _uid()
    tokens = _get_tokens(uid, 'onedrive')
    if not tokens: return jsonify({'error': 'Not connected to OneDrive'}), 401
    try:
        import requests
        resp = requests.get(
            'https://graph.microsoft.com/v1.0/me/drive/root/children?$top=50',
            headers={'Authorization': f'Bearer {tokens["access_token"]}'}
        )
        items = resp.json().get('value', [])
        return jsonify({'files': items}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Status ────────────────────────────────────────────────────────────────────

@productivity_bp.route('/status', methods=['GET'])
@jwt_required()
def cloud_status():
    """Return which cloud providers this user is connected to."""
    uid = _uid()
    providers = ['google', 'dropbox', 'onedrive']
    connected = {}
    for p in providers:
        t = _get_tokens(uid, p)
        connected[p] = bool(t and t.get('access_token') or t and t.get('token'))
    return jsonify({'connected': connected}), 200
