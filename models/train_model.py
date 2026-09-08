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

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from ai_modules.productivity_predictor import (
    Features,
    ProductivityPredictor,
)
from models.evaluation import benchmark_regressors, compute_metrics


def load_csv(path: str) -> list[tuple[Features, int]]:
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

    training_mean = sum(expected for _, expected in train_data) / len(train_data)
    cv_results = benchmark_regressors(train_data)
    print("\n5-fold cross-validation MAE (training data only):")
    for model_name, result in cv_results.items():
        print(f"  {model_name:24s}: {result['mae_mean']:.4f} +/- {result['mae_std']:.4f}")

    metrics = compute_metrics(predictor, eval_data, round(training_mean))
    print(f"\nMAE                     : {metrics['mae']:.4f}")
    print(f"RMSE                    : {metrics['rmse']:.4f}")
    print(f"R2                      : {metrics['r2']:.4f}")
    print(f"Within 1 point accuracy : {metrics['within_one_accuracy']:.4f}")
    print(f"Baseline MAE            : {metrics['baseline_mae']:.4f}")
    print(f"Improvement vs baseline : {metrics['improvement_vs_baseline_pct']:.2f}%")

    if args.save:
        predictor.save_model(args.model)
        print(f"\nSaved model to {args.model}.")

    print(f"\nModel info: {predictor.get_model_info()}")


if __name__ == '__main__':
    main()