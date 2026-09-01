"""trends.py — Aggregated nutrition and focus trend data for the analytics tab."""

from flask import Blueprint, jsonify, request

from api.blueprints import state
from api.blueprints.helpers import require_auth, require_user, coerce_int

trends_bp = Blueprint('trends', __name__)


@trends_bp.route('/api/trends/<user_id>', methods=['GET'])
def get_trends(user_id):
    """
    Return recent nutrition (calories/macros per day) and focus scores for the
    analytics charts. Reads from persisted history, so trends survive restarts.

    Query params:
        days : int  — max number of recent nutrition days (default 7)
        focus_limit : int — max number of recent focus points (default 20)
    """
    user, err = require_user(user_id)
    if err:
        return err
    auth_err = require_auth(user_id)
    if auth_err:
        return auth_err

    days, days_err = coerce_int(request.args.get('days', 7), 7, minimum=1, maximum=365)
    if days_err:
        return days_err
    focus_limit, focus_err = coerce_int(request.args.get('focus_limit', 20), 20, minimum=1, maximum=200)
    if focus_err:
        return focus_err

    # Nutrition: per-day totals, ascending by date, most recent `days`.
    user_logs = state.daily_logs.get(user_id, {})
    nutrition = []
    for date_str in sorted(user_logs, key=str)[-days:]:
        daily = user_logs[date_str]
        total = daily.get_total_nutrition()
        if total.calories == 0 and total.protein_g == 0:
            continue
        nutrition.append({
            "date": date_str,
            "calories": total.calories,
            "protein_g": round(total.protein_g, 1),
            "carbs_g": round(total.carbs_g, 1),
            "fat_g": round(total.fat_g, 1),
        })

    # Focus: predicted scores over time, oldest first for the chart.
    sessions = state.productivity_sessions.get(user_id, [])
    focus = [
        {
            "timestamp": s.get("timestamp"),
            "focus": float(s.get("predicted_focus_score")),
        }
        for s in sessions
        if s.get("predicted_focus_score") is not None
    ][-focus_limit:]

    return jsonify({
        "user_id": user_id,
        "nutrition": nutrition,
        "focus": focus,
    }), 200
