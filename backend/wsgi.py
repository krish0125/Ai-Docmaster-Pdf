import os
import sys

# Ensure the backend directory is in the import path
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app import create_app

app = create_app()

if __name__ == '__main__':
    # For development runs
    app.run(port=5001)
