"""File utility service — save, validate, delete uploads."""

import os
import uuid
from werkzeug.utils import secure_filename


def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """Check whether *filename* has one of the allowed extensions."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed_extensions


def generate_unique_filename(original_name: str) -> str:
    """Return a UUID-based filename that preserves the original extension."""
    ext = ''
    if '.' in original_name:
        ext = '.' + original_name.rsplit('.', 1)[1].lower()
    return f"{uuid.uuid4().hex}{ext}"


def save_upload(file, upload_folder: str) -> dict:
    """Save a Werkzeug FileStorage object to *upload_folder*.

    Returns a dict with metadata about the saved file.
    Raises ValueError if the file object is invalid.
    """
    if file is None or file.filename == '':
        raise ValueError('No file provided')

    original_name = secure_filename(file.filename)
    if not original_name:
        original_name = 'unnamed_file'

    filename = generate_unique_filename(original_name)
    file_path = os.path.join(upload_folder, filename)

    os.makedirs(upload_folder, exist_ok=True)
    file.save(file_path)

    size = os.path.getsize(file_path)
    file_type = original_name.rsplit('.', 1)[1].lower() if '.' in original_name else 'unknown'

    return {
        'filename': filename,
        'original_name': original_name,
        'file_path': file_path,
        'size': size,
        'file_type': file_type,
    }


def delete_file(file_path: str) -> bool:
    """Delete a file from disk. Returns True if deleted, False otherwise."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        print(f"[FileService] delete_file error: {e}")
        return False


def get_file_size_formatted(size_bytes: int) -> str:
    """Format byte count to a human-readable string (KB / MB / GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
