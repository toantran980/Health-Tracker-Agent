import csv
from ai_modules.productivity_predictor import ProductivityPredictor, Features

TRAIN_PATH = "data/training_data.csv"
EVAL_PATH = "data/eval.csv"

def load_cases(csv_path):
    cases = []
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
            cases.append((features, expected))
    return cases

def main():
    # Load training data
    train_cases = load_cases(TRAIN_PATH)
    predictor = ProductivityPredictor()
    for features, expected in train_cases:
        predictor.add_training_data(features, expected)
    predictor.train()

    # Evaluate on eval data
    eval_cases = load_cases(EVAL_PATH)
    errors = []
    for features, expected in eval_cases:
        pred = predictor.predict(features)
        errors.append(abs(pred - expected))
    mae = sum(errors) / len(errors) if errors else None
    print(f"Eval MAE: {mae:.3f} (n={len(errors)})")

if __name__ == "__main__":
    main()
