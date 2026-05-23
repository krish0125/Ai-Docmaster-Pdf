from datetime import datetime, timezone
from bson import ObjectId
from database.db import get_db
import database.json_db as jdb


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def create_user(name: str, email: str, password_hash: str) -> dict | None:
    """Insert a new user document. Returns the created user dict or None on failure."""
    db = get_db()
    if db is None:
        return jdb.json_create_user(name, email, password_hash)
    try:
        user_doc = {
            'name': name,
            'email': email.lower().strip(),
            'password': password_hash,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
        }
        result = db.users.insert_one(user_doc)
        user_doc['_id'] = result.inserted_id
        return user_doc
    except Exception as e:
        print(f"[Models] create_user error: {e}")
        return None


def find_user_by_email(email: str) -> dict | None:
    """Find a user by email address."""
    db = get_db()
    if db is None:
        return jdb.json_find_user_by_email(email)
    try:
        return db.users.find_one({'email': email.lower().strip()})
    except Exception as e:
        print(f"[Models] find_user_by_email error: {e}")
        return None


def find_user_by_id(user_id: str) -> dict | None:
    """Find a user by their ObjectId string."""
    db = get_db()
    if db is None:
        return jdb.json_find_user_by_id(user_id)
    try:
        return db.users.find_one({'_id': ObjectId(user_id)})
    except Exception as e:
        print(f"[Models] find_user_by_id error: {e}")
        return None


def update_user(user_id: str, update_fields: dict) -> bool:
    """Update user fields. Returns True on success."""
    db = get_db()
    if db is None:
        return jdb.json_update_user(user_id, update_fields)
    try:
        update_fields['updated_at'] = datetime.now(timezone.utc)
        result = db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_fields},
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"[Models] update_user error: {e}")
        return False


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

def save_file_record(user_id: str, filename: str, original_name: str,
                     file_type: str, file_path: str, size: int) -> dict | None:
    """Save a file metadata record. Returns the document or None."""
    db = get_db()
    if db is None:
        return jdb.json_save_file_record(user_id, filename, original_name, file_type, file_path, size)
    try:
        file_doc = {
            'user_id': user_id,
            'filename': filename,
            'original_name': original_name,
            'file_type': file_type,
            'file_path': file_path,
            'size': size,
            'created_at': datetime.now(timezone.utc),
        }
        result = db.files.insert_one(file_doc)
        file_doc['_id'] = result.inserted_id
        return file_doc
    except Exception as e:
        print(f"[Models] save_file_record error: {e}")
        return None


def get_user_files(user_id: str) -> list:
    """Return all file records for a user, newest first."""
    db = get_db()
    if db is None:
        return jdb.json_get_user_files(user_id)
    try:
        cursor = db.files.find({'user_id': user_id}).sort('created_at', -1)
        return list(cursor)
    except Exception as e:
        print(f"[Models] get_user_files error: {e}")
        return []


def get_file_by_id(file_id: str) -> dict | None:
    """Get a single file record by its _id."""
    db = get_db()
    if db is None:
        return jdb.json_get_file_by_id(file_id)
    try:
        return db.files.find_one({'_id': ObjectId(file_id)})
    except Exception as e:
        print(f"[Models] get_file_by_id error: {e}")
        return None


def delete_file_record(file_id: str) -> bool:
    """Delete a file record from the database. Returns True on success."""
    db = get_db()
    if db is None:
        return jdb.json_delete_file_record(file_id)
    try:
        result = db.files.delete_one({'_id': ObjectId(file_id)})
        return result.deleted_count > 0
    except Exception as e:
        print(f"[Models] delete_file_record error: {e}")
        return False


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

def save_history(user_id: str, file_id: str, operation: str,
                 result: str, metadata: dict | None = None) -> dict | None:
    """Save an operation history entry."""
    db = get_db()
    if db is None:
        return jdb.json_save_history(user_id, file_id, operation, result, metadata)
    try:
        history_doc = {
            'user_id': user_id,
            'file_id': file_id,
            'operation': operation,
            'result': result,
            'metadata': metadata or {},
            'created_at': datetime.now(timezone.utc),
        }
        db_result = db.history.insert_one(history_doc)
        history_doc['_id'] = db_result.inserted_id
        return history_doc
    except Exception as e:
        print(f"[Models] save_history error: {e}")
        return None


def get_user_history(user_id: str, limit: int = 50) -> list:
    """Return recent operation history for a user."""
    db = get_db()
    if db is None:
        return jdb.json_get_user_history(user_id, limit)
    try:
        cursor = (
            db.history.find({'user_id': user_id})
            .sort('created_at', -1)
            .limit(limit)
        )
        return list(cursor)
    except Exception as e:
        print(f"[Models] get_user_history error: {e}")
        return []


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

def save_chat(user_id: str, file_id: str, messages: list) -> dict | None:
    """Create a new chat session."""
    db = get_db()
    if db is None:
        return jdb.json_save_chat(user_id, file_id, messages)
    try:
        chat_doc = {
            'user_id': user_id,
            'file_id': file_id,
            'messages': messages,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
        }
        result = db.chat.insert_one(chat_doc)
        chat_doc['_id'] = result.inserted_id
        return chat_doc
    except Exception as e:
        print(f"[Models] save_chat error: {e}")
        return None


def get_chat(chat_id: str) -> dict | None:
    """Retrieve a chat session by its _id."""
    db = get_db()
    if db is None:
        return jdb.json_get_chat(chat_id)
    try:
        return db.chat.find_one({'_id': ObjectId(chat_id)})
    except Exception as e:
        print(f"[Models] get_chat error: {e}")
        return None


def get_chat_by_file(user_id: str, file_id: str) -> dict | None:
    """Retrieve the most recent chat session for a user + file pair."""
    db = get_db()
    if db is None:
        return jdb.json_get_chat_by_file(user_id, file_id)
    try:
        return db.chat.find_one(
            {'user_id': user_id, 'file_id': file_id},
            sort=[('updated_at', -1)],
        )
    except Exception as e:
        print(f"[Models] get_chat_by_file error: {e}")
        return None


def update_chat_messages(chat_id: str, messages: list) -> bool:
    """Append / replace the messages list in an existing chat."""
    db = get_db()
    if db is None:
        return jdb.json_update_chat_messages(chat_id, messages)
    try:
        result = db.chat.update_one(
            {'_id': ObjectId(chat_id)},
            {'$set': {'messages': messages, 'updated_at': datetime.now(timezone.utc)}},
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"[Models] update_chat_messages error: {e}")
        return False


def get_user_chats(user_id: str) -> list:
    """Return all chat sessions for a user, newest first."""
    db = get_db()
    if db is None:
        return jdb.json_get_user_chats(user_id)
    try:
        cursor = db.chat.find({'user_id': user_id}).sort('updated_at', -1)
        return list(cursor)
    except Exception as e:
        print(f"[Models] get_user_chats error: {e}")
        return []
