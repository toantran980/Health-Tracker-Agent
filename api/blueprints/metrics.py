import csv
from flask import Blueprint, jsonify, request
from ai_modules.productivity_predictor import ProductivityPredictor, Features
import os

metrics_bp = Blueprint('metrics', __name__, url_prefix='/api/metrics')

@metrics_bp.route('/productivity_predictor', methods=['GET'])
def productivity_predictor_metrics():
    """Return MAE for ProductivityPredictor using evaluation CSV (configurable path)"""
    # Use ?file=... query parameter for evaluation file path
    csv_path = request.args.get('file')
    if not csv_path:
        return jsonify({"error": "No evaluation file specified. Pass ?file=/path/to/eval.csv as a query parameter."}), 400
    test_cases = []
    try:
        with open(csv_path, newline='') as csvfile:
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
                expected = int(row["expected_focus_score"])
                test_cases.append((features, expected))
    except Exception as e:
        return jsonify({"error": f"Could not load evaluation data: {e}", "csv_path": csv_path}), 500

    predictor = ProductivityPredictor()
    errors = []
    for features, expected in test_cases:
        pred = predictor.predict(features)
        errors.append(abs(pred - expected))
    mae = sum(errors) / len(errors) if errors else None
    return jsonify({
        "model": "ProductivityPredictor",
        "metric": "MAE",
        "mae": mae,
        "n": len(errors),
        "csv_path": csv_path
    })
