"""
Train and evaluate the module-specific SleepQualityPredictor on the Sleep Health dataset.

CLI:
    python models/train_sleep_model.py                       # train + evaluate
    python models/train_sleep_model.py --csv <csv> --model <pkl>   # custom paths

Behavior:
  - Maps the Sleep Health survey columns onto SleepFeatures.
  - Columns absent from the dataset (bedtime, caffeine, screen time) use neutral
    default values so training is driven by the real survey columns.
  - Splits data into train / validation / test (70/15/15). Validation selects
    the best regressor family; test reports the final, held-out metrics.

Usage:
    python models/train_sleep_model.py
"""

import argparse
import os
import sys

import pandas as pd
from sklearn.ensemble import (
    ExtraTreesRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from ai_modules.sleep_quality_predictor import SleepFeatures, SleepQualityPredictor
from models.evaluation import compute_metrics

DEFAULT_CSV = os.path.join(
    BASE_DIR,
    "data", "external", "sleep_health_and_lifestyle",
    "Sleep_health_and_lifestyle_dataset.csv",
)
DEFAULT_MODEL = os.path.join(BASE_DIR, "data", "sleep_quality_model.pkl")

# Neutral defaults for survey fields not present in the dataset.
DEFAULT_BEDTIME_HOUR = 22.5
DEFAULT_CAFFEINE_SERVINGS = 1
DEFAULT_SCREEN_TIME_MIN = 15

REGRESSORS = {
    "random_forest": RandomForestRegressor(
        n_estimators=300, max_depth=8, min_samples_leaf=3, max_features="sqrt",
        random_state=42, n_jobs=-1,
    ),
    "extra_trees": ExtraTreesRegressor(
        n_estimators=300, max_depth=10, min_samples_leaf=2, max_features="sqrt",
        random_state=42, n_jobs=-1,
    ),
    "hist_gradient_boosting": HistGradientBoostingRegressor(
        max_iter=200, max_leaf_nodes=15, l2_regularization=1.0,
        early_stopping=True, random_state=42,
    ),
}


def dataset_to_examples(df: pd.DataFrame) -> list[tuple[SleepFeatures, int]]:
    examples = []
    for _, row in df.iterrows():
        features = SleepFeatures(
            bedtime_hour=DEFAULT_BEDTIME_HOUR,
            sleep_duration_h=float(row["Sleep Duration"]),
            caffeine_servings=DEFAULT_CAFFEINE_SERVINGS,
            exercise_minutes=int(row["Physical Activity Level"]),
            screen_time_bedtime_min=DEFAULT_SCREEN_TIME_MIN,
            stress_level=int(row["Stress Level"]),
        )
        examples.append((features, int(row["Quality of Sleep"])))
    return examples


def split_examples(examples):
    train, rest = train_test_split(examples, test_size=0.3, random_state=42)
    val, test = train_test_split(rest, test_size=0.5, random_state=42)
    return train, val, test


def regressor_vectors(examples) -> tuple[list, list]:
    return [item.to_vector() for item, _ in examples], [target for _, target in examples]


def main():
    parser = argparse.ArgumentParser(
        description="Train/evaluate SleepQualityPredictor on the Sleep Health dataset."
    )
    parser.add_argument("--csv", default=DEFAULT_CSV, help="Sleep Health CSV path.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model output path.")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    examples = dataset_to_examples(df)
    print(f"Loaded {len(examples)} labeled sleep-quality samples from {args.csv}")

    train, val, test = split_examples(examples)
    print(f"Splits -> train: {len(train)}, val: {len(val)}, test: {len(test)}")

    x_train, y_train = regressor_vectors(train)
    x_val, y_val = regressor_vectors(val)

    best_name, best_mae = None, None
    for name, regressor in REGRESSORS.items():
        regressor.fit(x_train, y_train)
        mae = mean_absolute_error(y_val, regressor.predict(x_val))
        print(f"  val MAE {name:22s}: {mae:.4f}")
        if best_mae is None or mae < best_mae:
            best_name, best_mae = name, mae
    print(f"Selected regressor: {best_name} (val MAE {best_mae:.4f})")

    predictor = SleepQualityPredictor()
    predictor.training_data = []
    for features, quality in train + val:
        predictor.add_training_data(features, quality)
    selected = REGRESSORS[best_name].fit(x_train + x_val, y_train + y_val)
    predictor.rf_model = selected
    predictor.is_trained = True
    print(f"Retrained {best_name} on train+val ({len(train)} + {len(val)} rows)")

    baseline = sum(target for _, target in train) / len(train)
    metrics = compute_metrics(predictor, test, baseline)
    print(f"\nFinal held-out test split (n={metrics['n']}):")
    print(f"  MAE                    : {metrics['mae']:.4f}")
    print(f"  RMSE                   : {metrics['rmse']:.4f}")
    print(f"  R2                     : {metrics['r2']:.4f}")
    print(f"  Within 1 point accuracy: {metrics['within_one_accuracy']:.4f}")
    print(f"  Improvement vs baseline: {metrics['improvement_vs_baseline_pct']:.2f}%")

    predictor.save_model(args.model)
    print(f"\nSaved model to {args.model}")


if __name__ == "__main__":
    main()