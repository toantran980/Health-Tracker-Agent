"""health.py — Health check and health insights endpoints."""

from datetime import datetime

from flask import Blueprint, jsonify

from api.blueprints import state
from api.blueprints.helpers import require_user

health_bp = Blueprint('health', __name__)


@health_bp.route('/api/health', methods=['GET'])
def health_check():
    """Liveness probe — returns 200 when the server is running."""
    persisted_users = (
        state.mongo_store.count_users() if state.mongo_store.enabled else len(state.users)
    )
    return jsonify({
        "status":    "healthy",
        "timestamp": datetime.now().isoformat(),
        "users":     persisted_users,
        "mongodb": {
            "enabled":  state.mongo_store.enabled,
            "uri":      state.mongo_store.uri if state.mongo_store.enabled else None,
            "database": state.mongo_store.db_name if state.mongo_store.enabled else None,
        },
    }), 200


@health_bp.route('/api/insights/<user_id>', methods=['GET'])
def get_health_insights(user_id):
    """Return a combined summary of the user's health metrics and module status."""
    user, err = require_user(user_id)
    if err:
        return err

    return jsonify({
        "user_profile": {
            "name":      user.name,
            "age":       user.age,
            "weight_kg": user.current_weight_kg,
            "goals":     [g.value for g in user.goals],
        },
        "nutritional_metrics": {
            "bmr":             round(user.get_bmr(), 1),
            "tdee":            user.get_tdee(),
            "target_calories": user.target_calories,
        },
        "ai_modules_status": {
            "knowledge_base":     user_id in state.knowledge_bases,
            "nutrition_analyzer": user_id in state.nutrition_analyzers,
            "meal_recommender":   user_id in state.meal_recommenders,
        },
    }), 200
