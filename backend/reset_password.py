"""One-time script to reset the password for an account."""
import sys
import os

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from config import Config
import bcrypt

# Load dotenv
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(_BACKEND_DIR), '.env'))

EMAIL = "demo123@gmail.com"
NEW_PASSWORD = "demo123456"

def reset_password():
    try:
        from database.db import get_db
        from database.models import User
        session = get_db()
        if session is None:
            raise Exception("Database session unavailable")
            
        user = session.query(User).filter(User.email == EMAIL.lower().strip()).first()
        if user is None:
            print(f"No user found with email: {EMAIL}")
            return
        
        pw_hash = bcrypt.hashpw(NEW_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user.password = pw_hash
        session.commit()
        print(f"[OK] Password for {EMAIL} reset to: {NEW_PASSWORD}")
    except Exception as e:
        print(f"TiDB unavailable: {e}")
        # Try JSON DB fallback
        import json
        db_file = os.path.join(_BACKEND_DIR, 'database', 'local_db.json')
        if os.path.exists(db_file):
            with open(db_file, 'r') as f:
                data = json.load(f)
            users = data.get('users', [])
            found = False
            for u in users:
                if u.get('email', '').lower() == EMAIL.lower():
                    pw_hash = bcrypt.hashpw(NEW_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    u['password'] = pw_hash
                    found = True
                    break
            if found:
                with open(db_file, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                print(f"[OK] Password reset in local JSON DB for {EMAIL} -> {NEW_PASSWORD}")
            else:
                print(f"User not found in JSON DB either.")
        else:
            print("No local_db.json found. Database must be used.")

if __name__ == '__main__':
    reset_password()
