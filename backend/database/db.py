from pymongo import MongoClient
from config import Config

client = None
db = None


def get_db():
    """Get MongoDB database instance. Creates connection on first call.
    Returns None if MongoDB is not available so routes can handle gracefully."""
    global client, db
    if db is None:
        try:
            client = MongoClient(
                Config.MONGO_URI,
                serverSelectionTimeoutMS=3000,
                connectTimeoutMS=3000,
            )
            # Force a connection attempt to detect failures early
            client.admin.command('ping')
            db = client[Config.MONGO_DB_NAME]

            # Create indexes for performance
            db.users.create_index('email', unique=True)
            db.files.create_index('user_id')
            db.history.create_index('user_id')
            db.chat.create_index('user_id')
            print(f"[DB] Connected to MongoDB: {Config.MONGO_DB_NAME}")
        except Exception as e:
            print(f"[DB] MongoDB connection error: {e}")
            client = None
            db = None
            return None
    return db


def close_db():
    """Close the MongoDB connection."""
    global client, db
    if client:
        client.close()
        client = None
        db = None
