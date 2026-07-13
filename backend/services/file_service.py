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

    # Upload to R2, delete local if successful
    if upload_to_r2(file_path, filename):
        try:
            os.remove(file_path)
        except Exception:
            pass

    return {
        'filename': filename,
        'original_name': original_name,
        'file_path': file_path,
        'size': size,
        'file_type': file_type,
    }


def delete_file(file_path: str) -> bool:
    """Delete a file from disk and R2. Returns True if deleted, False otherwise."""
    filename = os.path.basename(file_path)
    delete_from_r2(filename)
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

def get_s3_client():
    """Return a boto3 client for Cloudflare R2 if configured."""
    account_id = os.getenv('R2_ACCOUNT_ID')
    access_key = os.getenv('R2_ACCESS_KEY_ID')
    secret_key = os.getenv('R2_SECRET_ACCESS_KEY')
    
    if not (account_id and access_key and secret_key):
        return None
    try:
        import boto3
        from botocore.config import Config as BotoConfig
        return boto3.client(
            's3',
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name='auto',
            config=BotoConfig(signature_version='s3v4')
        )
    except ImportError:
        return None

def upload_to_r2(local_file_path: str, object_name: str) -> bool:
    """Upload a local file to Cloudflare R2."""
    s3 = get_s3_client()
    bucket = os.getenv('R2_BUCKET_NAME')
    if s3 is None or not bucket:
        return False
    try:
        s3.upload_file(local_file_path, bucket, object_name)
        return True
    except Exception as e:
        print(f"[R2] Upload error: {e}")
        return False

def download_from_r2(object_name: str, download_path: str) -> bool:
    """Download a file from Cloudflare R2 to local disk."""
    s3 = get_s3_client()
    bucket = os.getenv('R2_BUCKET_NAME')
    if s3 is None or not bucket:
        return False
    try:
        s3.download_file(bucket, object_name, download_path)
        return True
    except Exception as e:
        print(f"[R2] Download error: {e}")
        return False

def delete_from_r2(object_name: str) -> bool:
    """Delete a file from Cloudflare R2."""
    s3 = get_s3_client()
    bucket = os.getenv('R2_BUCKET_NAME')
    if s3 is None or not bucket:
        return False
    try:
        s3.delete_object(Bucket=bucket, Key=object_name)
        return True
    except Exception as e:
        print(f"[R2] Delete error: {e}")
        return False
