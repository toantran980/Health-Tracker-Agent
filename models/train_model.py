"""
Train and evaluate ProductivityPredictor on synthetic data.

CLI:
    python models/train_model.py                          # train + evaluate
    python models/train_model.py --incremental --save     # merge into saved model
    python models/train_model.py --train data/new.csv --model data/productivity_model.pkl

Behavior:
  - `--incremental` loads an existing model file (if present), appends the
    new training rows, and retrains — replacing the full-blown retrain that
    would otherwise discard prior learning.
  - `--save` persists the final model to `--model` for later reuse.
"""

import argparse
import csv
import os
import sys
from typing import List, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from ai_modules.productivity_predictor import ProductivityPredictor, Features  # noqa: E402


def load_csv(path: str) -> List[Tuple[Features, int]]:
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

def compute_rmse(predictor, data):
    errors = [(predictor.predict(f) - expected) ** 2 for f, expected in data]
    return (sum(errors) / len(errors)) ** 0.5 if errors else 0.0

def compute_r2(predictor, data):
    y_true = [expected for _, expected in data]
    y_pred = [predictor.predict(f) for f, _ in data]
    mean_y = sum(y_true) / len(y_true) if y_true else 0.0
    ss_tot = sum((y - mean_y) ** 2 for y in y_true)
    ss_res = sum((y_t - y_p) ** 2 for y_t, y_p in zip(y_true, y_pred))
    return 1 - ss_res / ss_tot if ss_tot != 0 else 0.0


def add_and_train(predictor, train_data):
    for features, expected in train_data:
        predictor.add_training_data(features, expected)
    predictor.train()


def main():
    parser = argparse.ArgumentParser(description="Train/evaluate the ProductivityPredictor.")
    parser.add_argument("--train", default=os.path.join(BASE_DIR, 'data', 'training_data.csv'),
                        help="CSV path containing training rows.")
    parser.add_argument("--eval", default=os.path.join(BASE_DIR, 'data', 'eval.csv'),
                        help="CSV path containing evaluation rows.")
    parser.add_argument("--model", default=os.path.join(BASE_DIR, 'data', 'productivity_model.pkl'),
                        help="Model file path used by --incremental/--save.")
    parser.add_argument("--incremental", action="store_true",
                        help="Merge --train rows into an existing model file instead of starting fresh.")
    parser.add_argument("--save", action="store_true",
                        help="Save the trained model to --model after training.")
    args = parser.parse_args()

    print(f"Loading training data from {args.train}...")
    train_data = load_csv(args.train)
    print(f"Loaded {len(train_data)} training samples.")

    print(f"Loading eval data from {args.eval}...")
    eval_data = load_csv(args.eval)
    print(f"Loaded {len(eval_data)} eval samples.")

    if args.incremental and os.path.exists(args.model):
        print(f"Loading existing model: {args.model} (incremental mode).")
        predictor = ProductivityPredictor.load_model(args.model)
        print(f"Existing training samples: {len(predictor.training_data)}.")
        merged_samples = len(predictor.training_data) + len(train_data)
        predictor.incremental_update(train_data)
        print(f"Merged training set now has {merged_samples} samples.")
    else:
        if args.incremental:
            print("No existing model found — starting from scratch.")
        predictor = ProductivityPredictor()
        print("Training fresh model...")
        add_and_train(predictor, train_data)

    mae_before = compute_mae(predictor, eval_data)
    rmse_before = compute_rmse(predictor, eval_data)
    r2_before = compute_r2(predictor, eval_data)
    print(f"\nMAE : {mae_before:.4f}")
    print(f"RMSE: {rmse_before:.4f}")
    print(f"R2  : {r2_before:.4f}")

    if args.save:
        predictor.save_model(args.model)
        print(f"\nSaved model to {args.model}.")

    print(f"\nModel info: {predictor.get_model_info()}")


if __name__ == '__main__':
    main()