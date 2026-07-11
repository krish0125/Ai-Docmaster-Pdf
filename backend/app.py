"""AI DocMaster — Flask Application Entry Point.

Application factory pattern with blueprint registration, CORS, JWT, and
error handlers.  The app starts and runs even when MongoDB, Tesseract, or
Gemini are not configured.
"""

import os
import sys

# Ensure the backend directory is on sys.path so that absolute imports
# like ``from config import Config`` work regardless of the working
# directory used to launch the app.
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config import Config


def create_app() -> Flask:
    """Application factory — create and configure the Flask app."""

    app = Flask(__name__)

    # ── Configuration ──────────────────────────────────────────────────
    app.config['SECRET_KEY'] = Config.SECRET_KEY
    app.config['JWT_SECRET_KEY'] = Config.JWT_SECRET_KEY
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = Config.JWT_ACCESS_TOKEN_EXPIRES
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

    # ── CORS ───────────────────────────────────────────────────────────
    cors_origins = Config.ALLOWED_CORS_ORIGINS
    if cors_origins:
        origins_list = [o.strip() for o in cors_origins.split(',') if o.strip()]
    else:
        origins_list = [
            "http://127.0.0.1:5500",
            "http://localhost:5500",
            "http://127.0.0.1:5501",
            "http://localhost:5501"
        ]
    CORS(
        app,
        origins=origins_list,
        supports_credentials=True
    )

    app.debug = Config.FLASK_DEBUG


    # ── JWT ─────────────────────────────────────────────────────────────
    JWTManager(app)

    # ── Upload folder ──────────────────────────────────────────────────
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    # ── Blueprints ─────────────────────────────────────────────────────
    from routes.auth_routes import auth_bp
    from routes.pdf_routes import pdf_bp
    from routes.ocr_routes import ocr_bp
    from routes.ai_routes import ai_bp
    from routes.file_routes import file_bp
    from routes.feedback_routes import feedback_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(pdf_bp,  url_prefix='/pdf')
    app.register_blueprint(ocr_bp,  url_prefix='/ocr')
    app.register_blueprint(ai_bp,   url_prefix='/ai')
    app.register_blueprint(file_bp, url_prefix='/files')
    app.register_blueprint(feedback_bp, url_prefix='/feedback')

    # Phase 2+ blueprints — each is guarded so missing files don't crash the server
    _phase_blueprints = [
        ('routes.convert_routes',      'convert_bp',      '/convert'),
        ('routes.edit_routes',         'edit_bp',         '/edit'),
        ('routes.security_routes',     'security_bp',     '/security'),
        ('routes.image_routes',        'image_bp',        '/image'),
        ('routes.utility_routes',      'utility_bp',      '/utils'),
        ('routes.productivity_routes', 'productivity_bp', '/productivity'),
    ]
    for _module, _attr, _prefix in _phase_blueprints:
        try:
            import importlib
            _mod = importlib.import_module(_module)
            _bp  = getattr(_mod, _attr)
            app.register_blueprint(_bp, url_prefix=_prefix)
            print(f'[App] Registered blueprint: {_prefix}')
        except (ImportError, AttributeError) as _e:
            print(f'[App] Skipping {_module}: {_e}')

    # ── Health check ───────────────────────────────────────────────────
    @app.route('/health', methods=['GET'])
    def health():
        """Quick health-check endpoint."""
        import subprocess
        status: dict = {
            'status': 'running',
            'service': 'AI DocMaster Backend',
        }

        # Check MongoDB
        try:
            from database.db import get_db
            db = get_db()
            status['mongodb'] = 'connected' if db is not None else 'unavailable'
        except Exception:
            status['mongodb'] = 'unavailable'

        # Check Gemini
        status['gemini_configured'] = bool(Config.GEMINI_API_KEY)

        # Check Tesseract
        status['tesseract_found'] = os.path.isfile(Config.TESSERACT_PATH)

        # Check Poppler (for PDF-to-image)
        poppler_found = False
        poppler_path = getattr(Config, 'POPPLER_PATH', None) or os.environ.get('POPPLER_PATH')
        if poppler_path and os.path.isdir(poppler_path):
            poppler_found = (
                os.path.isfile(os.path.join(poppler_path, 'pdfinfo.exe')) or
                os.path.isfile(os.path.join(poppler_path, 'pdfinfo'))
            )
        if not poppler_found:
            try:
                res = subprocess.run(['pdfinfo', '-v'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                poppler_found = (res.returncode == 0)
            except Exception:
                pass
        status['poppler_found'] = poppler_found

        # Check LibreOffice (for Office-to-PDF)
        soffice_found = False
        common_soffice_paths = [
            r'C:\Program Files\LibreOffice\program\soffice.exe',
            r'C:\Program Files (x86)\LibreOffice\program\soffice.exe'
        ]
        for p in common_soffice_paths:
            if os.path.isfile(p):
                soffice_found = True
                break
        if not soffice_found:
            try:
                res = subprocess.run(['soffice', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                soffice_found = (res.returncode == 0)
            except Exception:
                pass
        status['libreoffice_found'] = soffice_found

        # Check wkhtmltopdf (for HTML-to-PDF)
        wk_found = False
        common_wk_paths = [
            r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
            r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe'
        ]
        for p in common_wk_paths:
            if os.path.isfile(p):
                wk_found = True
                break
        if not wk_found:
            try:
                res = subprocess.run(['wkhtmltopdf', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                wk_found = (res.returncode == 0)
            except Exception:
                pass
        status['wkhtmltopdf_found'] = wk_found

        return jsonify(status), 200

    # ── Error handlers ─────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(413)
    def request_entity_too_large(error):
        max_mb = Config.MAX_CONTENT_LENGTH / (1024 * 1024)
        return jsonify({
            'error': f'File too large. Maximum size is {max_mb:.0f} MB.',
        }), 413

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500

    _run_startup_checks()

    return app


def _run_startup_checks():
    """Run production-ready self-checks on boot and log to console."""
    print("=" * 60)
    print("  AI DocMaster Startup Self-Check")
    print("=" * 60)

    # 1. Check MongoDB
    try:
        from database.db import get_db
        db = get_db()
        if db is not None:
            print("[Startup Check] MongoDB: CONNECTED")
        else:
            print("[Startup Check] MongoDB: WARNING - Unreachable (graceful mode)")
    except Exception as e:
        print(f"[Startup Check] MongoDB: ERROR - {e}")

    # 2. Check Gemini key
    key = Config.GEMINI_API_KEY
    if not key:
        print("[Startup Check] Gemini API Key: WARNING - Missing (AI engines will fail)")
    elif key in ('placeholder', 'your-gemini-api-key', 'dev-key'):
        print("[Startup Check] Gemini API Key: WARNING - Using default/placeholder key")
    else:
        print("[Startup Check] Gemini API Key: CONFIGURED")

    # 3. Check Tesseract path
    if os.path.isfile(Config.TESSERACT_PATH):
        print("[Startup Check] Tesseract OCR: FOUND")
    else:
        print(f"[Startup Check] Tesseract OCR: WARNING - Not found at path: {Config.TESSERACT_PATH}")

    # 4. Check Upload Folder write access
    try:
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        test_file = os.path.join(Config.UPLOAD_FOLDER, '.startup_write_test')
        with open(test_file, 'w') as f:
            f.write('write test')
        os.remove(test_file)
        print("[Startup Check] Upload Directory: WRITABLE")
    except Exception as e:
        print(f"[Startup Check] Upload Directory: ERROR - Not writable: {e}")

    # 5. Check Dev Secrets
    if Config.SECRET_KEY in ('dev-secret-key', 'placeholder', ''):
        print("[SECURITY WARNING] Flask SECRET_KEY is using a dev-only default placeholder!")
    if Config.JWT_SECRET_KEY in ('jwt-dev-secret', 'placeholder', ''):
        print("[SECURITY WARNING] JWT_SECRET_KEY is using a dev-only default placeholder!")

    print("=" * 60)


# ── Main ────────────────────────────────────────────────────────────────
app = create_app()

if __name__ == '__main__':
    print("=" * 50)
    print("  AI DocMaster Backend")
    print("  http://localhost:5001")
    print("=" * 50)
    app.run(debug=Config.FLASK_DEBUG, use_reloader=Config.FLASK_DEBUG, port=5001)

