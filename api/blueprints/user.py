"""user.py — User profile endpoints."""

import sys
import traceback
from flask import Blueprint, request, jsonify

from models.user_profile import UserProfile, Goal, BiologicalSex
from api.blueprints import state
from api.blueprints.helpers import require_user, ensure_ai_modules

user_bp = Blueprint('user', __name__)


def _to_int(val, default: int) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _to_float(val, default: float) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


@user_bp.route('/api/user/create', methods=['POST'])
def create_user():
    """
    Create a new user profile and initialise all AI modules.

    Body (JSON):
        user_id, name, age, weight_kg, height_cm, biological_sex,
        goals, target_calories, target_protein_g, target_carbs_g, target_fat_g
    """
    data = request.get_json(silent=True) or request.form.to_dict()

    # Assign user_id
    user_id = data.get('user_id') or f"user_{max(len(state.users), state.mongo_store.count_users()) + 1}"

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
    # Build UserProfile
    try:
        user = UserProfile(
            user_id          = user_id,
            name             = data.get('name', 'Unknown'),
            age              = _to_int(data.get('age'), 25),
            weight_kg        = _to_float(data.get('weight_kg'), 70.0),
            height_cm        = _to_float(data.get('height_cm'), 175.0),
            biological_sex   = bio_sex,
            goals            = [Goal(g) for g in goals_list],
            target_calories  = _to_int(data.get('target_calories'), 2000),
            target_protein_g = _to_float(data.get('target_protein_g'), 150.0),
            target_carbs_g   = _to_float(data.get('target_carbs_g'), 200.0),
            target_fat_g     = _to_float(data.get('target_fat_g'), 65.0),
        )
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        return jsonify({"status": "error", "message": f"Invalid user data: {e}"}), 400

    # Persist and initialise AI modules
    try:
        state.users[user_id] = user
        ensure_ai_modules(user_id, user)
        state.mongo_store.save_user(user.to_dict())
    except Exception as e:
        # Roll back in-memory state so a retry doesn't collide
        state.users.pop(user_id, None)
        traceback.print_exc(file=sys.stderr)
        return jsonify({"status": "error", "message": f"Failed to initialise user: {e}"}), 500

    return jsonify({"status": "success", "user_id": user_id, "user": user.to_dict()}), 201


@user_bp.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """Return a user profile by ID."""
    user, err = require_user(user_id)
    if err:
        return err
    return jsonify(user.to_dict()), 200