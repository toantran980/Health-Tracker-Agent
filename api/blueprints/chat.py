"""chat.py — AI health chatbot endpoints."""

from flask import Blueprint, request, jsonify

from ai_modules.health_chatbot import HealthChatbot, UserHealthSnapshot
from api.blueprints import state
from api.blueprints.helpers import require_user, error_response

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/api/chat/<user_id>', methods=['POST'])
def chat(user_id):
    """
    Send a message to the AI health chatbot.

    Body (JSON):
        message              : str  (required)
        calories_today       : int
        protein_g            : float
        carbs_g              : float
        fat_g                : float
        water_ml             : int
        study_hours_today    : float
        focus_score          : float
        sleep_hours          : float
        dietary_restrictions : list[str]
        active_insights      : list[str]
    """
    user, err = require_user(user_id)
    if err:
        return err

    data    = request.json or {}
    message = data.get("message", "").strip()
    if not message:
        return error_response("message is required", "MISSING_MESSAGE", 400)

    snapshot = UserHealthSnapshot(
        name                   = user.name,
        weight_lbs             = round(user.weight_kg * 2.20462, 1),
        calories_today         = data.get("calories_today",      0),
        protein_g              = data.get("protein_g",           0),
        carbs_g                = data.get("carbs_g",             0),
        fat_g                  = data.get("fat_g",               0),
        water_ml               = data.get("water_ml",            0),
        study_hours_today      = data.get("study_hours_today",   0),
        focus_score            = data.get("focus_score"),
        sleep_hours_last_night = data.get("sleep_hours"),
        health_goal            = user.goals[0].value if user.goals else "general_wellness",
        dietary_restrictions   = data.get("dietary_restrictions", user.dietary_restrictions),
        active_insights        = data.get("active_insights",     []),
    )

    if user_id not in state.bot_sessions:
        state.bot_sessions[user_id] = HealthChatbot(snapshot)
    else:
        state.bot_sessions[user_id].update_snapshot(snapshot)

    reply = state.bot_sessions[user_id].chat(message)
    return jsonify({"reply": reply}), 200


@chat_bp.route('/api/chat/<user_id>/reset', methods=['POST'])
def reset_chat(user_id):
    """Wipe the conversation history for a user's chatbot session."""
    if user_id in state.bot_sessions:
        state.bot_sessions[user_id].reset()
    return jsonify({"status": "ok"}), 200
