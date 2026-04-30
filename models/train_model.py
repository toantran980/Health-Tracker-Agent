"""
Train the ProductivityPredictor on synthetic data and evaluate MAE.
"""

import csv
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_modules.productivity_predictor import ProductivityPredictor, Features


def load_csv(path: str):
    rows = []
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            features = Features(
                hour_of_day=int(row['hour_of_day']),
                day_of_week=int(row['day_of_week']),
                sleep_quality=float(row['sleep_quality']),
                sleep_hours=float(row['sleep_hours']),
                nutrition_score=float(row['nutrition_score']),
                energy_level=int(row['energy_level']),
                previous_session_duration=int(row['previous_session_duration']),
                task_difficulty=int(row['task_difficulty']),
            )
            expected = int(row['expected_focus_score'])
            rows.append((features, expected))
    return rows


def compute_mae(predictor, data):
    errors = [abs(predictor.predict(f) - expected) for f, expected in data]
    return sum(errors) / len(errors) if errors else 0.0


def main():
    train_path = os.path.join('data', 'training_data.csv')
    eval_path  = os.path.join('data', 'eval.csv')

    print(f"Loading training data from {train_path}...")
    train_data = load_csv(train_path)
    print(f"Loaded {len(train_data)} training samples.")

    print(f"Loading eval data from {eval_path}...")
    eval_data = load_csv(eval_path)
    print(f"Loaded {len(eval_data)} eval samples.")

    predictor = ProductivityPredictor()

    # Evaluate before training
    mae_before = compute_mae(predictor, eval_data)
    print(f"\nMAE before training: {mae_before:.4f}")

    # Train
    print("\nTraining model...")
    training_samples = [(f, e) for f, e in train_data]
    predictor.train(training_samples)

    # Evaluate after training
    mae_after = compute_mae(predictor, eval_data)
    print(f"MAE after training:  {mae_after:.4f}")
    print(f"Improvement:         {mae_before - mae_after:.4f}")
    print(f"\nModel info: {predictor.get_model_info()}")


if __name__ == '__main__':
    main()
