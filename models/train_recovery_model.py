"""
Train and evaluate the module-specific RecoveryPredictor on FitBit wearable data.

CLI:
    python models/train_recovery_model.py                 # train + evaluate
    python models/train_recovery_model.py --model <pkl>   # custom output path

Behavior:
  - Merges FitBit daily activity with sleep records to derive per-person,
    per-day recovery features.
  - FitBit does not provide a true readiness label, so the training target is
    a documented, data-derived heuristic proxy (same formula the predictor's
    fallback path uses), giving the model realistic wearable feature
    distributions while keeping the label definition transparent.
  - Splits data into train / validation / test (70/15/15). Validation selects
    the best regressor family; test reports the final, held-out metrics.

Usage:
    python models/train_recovery_model.py
"""

import argparse
import glob
import os
import sys

import numpy as np
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

from ai_modules.recovery_predictor import RecoveryFeatures, RecoveryPredictor
from models.evaluation import compute_metrics

FITBIT_DIR = os.path.join(BASE_DIR, "data", "external", "fitbit_dataset")
DEFAULT_MODEL = os.path.join(BASE_DIR, "data", "recovery_model.pkl")

# FitBit does not record stress or perceived energy; neutral defaults.
DEFAULT_STRESS_LEVEL = 3
DEFAULT_CURRENT_ENERGY = 6
REST_THRESHOLD_MINUTES = 20

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


def minutes_to_quality(total_minutes: float) -> int:
    """Map sleep duration in minutes to a 1-10 quality proxy using sleep research."""
    if total_minutes <= 0:
        return 1
    if total_minutes < 360:
        quality = 1 + total_minutes / 360 * 5
    elif total_minutes < 420:
        quality = 6 + (total_minutes - 360) / 60 * 2
    elif total_minutes <= 540:
        quality = 8 + (total_minutes - 420) / 120 * 2
    else:
        quality = 10 - (total_minutes - 540) / 120 * 3
    return max(1, min(10, round(quality)))


def readiness_label(quality: int, sleep_hours: float, load_3d: int, days_rest: int) -> int:
    """Data-derived readiness proxy used to label FitBit recovery rows."""
    base = 0.35 * quality + 0.35 * DEFAULT_CURRENT_ENERGY - 0.2 * DEFAULT_STRESS_LEVEL
    if load_3d > 150:
        base -= 1.5
    if days_rest >= 5:
        base -= 1.0
    return max(1, min(10, round(base)))


def load_merged_days() -> pd.DataFrame:
    activity = pd.concat(
        [pd.read_csv(path) for path in glob.glob(os.path.join(FITBIT_DIR, "**", "dailyActivity_merged.csv"), recursive=True)],
        ignore_index=True,
    )
    activity["date"] = pd.to_datetime(activity["ActivityDate"])
    activity["active_minutes"] = activity["VeryActiveMinutes"] + activity["FairlyActiveMinutes"]

    sleep_files = glob.glob(os.path.join(FITBIT_DIR, "**", "sleepDay_merged.csv"), recursive=True)
    sleep = pd.concat(
        [pd.read_csv(path) for path in sleep_files],
        ignore_index=True,
    )
    sleep["date"] = pd.to_datetime(sleep["SleepDay"].str.split().str[0])

    merged = activity.merge(sleep, on=["Id", "date"], suffixes=("", "_sleep"))
    merged = merged.sort_values(["Id", "date"]).reset_index(drop=True)
    return merged


def build_examples(days: pd.DataFrame) -> list[tuple[RecoveryFeatures, int]]:
    examples = []
    for user_id, user_days in days.groupby("Id"):
        user_days = user_days.sort_values("date")
        user_days["load_3d"] = user_days["active_minutes"].rolling(3, min_periods=1).sum()
        rest_since: list[int] = []
        last_rest = None
        for index, row in user_days.iterrows():
            if row["active_minutes"] < REST_THRESHOLD_MINUTES:
                last_rest = row["date"]
            rest_days = (row["date"] - last_rest).days if last_rest is not None else 7
            rest_since.append(rest_days)
        user_days["days_since_rest"] = rest_since

        for _, row in user_days.iterrows():
            quality = minutes_to_quality(float(row["TotalMinutesAsleep"]))
            sleep_hours = float(row["TotalMinutesAsleep"]) / 60.0
            load_3d = int(row["load_3d"])
            days_rest = int(row["days_since_rest"])
            features = RecoveryFeatures(
                sleep_quality=float(quality),
                sleep_hours=sleep_hours,
                workout_load_3d_minutes=load_3d,
                stress_level=DEFAULT_STRESS_LEVEL,
                current_energy=DEFAULT_CURRENT_ENERGY,
                days_since_rest=days_rest,
            )
            examples.append((features, readiness_label(quality, sleep_hours, load_3d, days_rest)))
    return examples


def regressor_vectors(examples) -> tuple[list, list]:
    return [item.to_vector() for item, _ in examples], [target for _, target in examples]


def main():
    parser = argparse.ArgumentParser(
        description="Train/evaluate RecoveryPredictor on FitBit wearable data."
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model output path.")
    args = parser.parse_args()

    days = load_merged_days()
    print(f"Merged {len(days)} user-day records from {FITBIT_DIR}")

    examples = build_examples(days)
    print(f"Built {len(examples)} labeled recovery examples ({len(days['Id'].unique())} users)")

    np.random.seed(42)
    indices = np.random.permutation(len(examples))
    train_size = int(0.7 * len(examples))
    rest = [examples[i] for i in indices[train_size:]]
    val, test = train_test_split(rest, test_size=0.5, random_state=42)
    train = [examples[i] for i in indices[:train_size]]
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

    predictor = RecoveryPredictor()
    predictor.training_data = []
    for features, readiness in train + val:
        predictor.add_training_data(features, readiness)
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