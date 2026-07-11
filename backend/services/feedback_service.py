import os
import json
from datetime import datetime, timezone
from database.db import get_db

# Fallback JSON file path
FEEDBACK_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'feedback.json')

def save_feedback(user_id: str | None, rating: int, message: str | None, page: str | None, user_agent: str | None) -> dict | None:
    db = get_db()
    feedback_doc = {
        'user_id': user_id,
        'rating': rating,
        'message': message,
        'page': page,
        'user_agent': user_agent,
        'created_at': datetime.now(timezone.utc)
    }

    if db is None:
        # Save to local JSON fallback
        try:
            entries = []
            if os.path.isfile(FEEDBACK_JSON):
                with open(FEEDBACK_JSON, 'r', encoding='utf-8') as f:
                    entries = json.load(f)
            
            # Serialize datetime
            doc_serialized = feedback_doc.copy()
            doc_serialized['created_at'] = feedback_doc['created_at'].isoformat()
            doc_serialized['_id'] = str(len(entries) + 1)
            
            entries.append(doc_serialized)
            with open(FEEDBACK_JSON, 'w', encoding='utf-8') as f:
                json.dump(entries, f, indent=2)
            return doc_serialized
        except Exception as e:
            print(f"[FeedbackService] JSON save fallback error: {e}")
            return None

    try:
        result = db.feedback.insert_one(feedback_doc)
        feedback_doc['_id'] = result.inserted_id
        return feedback_doc
    except Exception as e:
        print(f"[FeedbackService] MongoDB insert error: {e}")
        return None

def get_feedback_list(page: int = 1, limit: int = 10) -> tuple[list[dict], int]:
    db = get_db()
    skip = (page - 1) * limit

    if db is None:
        try:
            if not os.path.isfile(FEEDBACK_JSON):
                return [], 0
            with open(FEEDBACK_JSON, 'r', encoding='utf-8') as f:
                entries = json.load(f)
            # Sort by created_at newest first
            entries.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            total = len(entries)
            paginated = entries[skip:skip + limit]
            return paginated, total
        except Exception:
            return [], 0

    try:
        total = db.feedback.count_documents({})
        cursor = db.feedback.find().sort('created_at', -1).skip(skip).limit(limit)
        results = []
        for doc in cursor:
            doc['_id'] = str(doc['_id'])
            if isinstance(doc.get('created_at'), datetime):
                doc['created_at'] = doc['created_at'].isoformat()
            results.append(doc)
        return results, total
    except Exception as e:
        print(f"[FeedbackService] MongoDB query error: {e}")
        return [], 0

def get_feedback_stats() -> dict:
    db = get_db()
    if db is None:
        try:
            if not os.path.isfile(FEEDBACK_JSON):
                return {'average_rating': 0.0, 'total_count': 0}
            with open(FEEDBACK_JSON, 'r', encoding='utf-8') as f:
                entries = json.load(f)
            if not entries:
                return {'average_rating': 0.0, 'total_count': 0}
            ratings = [float(e['rating']) for e in entries if 'rating' in e]
            avg = sum(ratings) / len(ratings) if ratings else 0.0
            return {'average_rating': round(avg, 2), 'total_count': len(entries)}
        except Exception:
            return {'average_rating': 0.0, 'total_count': 0}

    try:
        pipeline = [
            {
                '$group': {
                    '_id': None,
                    'avg_rating': {'$avg': '$rating'},
                    'count': {'$sum': 1}
                }
            }
        ]
        result = list(db.feedback.aggregate(pipeline))
        if not result:
            return {'average_rating': 0.0, 'total_count': 0}
        return {
            'average_rating': round(result[0]['avg_rating'], 2),
            'total_count': result[0]['count']
        }
    except Exception as e:
        print(f"[FeedbackService] MongoDB aggregation error: {e}")
        return {'average_rating': 0.0, 'total_count': 0}
