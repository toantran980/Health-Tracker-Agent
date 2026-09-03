"""sleep.py — Sleep logging, history retrieval, and sleep quality prediction endpoints."""

from __future__ import annotations

from uuid import uuid4

from flask import Blueprint, jsonify, request

from ai_modules.sleep_quality_predictor import SleepFeatures, SleepQualityPredictor
from api.blueprints import state
from api.blueprints.helpers import (
    coerce_float,
    coerce_int,
    error_response,
    parse_iso_datetime,
    require_auth,
    require_fields,
    require_user,
)

sleep_bp = Blueprint('sleep', __name__)


def get_or_create_sleep_predictor(user_id: str) -> SleepQualityPredictor:
    predictor = state.sleep_predictors.get(user_id)
    if not predictor:
        predictor = SleepQualityPredictor()
        state.sleep_predictors[user_id] = predictor
    return predictor


@sleep_bp.route('/api/sleep/log', methods=['POST'])
def log_sleep():
    """
    Log a night of sleep with duration, quality, and hygiene factors (auth required).

    Body (JSON):
        user_id                 : str    (required)
        duration_hours          : float  (required, e.g. 7.5)
        bedtime_hour            : float  (optional, e.g. 23.0)
        quality_score           : int    (1-10, optional self-reported)
        caffeine_servings       : int    (optional)
        exercise_minutes        : int    (optional)
        screen_time_bedtime_min : int    (optional)
        stress_level            : int    (1-10, optional)
        notes                   : str    (optional)
        timestamp               : str    (ISO-8601, optional)
    """
    data = request.get_json(silent=True) or {}
    user_id = str(data.get('user_id', '')).strip()

    missing = require_fields(data, ["user_id", "duration_hours"])
    if missing:
        return missing

    _, err = require_user(user_id)
    if err:
        return err

    auth_err = require_auth(user_id)
    if auth_err:
        return auth_err

    duration, dur_err = coerce_float(data.get('duration_hours'), None, minimum=0.5, maximum=24.0)
    if dur_err:
        return dur_err
    if duration is None:
        return error_response("duration_hours is required", "MISSING_DURATION", 400)

    bedtime_hour, bt_err = coerce_float(data.get('bedtime_hour', 23.0), 23.0, minimum=0.0, maximum=24.0)
    if bt_err:
        return bt_err

    quality, q_err = coerce_int(data.get('quality_score'), None, minimum=1, maximum=10)
    if q_err:
        return q_err

    caffeine, c_err = coerce_int(data.get('caffeine_servings', 0), 0, minimum=0, maximum=20)
    if c_err:
        return c_err

    exercise, ex_err = coerce_int(data.get('exercise_minutes', 0), 0, minimum=0, maximum=600)
    if ex_err:
        return ex_err

    screen_time, sc_err = coerce_int(data.get('screen_time_bedtime_min', 0), 0, minimum=0, maximum=240)
    if sc_err:
        return sc_err

    stress, st_err = coerce_int(data.get('stress_level', 5), 5, minimum=1, maximum=10)
    if st_err:
        return st_err

    ts = parse_iso_datetime(data.get('timestamp'))

    log_doc = {
        "log_id": f"sleep_{uuid4().hex[:12]}",
        "user_id": user_id,
        "timestamp": ts.isoformat(),
        "duration_hours": duration,
        "bedtime_hour": bedtime_hour,
        "quality_score": quality,
        "caffeine_servings": caffeine,
        "exercise_minutes": exercise,
        "screen_time_bedtime_min": screen_time,
        "stress_level": stress,
        "notes": str(data.get('notes') or '').strip(),
    }

    state.sleep_logs.setdefault(user_id, []).insert(0, log_doc)
    state.mongo_store.save_sleep_log(log_doc)

    # If user provided a ground truth quality rating, update the predictor
    if quality is not None:
        features = SleepFeatures(
            bedtime_hour=bedtime_hour,
            sleep_duration_h=duration,
            caffeine_servings=caffeine,
            exercise_minutes=exercise,
            screen_time_bedtime_min=screen_time,
            stress_level=stress,
        )
        predictor = get_or_create_sleep_predictor(user_id)
        predictor.add_training_data(features, quality)
        if len(predictor.training_data) % 3 == 0:
            predictor.train()

    return jsonify({"status": "success", "sleep_log": log_doc}), 201


@sleep_bp.route('/api/sleep/logs/<user_id>', methods=['GET'])
def get_sleep_logs(user_id):
    """Return logged sleep records for a user, newest first."""
    _, err = require_user(user_id)
    if err:
        return err

    limit, limit_err = coerce_int(request.args.get('limit', 50), 50, minimum=1, maximum=500)
    if limit_err:
        return limit_err

    logs = state.sleep_logs.get(user_id, [])[:limit]
    return jsonify({"count": len(logs), "sleep_logs": logs}), 200


@sleep_bp.route('/api/sleep/predict/<user_id>', methods=['GET'])
def predict_sleep_quality(user_id):
    """Predict sleep quality rating (1-10) and hygiene recommendations based on planned habits."""
    user, err = require_user(user_id)
    if err:
        return err

    duration, d_err = coerce_float(
        request.args.get('duration_hours', getattr(user, 'current_sleep_hours', 8.0)),
        8.0, minimum=1.0, maximum=16.0
    )
    if d_err:
        return d_err

    bedtime, b_err = coerce_float(request.args.get('bedtime_hour', 23.0), 23.0, minimum=0.0, maximum=24.0)
    if b_err:
        return b_err

    caffeine, c_err = coerce_int(request.args.get('caffeine_servings', 1), 1, minimum=0, maximum=15)
    if c_err:
        return c_err

    exercise, ex_err = coerce_int(request.args.get('exercise_minutes', 30), 30, minimum=0, maximum=300)
    if ex_err:
        return ex_err

    screen_time, sc_err = coerce_int(request.args.get('screen_time_bedtime_min', 15), 15, minimum=0, maximum=180)
    if sc_err:
        return sc_err

    stress, st_err = coerce_int(request.args.get('stress_level', 4), 4, minimum=1, maximum=10)
    if st_err:
        return st_err

    features = SleepFeatures(
        bedtime_hour=bedtime,
        sleep_duration_h=duration,
        caffeine_servings=caffeine,
        exercise_minutes=exercise,
        screen_time_bedtime_min=screen_time,
        stress_level=stress,
    )

    predictor = get_or_create_sleep_predictor(user_id)
    predicted_score = predictor.predict(features)
    recommendations = predictor.get_sleep_hygiene_recommendations(features)

    return jsonify({
        "predicted_sleep_quality": predicted_score,
        "recommendations": recommendations,
        "features": {
            "bedtime_hour": bedtime,
            "duration_hours": duration,
            "caffeine_servings": caffeine,
            "exercise_minutes": exercise,
            "screen_time_bedtime_min": screen_time,
            "stress_level": stress,
        }
    }), 200
