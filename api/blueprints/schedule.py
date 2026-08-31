"""schedule.py — Schedule optimisation, productivity prediction, and knowledge base endpoints."""

from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from ai_modules import ScheduleOptimizer, ProductivityPredictor, Features
from api.blueprints import state
from api.blueprints.helpers import (
    require_user,
    normalize_schedule_tasks,
    coerce_int,
    error_response,
)

schedule_bp = Blueprint('schedule', __name__)


# Schedule optimization

@schedule_bp.route('/api/schedule/optimize/<user_id>', methods=['POST'])
def optimize_schedule(user_id):
    """Optimise a list of study tasks for a user and persist the result."""
    user, err = require_user(user_id)
    if err:
        return err

    data      = request.json or {}
    optimizer = ScheduleOptimizer(user.earliest_study_time, user.latest_study_time)
    tasks     = normalize_schedule_tasks(data.get('tasks', []))
    optimized = optimizer.optimize_schedule(tasks)

    # Persist for history/trends (best-effort; in-memory fallback too).
    schedule_doc = {
        "created_at": datetime.now(timezone.utc),
        "num_tasks":  len(optimized),
        "schedule":   [
            {
                "task":       item.get("task", {}).get("name", "Untitled"),
                "time_slot":  item.get("time_slot"),
                "warning":    item.get("warning"),
                "day":        item["slot"].day_name if item.get("slot") else None,
                "start_hour": item["slot"].start_hour if item.get("slot") else None,
                "end_hour":   item["slot"].end_hour if item.get("slot") else None,
            }
            for item in optimized
        ],
    }
    state.schedule_history.setdefault(user_id, []).insert(0, schedule_doc)
    state.mongo_store.save_schedule(user_id, schedule_doc)

    return jsonify({
        "status":    "success",
        "schedule":  optimized,
        "num_tasks": len(optimized),
    }), 200


@schedule_bp.route('/api/schedule/history/<user_id>', methods=['GET'])
def schedule_history(user_id):
    """Return previously optimised schedules for a user."""
    _, err = require_user(user_id)
    if err:
        return err

    limit, limit_err = coerce_int(request.args.get('limit', 10), 10, minimum=1, maximum=100)
    if limit_err:
        return limit_err
    history = state.schedule_history.get(user_id, [])[:limit]
    return jsonify({"count": len(history), "schedules": history}), 200


@schedule_bp.route('/api/schedule/available-slots/<user_id>', methods=['GET'])
def get_available_slots(user_id):
    """Return available time slots for a given session duration."""
    user, err = require_user(user_id)
    if err:
        return err

    duration, duration_err = coerce_int(request.args.get('duration_minutes', 60), 60, minimum=1, maximum=480)
    if duration_err:
        return duration_err
    optimizer = ScheduleOptimizer(user.earliest_study_time, user.latest_study_time)
    slots     = optimizer.get_available_slots(duration)

    return jsonify({
        "slots": [
            {
                "day":                 slot.day_name,
                "start_hour":          slot.start_hour,
                "end_hour":            slot.end_hour,
                "productivity_factor": slot.productivity_factor,
            }
            for slot in slots
        ]
    }), 200


# Productivity prediction

@schedule_bp.route('/api/productivity/predict/<user_id>', methods=['POST'])
def predict_productivity(user_id):
    """Predict focus score and recommended session duration; persist the session."""
    _, err = require_user(user_id)
    if err:
        return err

    data     = request.json or {}
    features = Features(
        hour_of_day               = data.get('hour_of_day',               10),
        day_of_week               = data.get('day_of_week',               0),
        sleep_quality             = data.get('sleep_quality',             7.0),
        sleep_hours               = data.get('sleep_hours',               8.0),
        nutrition_score           = data.get('nutrition_score',           75.0),
        energy_level              = data.get('energy_level',              7),
        previous_session_duration = data.get('previous_session_duration', 60),
        task_difficulty           = data.get('task_difficulty',           5),
    )

    predictor   = ProductivityPredictor()
    focus_score = predictor.predict(features)
    duration    = predictor.estimate_session_duration(
        data.get('task_difficulty', 5),
        data.get('energy_level', 7),
        focus_score,
    )

    # Persist a productivity session for trend analysis.
    session_doc = {
        "timestamp":                   datetime.now(timezone.utc),
        "input": {
            "hour_of_day":               features.hour_of_day,
            "day_of_week":               features.day_of_week,
            "sleep_quality":             features.sleep_quality,
            "sleep_hours":               features.sleep_hours,
            "nutrition_score":           features.nutrition_score,
            "energy_level":              features.energy_level,
            "previous_session_duration": features.previous_session_duration,
            "task_difficulty":           features.task_difficulty,
        },
        "predicted_focus_score":        focus_score,
        "recommended_duration_minutes": duration,
    }
    state.productivity_sessions.setdefault(user_id, []).insert(0, session_doc)
    state.mongo_store.save_productivity_session(user_id, session_doc)

    return jsonify({
        "predicted_focus_score":        focus_score,
        "recommended_duration_minutes": duration,
        "model_info":                   predictor.get_model_info(),
    }), 200


@schedule_bp.route('/api/productivity/sessions/<user_id>', methods=['GET'])
def productivity_sessions(user_id):
    """Return previously saved productivity prediction sessions."""
    _, err = require_user(user_id)
    if err:
        return err

    limit, limit_err = coerce_int(request.args.get('limit', 10), 10, minimum=1, maximum=100)
    if limit_err:
        return limit_err
    sessions = state.productivity_sessions.get(user_id, [])[:limit]
    return jsonify({"count": len(sessions), "sessions": sessions}), 200


@schedule_bp.route('/api/productivity/optimal-time/<user_id>', methods=['GET'])
def get_optimal_study_time(user_id):
    """Return the optimal hour and day for a study session."""
    user, err = require_user(user_id)
    if err:
        return err

    predictor        = ProductivityPredictor()
    hour, day, focus = predictor.suggest_optimal_time(
        user.earliest_study_time, user.latest_study_time
    )
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    return jsonify({
        "optimal_hour":          hour,
        "optimal_day":           days[day],
        "predicted_focus_score": focus,
    }), 200


# Knowledge base recommendations

@schedule_bp.route('/api/recommendations/<user_id>', methods=['POST'])
def get_recommendations(user_id):
    """Run the knowledge base inference engine and return top recommendations."""
    user, err = require_user(user_id)
    if err:
        return err

    kb = state.knowledge_bases.get(user_id)
    if not kb:
        return error_response("Knowledge base not initialized", "KNOWLEDGE_BASE_NOT_INITIALIZED", 400)

    data = request.json or {}
    kb.add_facts({
        "daily_calories":              data.get("daily_calories",              2000),
        "daily_protein":               data.get("daily_protein",               150),
        "energy_level":                data.get("energy_level",                5),
        "sleep_hours":                 data.get("sleep_hours",                 8),
        "upcoming_difficulty":         data.get("upcoming_difficulty",         5),
        "recent_session_duration":     data.get("recent_session_duration",     60),
        "macro_balance":               data.get("macro_balance",               "balanced"),
        "macro_balance_details":       data.get("macro_balance_details",       {}),
        "correlation_nutrition_study": data.get("correlation_nutrition_study", 0.0),
        "adherence_rate":              data.get("adherence_rate",              0.5),
    })

    recommendations = kb.get_top_recommendations(n=3)
    kb.clear_facts()

    # Persist recommendation history for longitudinal analysis.
    state.mongo_store.save_recommendation({
        "user_id":         user_id,
        "recommendations": recommendations,
        "source":          "knowledge_base",
    })

    return jsonify({
        "status":          "success",
        "recommendations": recommendations,
        "count":           len(recommendations),
    }), 200