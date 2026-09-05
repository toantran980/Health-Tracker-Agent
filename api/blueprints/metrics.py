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

    # Load and train
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

    # Load eval data
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