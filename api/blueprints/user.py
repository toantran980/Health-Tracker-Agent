"""user.py — User profile endpoints."""

import sys
import traceback
from flask import Blueprint, request, jsonify

from models.user_profile import UserProfile, Goal, BiologicalSex
from api.blueprints import state
from api.blueprints.helpers import (
    require_user,
    ensure_ai_modules,
    coerce_int,
    coerce_float,
    error_response,
    save_user_with_hash,
)

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

    # Numeric fields through the shared validation helpers.
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