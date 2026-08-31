"""activity.py — Activity recommendation, logging, and trend analysis endpoints."""

from uuid import uuid4
from datetime import datetime, timedelta, timezone

from flask import Blueprint, request, jsonify
from api.blueprints import state
from api.blueprints.helpers import (
    require_user,
    require_auth,
    require_fields,
    error_response,
    parse_iso_datetime,
    coerce_int,
)
from ai_modules.activity_recommendation_engine import ActivityRecommendationEngine
from models.activity import ActivityLog, ActivityType

activity_bp = Blueprint('activity', __name__)


@activity_bp.route('/api/activity-recommendations/<user_id>', methods=['GET'])
def get_activity_recommendations(user_id):
    """Return personalized activity recommendations for the user."""
    user, err = require_user(user_id)
    if err:
        return err

    recommender = ActivityRecommendationEngine(user)
    n, n_err = coerce_int(request.args.get('n', 5), 5, minimum=1, maximum=20)
    if n_err:
        return n_err
    energy, energy_err = coerce_int(request.args.get('energy_level', 5), 5, minimum=1, maximum=10)
    if energy_err:
        return energy_err
    minutes, min_err = coerce_int(request.args.get('available_minutes', 30), 30, minimum=5, maximum=600)
    if min_err:
        return min_err

    recommendations = recommender.recommend(energy_level=energy, available_minutes=minutes, n=n)
    return jsonify({
        "recommendations": recommendations,
        "count": len(recommendations)
    }), 200


@activity_bp.route('/api/activity/log', methods=['POST'])
def log_activity():
    """
    Log a completed activity for longitudinal analysis (auth required).

    Body (JSON):
        user_id          : str    (required)
        activity_type    : str    (study|exercise|meal|sleep|rest|work, required)
        duration_minutes : int    (required)
        timestamp        : str    (ISO-8601, optional)
        metadata         : dict   (optional)
        energy_after     : int    (1-10, optional)
        notes            : str    (optional)
    """
    data = request.get_json(silent=True) or {}
    user_id = str(data.get('user_id', '')).strip()
    activity_type_raw = str(data.get('activity_type', '')).strip().lower()
    duration_raw = data.get('duration_minutes')

    missing = require_fields(data, ["user_id", "activity_type", "duration_minutes"])
    if missing:
        return missing
    _, err = require_user(user_id)
    if err:
        return err
    auth_err = require_auth(user_id)
    if auth_err:
        return auth_err

    if activity_type_raw not in ActivityType._value2member_map_:
        return error_response(
            f"activity_type must be one of {sorted(a.value for a in ActivityType)}",
            "INVALID_ACTIVITY_TYPE",
        )
    duration, dur_err = coerce_int(duration_raw, None, minimum=1, maximum=1440)
    if dur_err:
        return dur_err
    if duration is None:
        return error_response("duration_minutes is required", "MISSING_DURATION", 400)
    energy_after, energy_err = coerce_int(data.get('energy_after'), None, minimum=1, maximum=10)
    if energy_err:
        return energy_err

    log = ActivityLog(
        log_id=f"act_{uuid4().hex[:12]}",
        user_id=user_id,
        activity_type=ActivityType(activity_type_raw),
        timestamp=parse_iso_datetime(data.get('timestamp')),
        duration_minutes=duration,
        metadata=data.get('metadata') or {},
        energy_after=energy_after,
        notes=str(data.get('notes') or ''),
    )

    log_doc = log.to_dict()
    state.activity_logs.setdefault(user_id, []).insert(0, log_doc)
    state.mongo_store.save_activity_log(log_doc)

    return jsonify({"status": "success", "activity_log": log_doc}), 201


@activity_bp.route('/api/activity/logs/<user_id>', methods=['GET'])
def get_activity_logs(user_id):
    """Return logged activities for a user, newest first."""
    _, err = require_user(user_id)
    if err:
        return err

    limit, limit_err = coerce_int(request.args.get('limit', 50), 50, minimum=1, maximum=500)
    if limit_err:
        return limit_err
    logs = state.activity_logs.get(user_id, [])[:limit]
    return jsonify({"count": len(logs), "activity_logs": logs}), 200


@activity_bp.route('/api/activity/trends/<user_id>', methods=['GET'])
def activity_trends(user_id):
    """
    Aggregate logged activities into trend statistics over the last N days.

    Returns totals per activity type (count, total duration, avg energy),
    plus per-day summaries for the selected window.
    """
    _, err = require_user(user_id)
    if err:
        return err

    days, days_err = coerce_int(request.args.get('days', 7), 7, minimum=1, maximum=90)
    if days_err:
        return days_err

    logs = state.activity_logs.get(user_id, [])
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    type_stats: dict[str, dict] = {}
    per_day: dict[str, dict] = {}
    for log in logs:
        try:
            ts = parse_iso_datetime(log.get('timestamp'))
        except Exception:
            continue
        if ts < cutoff:
            continue

        act_type = log.get('activity_type', 'unknown')
        duration = int(log.get('duration_minutes') or 0)
        energy = log.get('energy_after')

        stat = type_stats.setdefault(act_type, {"count": 0, "total_duration_minutes": 0, "energy_scores": []})
        stat["count"] += 1
        stat["total_duration_minutes"] += duration
        if energy is not None:
            stat["energy_scores"].append(float(energy))

        day = ts.date().isoformat()
        day_entry = per_day.setdefault(day, {"count": 0, "total_duration_minutes": 0})
        day_entry["count"] += 1
        day_entry["total_duration_minutes"] += duration

    for stat in type_stats.values():
        if stat["energy_scores"]:
            stat["avg_energy_after"] = round(sum(stat["energy_scores"]) / len(stat["energy_scores"]), 2)
        stat.pop("energy_scores", None)

    return jsonify({
        "days": days,
        "by_type": type_stats,
        "per_day": dict(sorted(per_day.items())),
        "total_activities": sum(s["count"] for s in type_stats.values()),
        "total_duration_minutes": sum(s["total_duration_minutes"] for s in type_stats.values()),
    }), 200