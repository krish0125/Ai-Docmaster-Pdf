"""Thread-safe JSON file-based database fallback when MongoDB is unavailable."""

import os
import json
import uuid
import threading
from datetime import datetime, timezone

# Path to the local JSON database file
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'local_db.json')
_lock = threading.Lock()


def _load_data() -> dict:
    """Helper to load all data from the JSON file."""
    if not os.path.exists(DB_FILE):
        return {
            'users': [],
            'files': [],
            'history': [],
            'chats': []
        }
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {'users': [], 'files': [], 'history': [], 'chats': []}
            return json.loads(content)
    except Exception as e:
        print(f"[JSON DB] Error loading database: {e}")
        return {'users': [], 'files': [], 'history': [], 'chats': []}


def _save_data(data: dict):
    """Helper to save all data to the JSON file."""
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        print(f"[JSON DB] Error saving database: {e}")


# ── Users API ───────────────────────────────────────────────────────────────

def json_create_user(name: str, email: str, password_hash: str) -> dict | None:
    with _lock:
        data = _load_data()
        email_clean = email.lower().strip()
        
        # Check if user already exists
        for u in data['users']:
            if u['email'] == email_clean:
                print(f"[JSON DB] Create user failed: email {email_clean} already registered")
                return None
                
        user_doc = {
            '_id': str(uuid.uuid4()),
            'name': name,
            'email': email_clean,
            'password': password_hash,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }
        data['users'].append(user_doc)
        _save_data(data)
        return user_doc


def json_find_user_by_email(email: str) -> dict | None:
    with _lock:
        data = _load_data()
        email_clean = email.lower().strip()
        for u in data['users']:
            if u['email'] == email_clean:
                return u
        return None


def json_find_user_by_id(user_id: str) -> dict | None:
    with _lock:
        data = _load_data()
        for u in data['users']:
            if u['_id'] == str(user_id):
                return u
        return None


def json_update_user(user_id: str, update_fields: dict) -> bool:
    with _lock:
        data = _load_data()
        for u in data['users']:
            if u['_id'] == str(user_id):
                for k, v in update_fields.items():
                    if k == 'email':
                        u[k] = v.lower().strip()
                    else:
                        u[k] = v
                u['updated_at'] = datetime.now(timezone.utc).isoformat()
                _save_data(data)
                return True
        return False


# ── Files API ───────────────────────────────────────────────────────────────

def json_save_file_record(user_id: str, filename: str, original_name: str,
                          file_type: str, file_path: str, size: int) -> dict | None:
    with _lock:
        data = _load_data()
        file_doc = {
            '_id': str(uuid.uuid4()),
            'user_id': str(user_id),
            'filename': filename,
            'original_name': original_name,
            'file_type': file_type,
            'file_path': file_path,
            'size': size,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        data['files'].append(file_doc)
        _save_data(data)
        return file_doc


def json_get_user_files(user_id: str) -> list:
    with _lock:
        data = _load_data()
        user_files = [f for f in data['files'] if f['user_id'] == str(user_id)]
        # Sort newest first
        user_files.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return user_files


def json_get_file_by_id(file_id: str) -> dict | None:
    with _lock:
        data = _load_data()
        for f in data['files']:
            if f['_id'] == str(file_id):
                return f
        return None


def json_delete_file_record(file_id: str) -> bool:
    with _lock:
        data = _load_data()
        initial_len = len(data['files'])
        data['files'] = [f for f in data['files'] if f['_id'] != str(file_id)]
        if len(data['files']) < initial_len:
            _save_data(data)
            return True
        return False


# ── History API ──────────────────────────────────────────────────────────────

def json_save_history(user_id: str, file_id: str, operation: str,
                      result: str, metadata: dict | None = None) -> dict | None:
    with _lock:
        data = _load_data()
        history_doc = {
            '_id': str(uuid.uuid4()),
            'user_id': str(user_id),
            'file_id': str(file_id),
            'operation': operation,
            'result': result,
            'metadata': metadata or {},
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        data['history'].append(history_doc)
        _save_data(data)
        return history_doc


def json_get_user_history(user_id: str, limit: int = 50) -> list:
    with _lock:
        data = _load_data()
        user_history = [h for h in data['history'] if h['user_id'] == str(user_id)]
        # Sort newest first
        user_history.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return user_history[:limit]


# ── Chat API ─────────────────────────────────────────────────────────────────

def json_save_chat(user_id: str, file_id: str, messages: list) -> dict | None:
    with _lock:
        data = _load_data()
        chat_doc = {
            '_id': str(uuid.uuid4()),
            'user_id': str(user_id),
            'file_id': str(file_id),
            'messages': messages,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }
        data['chats'].append(chat_doc)
        _save_data(data)
        return chat_doc


def json_get_chat(chat_id: str) -> dict | None:
    with _lock:
        data = _load_data()
        for c in data['chats']:
            if c['_id'] == str(chat_id):
                return c
        return None


def json_get_chat_by_file(user_id: str, file_id: str) -> dict | None:
    with _lock:
        data = _load_data()
        chats = [c for c in data['chats'] if c['user_id'] == str(user_id) and c['file_id'] == str(file_id)]
        if not chats:
            return None
        # Return newest updated
        chats.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        return chats[0]


def json_update_chat_messages(chat_id: str, messages: list) -> bool:
    with _lock:
        data = _load_data()
        for c in data['chats']:
            if c['_id'] == str(chat_id):
                c['messages'] = messages
                c['updated_at'] = datetime.now(timezone.utc).isoformat()
                _save_data(data)
                return True
        return False


def json_get_user_chats(user_id: str) -> list:
    with _lock:
        data = _load_data()
        user_chats = [c for c in data['chats'] if c['user_id'] == str(user_id)]
        user_chats.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        return user_chats
