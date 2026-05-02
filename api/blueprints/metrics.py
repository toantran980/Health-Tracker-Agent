import csv
from flask import Blueprint, jsonify, request
from ai_modules.productivity_predictor import ProductivityPredictor, Features

metrics_bp = Blueprint('metrics', __name__, url_prefix='/api/metrics')


def compute_rmse(predictor, data):
    errors = [(predictor.predict(f) - expected) ** 2 for f, expected in data]
    return (sum(errors) / len(errors)) ** 0.5 if errors else 0.0


def compute_r2(predictor, data):
    y_true = [expected for _, expected in data]
    y_pred = [predictor.predict(f) for f, _ in data]
    mean_y = sum(y_true) / len(y_true)
    ss_tot = sum((y - mean_y) ** 2 for y in y_true)
    ss_res = sum((y_t - y_p) ** 2 for y_t, y_p in zip(y_true, y_pred))
    return 1 - ss_res / ss_tot if ss_tot != 0 else 0.0


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
    except Exception as e:
        return jsonify({"error": f"Could not load training data: {e}"}), 500

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
    except Exception as e:
        return jsonify({"error": f"Could not load evaluation data: {e}"}), 500

    # Compute all metrics
    mae  = sum(abs(predictor.predict(f) - e) for f, e in test_cases) / len(test_cases) if test_cases else None
    rmse = compute_rmse(predictor, test_cases)
    r2   = compute_r2(predictor, test_cases)

    return jsonify({
        "model": "ProductivityPredictor",
        "mae":  mae,
        "rmse": rmse,
        "r2":   r2,
        "n":    len(test_cases),
        "csv_path": eval_path
    })