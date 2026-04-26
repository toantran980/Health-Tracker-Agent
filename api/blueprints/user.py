"""user.py — User profile endpoints."""

from flask import Blueprint, request, jsonify

from models.user_profile import UserProfile, Goal, BiologicalSex
from api.blueprints import state
from api.blueprints.helpers import require_user, ensure_ai_modules

user_bp = Blueprint('user', __name__)


@user_bp.route('/api/user/create', methods=['POST'])
def create_user():
    """
    Create a new user profile and initialise all AI modules.

    Body (JSON):
        user_id, name, age, weight_kg, height_cm, biological_sex,
        goals, target_calories, target_protein_g, target_carbs_g, target_fat_g
    """
    data    = request.json or {}
    user_id = data.get('user_id')
    if not user_id:
        next_id = max(len(state.users), state.mongo_store.count_users()) + 1
        user_id = f"user_{next_id}"

    sex_str = data.get('biological_sex', 'male').lower()
    bio_sex = BiologicalSex.FEMALE if sex_str == 'female' else BiologicalSex.MALE

    user = UserProfile(
        user_id        = user_id,
        name           = data.get('name', 'Unknown'),
        age            = data.get('age', 25),
        weight_kg      = data.get('weight_kg', 70),
        height_cm      = data.get('height_cm', 175),
        biological_sex = bio_sex,
        goals          = [Goal(g) for g in data.get('goals', ['general_wellness'])],
        target_calories  = data.get('target_calories',  2000),
        target_protein_g = data.get('target_protein_g', 150.0),
        target_carbs_g   = data.get('target_carbs_g',   200.0),
        target_fat_g     = data.get('target_fat_g',     65.0),
    )

    state.users[user_id] = user
    ensure_ai_modules(user_id, user)
    state.mongo_store.save_user(user.to_dict())

    return jsonify({"status": "success", "user": user.to_dict()}), 201


@user_bp.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """Return a user profile by ID."""
    user, err = require_user(user_id)
    if err:
        return err
    return jsonify(user.to_dict()), 200
