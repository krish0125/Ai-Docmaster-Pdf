import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))


class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-dev-secret')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5500')

    TIDB_HOST = os.getenv('TIDB_HOST', '')
    TIDB_PORT = os.getenv('TIDB_PORT', '4000')
    TIDB_USER = os.getenv('TIDB_USER', '')
    TIDB_PASSWORD = os.getenv('TIDB_PASSWORD', '')
    TIDB_DB_NAME = os.getenv('TIDB_DB_NAME', 'ai_docmaster')
    
    import certifi
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{TIDB_USER}:{TIDB_PASSWORD}@{TIDB_HOST}:{TIDB_PORT}/"
        f"{TIDB_DB_NAME}?ssl_ca={certifi.where()}"
    )

    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    # Legacy: GROK_API_KEY kept temporarily for rollback reference only
    GROK_API_KEY = os.getenv('GROK_API_KEY', '')  # TODO: remove after Render env vars updated
    TESSERACT_PATH = os.getenv('TESSERACT_PATH', r'C:\Program Files\Tesseract-OCR\tesseract.exe' if os.name == 'nt' else 'tesseract')

    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 52428800))  # 50MB
    ALLOWED_EXTENSIONS = {
        # PDF
        'pdf',
        # Images
        'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'webp',
        # Office
        'docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt',
        # Text / markup
        'txt', 'html', 'htm', 'md',
        # eBook
        'epub',
        # Archives
        'zip',
    }
    # Poppler binaries for pdf2image (Windows: set path in .env)
    POPPLER_PATH = os.getenv('POPPLER_PATH', None)

    FLASK_DEBUG = os.getenv('FLASK_DEBUG', '0') == '1'
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@aidocmaster.com')
    ALLOWED_CORS_ORIGINS = os.getenv('ALLOWED_CORS_ORIGINS', 'http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000')

    # OAuth – Google
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', '')

    # OAuth – GitHub
    GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID', '')
    GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET', '')
    GITHUB_REDIRECT_URI = os.getenv('GITHUB_REDIRECT_URI', '')

