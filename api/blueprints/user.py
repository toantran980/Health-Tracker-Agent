import sys
import traceback
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from api.blueprints import state
from api.blueprints.helpers import (
    coerce_float,
    coerce_int,
    ensure_ai_modules,
    error_response,
    require_user,
    require_user_and_auth,
    save_user_with_hash,
)
from models.user_profile import BiologicalSex, Goal, UserProfile

user_bp = Blueprint('user', __name__)


@user_bp.route('/api/user/create', methods=['POST'])
def create_user():
    """
    Create a new user profile and initialise all AI modules.

    Body (JSON):
        user_id, name, age, weight_kg, height_cm, biological_sex,
        goals, target_calories, target_protein_g, target_carbs_g, target_fat_g,
        password (optional; enables /api/auth/login)
    """
    data = request.get_json(silent=True) or request.form.to_dict()

    # Assign and validate user_id uniqueness
    raw_user_id = data.get('user_id')
    if raw_user_id:
        user_id = str(raw_user_id).strip()
        existing = state.users.get(user_id)
        if not existing and state.mongo_store.enabled:
            existing = state.mongo_store.get_user(user_id)
        if existing:
            return error_response(f"User '{user_id}' already exists", "USER_ALREADY_EXISTS", 409)
    else:
        user_id = f"user_{max(len(state.users), state.mongo_store.count_users()) + 1}"

    # Biological sex
    sex_str = str(data.get('biological_sex') or 'male').strip().lower()
    bio_sex = BiologicalSex.FEMALE if sex_str == 'female' else BiologicalSex.MALE

    # Goals — accept string or list
    goals_raw = data.get('goals')
    if not goals_raw:
        goals_list = ['general_wellness']
    elif isinstance(goals_raw, str):
        goals_list = [goals_raw] if goals_raw else ['general_wellness']
    elif isinstance(goals_raw, list):
        goals_list = [g for g in goals_raw if g] or ['general_wellness']
    else:
        goals_list = ['general_wellness']

    age, age_err = coerce_int(data.get('age'), 25, minimum=1, maximum=120)
    if age_err:
        return age_err
    weight, weight_err = coerce_float(data.get('weight_kg'), 70.0, minimum=1, maximum=500)
    if weight_err:
        return weight_err
    height, height_err = coerce_float(data.get('height_cm'), 175.0, minimum=30, maximum=300)
    if height_err:
        return height_err
    cal, cal_err = coerce_int(data.get('target_calories'), 2000, minimum=0, maximum=10000)
    if cal_err:
        return cal_err
    protein, protein_err = coerce_float(data.get('target_protein_g'), 150.0, minimum=0, maximum=1000)
    if protein_err:
        return protein_err
    carbs, carbs_err = coerce_float(data.get('target_carbs_g'), 200.0, minimum=0, maximum=2000)
    if carbs_err:
        return carbs_err
    fat, fat_err = coerce_float(data.get('target_fat_g'), 65.0, minimum=0, maximum=1000)
    if fat_err:
        return fat_err
    water_target, water_err = coerce_int(data.get('water_target_ml'), 2500, minimum=0, maximum=10000)
    if water_err:
        return water_err

    # Build UserProfile
    try:
        user = UserProfile(
            user_id          = user_id,
            name             = data.get('name', 'Unknown'),
            age              = age,
            weight_kg        = weight,
            height_cm        = height,
            biological_sex   = bio_sex,
            goals            = [Goal(g) for g in goals_list],
            target_calories  = cal,
            target_protein_g = protein,
            target_carbs_g   = carbs,
            target_fat_g     = fat,
            water_target_ml  = water_target,
        )
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return error_response(f"Invalid user data: {e}", "INVALID_USER_DATA", 400)

    # Optional password → enables session login.
    password = str(data.get('password') or '')
    if password:
        if len(password) < 6:
            return error_response("Password must be at least 6 characters", "PASSWORD_TOO_SHORT", 400)
        from werkzeug.security import generate_password_hash
        user.password_hash = generate_password_hash(password)

    # Persist and initialise AI modules
    try:
        state.users[user_id] = user
        ensure_ai_modules(user_id, user)
        save_user_with_hash(user)
    except Exception as e:
        # Roll back in-memory state so a retry doesn't collide
        state.users.pop(user_id, None)
        traceback.print_exc(file=sys.stderr)
        return error_response(f"Failed to initialise user: {e}", "USER_INIT_FAILED", 500)

    return jsonify({
        "status": "success",
        "user_id": user_id,
        "user": user.to_public_dict(),
        "password_set": bool(password),
    }), 201


@user_bp.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """Return a user profile by ID (never exposes the password hash)."""
    user, err = require_user(user_id)
    if err:
        return err
    return jsonify(user.to_public_dict()), 200


@user_bp.route('/api/user/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    """
    Permanently delete a user account and all associated health records.
    Requires authentication as the target user.
    """
    _, err = require_user_and_auth(user_id)
    if err:
        return err

    # 1. Delete from MongoDB
    deleted_counts = {}
    if state.mongo_store.enabled:
        deleted_counts = state.mongo_store.delete_user_data(user_id)

    # 2. Clean up in-memory caches and modules
    state.users.pop(user_id, None)
    state.daily_logs.pop(user_id, None)
    state.activity_logs.pop(user_id, None)
    state.schedule_history.pop(user_id, None)
    state.productivity_sessions.pop(user_id, None)
    state.bot_sessions.pop(user_id, None)
    state.sleep_logs.pop(user_id, None)
    state.knowledge_bases.pop(user_id, None)
    state.nutrition_analyzers.pop(user_id, None)
    state.meal_recommenders.pop(user_id, None)
    state.recovery_predictors.pop(user_id, None)
    state.sleep_predictors.pop(user_id, None)

    # 3. Terminate current session if deleting self
    if session.get('user_id') == user_id:
        session.clear()

    return jsonify({
        "status": "deleted",
        "user_id": user_id,
        "records_purged": deleted_counts,
        "message": "User account and all associated health data permanently deleted.",
    }), 200


@user_bp.route('/api/user/<user_id>/export', methods=['GET'])
def export_user(user_id):
    """
    Export all stored health data for a user in structured JSON format (portability).
    Requires authentication as the target user.
    """
    user, err = require_user_and_auth(user_id)
    if err:
        return err

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    if state.mongo_store.enabled:
        export_payload = state.mongo_store.export_user_data(
            user_id, start_date=start_date, end_date=end_date
        )
    else:
        from api.blueprints.serialization_helpers import serialize_daily_log
        daily_logs_raw = state.daily_logs.get(user_id, {})
        serialized_logs = [serialize_daily_log(l) for l in daily_logs_raw.values()]
        bot = state.bot_sessions.get(user_id)
        chat_hist = getattr(bot, "history", []) if bot else []
        export_payload = {
            "export_metadata": {
                "user_id": user_id,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
                "filter_start_date": start_date,
                "filter_end_date": end_date,
            },
            "user_profile": user.to_public_dict(),
            "daily_logs": serialized_logs,
            "meals": [],
            "activity_logs": state.activity_logs.get(user_id, []),
            "sleep_logs": state.sleep_logs.get(user_id, []),
            "schedules": state.schedule_history.get(user_id, []),
            "productivity_sessions": state.productivity_sessions.get(user_id, []),
            "chat_history": chat_hist,
        }

    response = jsonify(export_payload)
    response.headers["Content-Disposition"] = f'attachment; filename="health_data_export_{user_id}.json"'
    return response, 200


@user_bp.route('/api/privacy', methods=['GET'])
def get_privacy_policy():
    """Return an overview of the Health Tracker privacy policies and data protection controls."""
    return jsonify({
        "policy_version": "2026.1",
        "data_collected": [
            "User profile (age, weight, height, sex, health goals)",
            "Nutritional logs (meals, calories, macronutrients, water intake)",
            "Physical activity logs (exercise, duration, energy ratings)",
            "Sleep tracking (duration, bedtime, self-reported quality)",
            "Productivity & focus logs (task schedules, focus scores)",
            "Chat queries and conversation turns"
        ],
        "data_protection_rights": {
            "erasure": "Permanent account deletion via DELETE /api/user/<user_id>",
            "portability": "Structured JSON download via GET /api/user/<user_id>/export",
            "rectification": "Profile and goal updates via user endpoints",
            "retention": "Configurable automated TTL cleanup on all logs"
        },
        "third_party_services": {
            "usda_food_api": "Queries food nutrition databases without PII transmission",
            "exercisedb_api": "Queries fitness libraries without PII transmission",
            "groq_ai": "Processes chat prompts; local rule-based fallback available if keyless"
        }
    }), 200