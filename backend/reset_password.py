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
        from pymongo import MongoClient
        client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=3000)
        client.admin.command('ping')
        db = client[Config.MONGO_DB_NAME]
        
        user = db.users.find_one({'email': EMAIL.lower().strip()})
        if user is None:
            print(f"No user found with email: {EMAIL}")
            return
        
        pw_hash = bcrypt.hashpw(NEW_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        db.users.update_one({'email': EMAIL.lower().strip()}, {'$set': {'password': pw_hash}})
        print(f"[OK] Password for {EMAIL} reset to: {NEW_PASSWORD}")
    except Exception as e:
        print(f"MongoDB unavailable: {e}")
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
            print("No local_db.json found. MongoDB must be used.")

if __name__ == '__main__':
    reset_password()
