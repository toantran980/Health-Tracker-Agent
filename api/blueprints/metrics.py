import csv
from flask import Blueprint, jsonify, request
from ai_modules.productivity_predictor import ProductivityPredictor, Features
from api.blueprints.helpers import error_response
from models.evaluation import compute_metrics

metrics_bp = Blueprint('metrics', __name__, url_prefix='/api/metrics')


@metrics_bp.route('/productivity_predictor', methods=['GET'])
def productivity_predictor_metrics():
    train_path = 'data/training_data.csv'
    eval_path  = request.args.get('file', 'data/eval.csv')

    train_cases = []
    try:
        with open(train_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                features = Features(
                    int(row["hour_of_day"]),
                    int(row["day_of_week"]),
                    float(row["sleep_quality"]),
                    float(row["sleep_hours"]),
                    float(row["nutrition_score"]),
                    int(row["energy_level"]),
                    int(row["previous_session_duration"]),
                    int(row["task_difficulty"])
                )
                train_cases.append((features, int(row["expected_focus_score"])))
    except Exception as e:  # noqa: BLE001
        return error_response(f"Could not load training data: {e}", "TRAINING_DATA_LOAD_FAILED", 500)

    predictor = ProductivityPredictor()
    for features, expected in train_cases:
        predictor.add_training_data(features, expected)
    predictor.train()

    test_cases = []
    try:
        with open(eval_path, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                features = Features(
                    int(row["hour_of_day"]),
                    int(row["day_of_week"]),
                    float(row["sleep_quality"]),
                    float(row["sleep_hours"]),
                    float(row["nutrition_score"]),
                    int(row["energy_level"]),
                    int(row["previous_session_duration"]),
                    int(row["task_difficulty"])
                )
                test_cases.append((features, int(row["expected_focus_score"])))
    except Exception as e:  # noqa: BLE001
        return error_response(f"Could not load evaluation data: {e}", "EVAL_DATA_LOAD_FAILED", 500)

    training_mean = sum(expected for _, expected in train_cases) / len(train_cases)
    metrics = compute_metrics(predictor, test_cases, round(training_mean))

    return jsonify({
        "model": "ProductivityPredictor",
        **metrics,
        "csv_path": eval_path
    })


@metrics_bp.route('/dependencies', methods=['GET'])
def get_dependency_metrics():
    """Return runtime dependency health metrics, database latency, and external API statistics."""
    import sys
    import time
    from datetime import datetime, timezone
    import config
    from api.blueprints import state
    from api.external_api_common import EXTERNAL_METRICS

    mongo_healthy = False
    mongo_latency_ms = 0.0
    if state.mongo_store.enabled:
        mongo_healthy, mongo_latency_ms = state.mongo_store.ping()

    persisted_users = (
        state.mongo_store.count_users() if state.mongo_store.enabled else len(state.users)
    )

    try:
        from api.routes import START_TIME
        uptime_sec = round(time.time() - START_TIME, 1)
    except Exception:  # noqa: BLE001
        uptime_sec = 0.0

    return jsonify({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_sec,
        "environment": config.ENVIRONMENT,
        "python_version": sys.version.split()[0],
        "database": {
            "type": "mongodb",
            "enabled": state.mongo_store.enabled,
            "healthy": mongo_healthy,
            "latency_ms": mongo_latency_ms,
            "user_count": persisted_users,
        },
        "external_apis": EXTERNAL_METRICS,
        "memory_caches": {
            "users": len(state.users),
            "daily_logs": len(state.daily_logs),
            "activity_logs": sum(len(v) for v in state.activity_logs.values()),
            "sleep_logs": sum(len(v) for v in state.sleep_logs.values()),
            "recent_submissions_tracked": len(state.recent_submissions),
        }
    }), 200