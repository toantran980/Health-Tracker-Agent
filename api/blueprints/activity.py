"""activity.py — Activity recommendation endpoints."""

from flask import Blueprint, request, jsonify
from api.blueprints import state
from api.blueprints.helpers import require_user, error_response
from ai_modules.activity_recommendation_engine import ActivityRecommendationEngine

activity_bp = Blueprint('activity', __name__)

@activity_bp.route('/api/activity-recommendations/<user_id>', methods=['GET'])
def get_activity_recommendations(user_id):
    """Return personalized activity recommendations for the user."""
    user, err = require_user(user_id)
    if err:
        return err

    recommender = ActivityRecommendationEngine(user)
    n = request.args.get('n', 5, type=int)
    recommendations = recommender.recommend(n=n)
    return jsonify({
        "recommendations": recommendations,
        "count": len(recommendations)
    }), 200