import os
import json
from datetime import datetime, timezone
from sqlalchemy import func
from database.db import get_db
from database.models import Feedback
import database.json_db as jdb

# Fallback JSON file path
FEEDBACK_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'feedback.json')

def _parse_id(id_str):
    if not id_str:
        return None
    try:
        return int(id_str)
    except ValueError:
        return None

def save_feedback(user_id: str | None, rating: int, message: str | None, page: str | None, user_agent: str | None) -> dict | None:
    session = get_db()

    if session is None:
        # Save to local JSON fallback
        try:
            entries = []
            if os.path.isfile(FEEDBACK_JSON):
                with open(FEEDBACK_JSON, 'r', encoding='utf-8') as f:
                    entries = json.load(f)
            
            doc_serialized = {
                'user_id': user_id,
                'rating': rating,
                'message': message,
                'page': page,
                'user_agent': user_agent,
                'created_at': datetime.now(timezone.utc).isoformat(),
                '_id': str(len(entries) + 1)
            }
            
            entries.append(doc_serialized)
            with open(FEEDBACK_JSON, 'w', encoding='utf-8') as f:
                json.dump(entries, f, indent=2)
            return doc_serialized
        except Exception as e:
            print(f"[FeedbackService] JSON save fallback error: {e}")
            return None

    try:
        uid = _parse_id(user_id) if user_id else None
        f = Feedback(
            user_id=uid,
            rating=rating,
            message=message,
            page=page,
            user_agent=user_agent
        )
        session.add(f)
        session.commit()
        session.refresh(f)
        return f.to_dict()
    except Exception as e:
        session.rollback()
        print(f"[FeedbackService] TiDB insert error: {e}")
        return None

def get_feedback_list(page: int = 1, limit: int = 10) -> tuple[list[dict], int]:
    session = get_db()
    skip = (page - 1) * limit

    if session is None:
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
        total = session.query(func.count(Feedback.id)).scalar()
        feedbacks = session.query(Feedback).order_by(Feedback.created_at.desc()).offset(skip).limit(limit).all()
        results = []
        for f in feedbacks:
            doc = f.to_dict()
            if isinstance(doc.get('created_at'), datetime):
                doc['created_at'] = doc['created_at'].isoformat()
            results.append(doc)
        return results, total
    except Exception as e:
        print(f"[FeedbackService] TiDB query error: {e}")
        return [], 0

def get_feedback_stats() -> dict:
    session = get_db()
    if session is None:
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
        result = session.query(
            func.avg(Feedback.rating).label('avg_rating'),
            func.count(Feedback.id).label('count')
        ).first()
        
        if not result or result.count == 0:
            return {'average_rating': 0.0, 'total_count': 0}
            
        return {
            'average_rating': round(float(result.avg_rating), 2),
            'total_count': result.count
        }
    except Exception as e:
        print(f"[FeedbackService] TiDB aggregation error: {e}")
        return {'average_rating': 0.0, 'total_count': 0}
