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
    CORS(
    app,
    origins=[
        'http://localhost:5500',
        'http://127.0.0.1:5500',
        'http://localhost:5501',        # ← ADD THIS LINE
        'http://127.0.0.1:5501',        # ← ADD THIS LINE
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:8080',
        'http://127.0.0.1:8080',
        'null',
    ],
    supports_credentials=True,
    allow_headers=['Content-Type', 'Authorization'],
    methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
)

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

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(pdf_bp,  url_prefix='/pdf')
    app.register_blueprint(ocr_bp,  url_prefix='/ocr')
    app.register_blueprint(ai_bp,   url_prefix='/ai')
    app.register_blueprint(file_bp, url_prefix='/files')

    # ── Health check ───────────────────────────────────────────────────
    @app.route('/health', methods=['GET'])
    def health():
        """Quick health-check endpoint."""
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

    return app


# ── Main ────────────────────────────────────────────────────────────────
app = create_app()

if __name__ == '__main__':
    print("=" * 50)
    print("  AI DocMaster Backend")
    print("  http://localhost:5001")
    print("=" * 50)
    app.run(debug=True, port=5001)
