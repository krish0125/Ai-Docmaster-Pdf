from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from middleware.auth import admin_required
from services.feedback_service import save_feedback, get_feedback_list, get_feedback_stats

feedback_bp = Blueprint('feedback', __name__)

@feedback_bp.route('', methods=['POST'])
@jwt_required(optional=True)
def create_feedback():
    """Create a new user feedback entry. JWT is optional (allows anonymous feedback)."""
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        rating = data.get('rating')
        message = data.get('message', '')
        page = data.get('page', '')

        # --- Validation ---
        if rating is None:
            return jsonify({'error': 'Rating is required'}), 400
        
        try:
            rating = int(rating)
        except (ValueError, TypeError):
            return jsonify({'error': 'Rating must be an integer'}), 400

        if rating < 1 or rating > 5:
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400

        # Cap message at 1000 characters
        if message and len(message) > 1000:
            message = message[:1000]

        # Get user ID from JWT if present
        user_id = get_jwt_identity()

        user_agent = request.headers.get('User-Agent', '')

        feedback = save_feedback(
            user_id=user_id,
            rating=rating,
            message=message,
            page=page,
            user_agent=user_agent
        )

        if not feedback:
            return jsonify({'error': 'Could not save feedback. Storage unreachable.'}), 503

        return jsonify({
            'message': 'Thank you for your feedback!',
            'feedback_id': str(feedback.get('_id'))
        }), 201

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@feedback_bp.route('', methods=['GET'])
@jwt_required()
@admin_required
def list_feedback():
    """Retrieve all user feedback entries (paginated) and stats. Admin privileges required."""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)

        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 10

        entries, total = get_feedback_list(page=page, limit=limit)
        stats = get_feedback_stats()

        return jsonify({
            'feedback': entries,
            'total': total,
            'page': page,
            'limit': limit,
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

