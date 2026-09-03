from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from ai_modules.goal_tracker import GoalTracker
from ai_modules.health_risk_assessor import HealthRiskAssessor
from ai_modules.recovery_predictor import RecoveryFeatures, RecoveryPredictor
from ai_modules.weekly_digest import WeeklyDigestGenerator
from api.blueprints import state
from api.blueprints.helpers import (
    coerce_float,
    coerce_int,
    require_user,
)
from api.blueprints.serialization_helpers import serialize_daily_log

health_bp = Blueprint('health', __name__)


def get_serialized_user_logs(user_id: str) -> list[dict]:
    logs_map = state.daily_logs.get(user_id, {})
    return [serialize_daily_log(logs_map[k]) for k in sorted(logs_map.keys(), reverse=True)]


def get_or_create_recovery_predictor(user_id: str) -> RecoveryPredictor:
    predictor = state.recovery_predictors.get(user_id)
    if not predictor:
        predictor = RecoveryPredictor()
        state.recovery_predictors[user_id] = predictor
    return predictor


@health_bp.route('/api/health', methods=['GET'])
def health_check():
    """Liveness probe — returns 200 when the server is running."""
    persisted_users = (
        state.mongo_store.count_users() if state.mongo_store.enabled else len(state.users)
    )
    return jsonify({
        "status":    "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
            "recovery_predictor": user_id in state.recovery_predictors,
            "sleep_predictor":    user_id in state.sleep_predictors,
        },
    }), 200


@health_bp.route('/api/health-risks/<user_id>', methods=['GET'])
def get_health_risks(user_id):
    """Evaluate and return rule-based health and nutrition risk warnings."""
    user, err = require_user(user_id)
    if err:
        return err

    daily_logs = get_serialized_user_logs(user_id)
    activity_logs = state.activity_logs.get(user_id, [])
    sleep_logs = state.sleep_logs.get(user_id, [])

    assessor = HealthRiskAssessor(user, daily_logs, activity_logs, sleep_logs)
    report = assessor.assess()
    return jsonify({
        "user_id": user_id,
        "assessed_at": datetime.now(timezone.utc).isoformat(),
        **report,
    }), 200


@health_bp.route('/api/recovery/<user_id>', methods=['GET'])
def get_recovery_readiness(user_id):
    """
    Predict physical readiness score (1-10) and training load recommendations.
    Accepts query parameter overrides or derives features from recent logs.
    """
    user, err = require_user(user_id)
    if err:
        return err

    sleep_logs = state.sleep_logs.get(user_id, [])
    activity_logs = state.activity_logs.get(user_id, [])

    # Derive recent sleep metrics or use defaults
    default_sleep_hours = getattr(user, 'current_sleep_hours', 8.0)
    default_sleep_qual = 7.0
    if sleep_logs:
        most_recent_sleep = sleep_logs[0]
        default_sleep_hours = float(most_recent_sleep.get("duration_hours") or default_sleep_hours)
        default_sleep_qual = float(most_recent_sleep.get("quality_score") or default_sleep_qual)

    sleep_h, sh_err = coerce_float(request.args.get('sleep_hours', default_sleep_hours), default_sleep_hours, 0.0, 16.0)
    if sh_err:
        return sh_err

    sleep_q, sq_err = coerce_float(request.args.get('sleep_quality', default_sleep_qual), default_sleep_qual, 1.0, 10.0)
    if sq_err:
        return sq_err

    stress, st_err = coerce_int(request.args.get('stress_level', 4), 4, 1, 10)
    if st_err:
        return st_err

    energy, en_err = coerce_int(request.args.get('energy_level', getattr(user, 'current_energy_level', 6)), 6, 1, 10)
    if en_err:
        return en_err

    # Compute workout load over last 3 days
    cutoff_3d = datetime.now(timezone.utc) - timedelta(days=3)
    calc_load = 0
    active_days_set = set()

    for act in activity_logs:
        try:
            ts_str = act.get("timestamp")
            ts = datetime.fromisoformat(ts_str) if ts_str else None
            if ts and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts and ts >= cutoff_3d and str(act.get("activity_type", "")).lower() == "exercise":
                calc_load += int(act.get("duration_minutes") or 0)
                active_days_set.add(ts.date().isoformat())
        except Exception:
            continue

    load, load_err = coerce_int(request.args.get('workout_load_3d_minutes', calc_load), calc_load, 0, 1200)
    if load_err:
        return load_err

    days_since_rest, rest_err = coerce_int(
        request.args.get('days_since_rest', len(active_days_set)), len(active_days_set), 0, 30
    )
    if rest_err:
        return rest_err

    features = RecoveryFeatures(
        sleep_quality=sleep_q,
        sleep_hours=sleep_h,
        workout_load_3d_minutes=load,
        stress_level=stress,
        current_energy=energy,
        days_since_rest=days_since_rest,
    )

    predictor = get_or_create_recovery_predictor(user_id)
    assessment = predictor.assess_readiness(features)

    return jsonify({
        "user_id": user_id,
        "assessed_at": datetime.now(timezone.utc).isoformat(),
        **assessment,
    }), 200


@health_bp.route('/api/goals/<user_id>', methods=['GET'])
def get_goal_milestones(user_id):
    """Return milestone completion percentages and projected target dates."""
    user, err = require_user(user_id)
    if err:
        return err

    daily_logs = get_serialized_user_logs(user_id)
    activity_logs = state.activity_logs.get(user_id, [])

    tracker = GoalTracker(user, daily_logs, activity_logs)
    summary = tracker.get_milestone_summary()
    return jsonify(summary), 200


@health_bp.route('/api/digest/<user_id>', methods=['GET'])
def get_weekly_digest(user_id):
    """Return an executive multi-domain weekly digest summary."""
    user, err = require_user(user_id)
    if err:
        return err

    daily_logs = get_serialized_user_logs(user_id)
    activity_logs = state.activity_logs.get(user_id, [])
    sleep_logs = state.sleep_logs.get(user_id, [])

    generator = WeeklyDigestGenerator(user, daily_logs, activity_logs, sleep_logs)
    digest = generator.generate()
    return jsonify(digest), 200

