"""
Train and evaluate the ActivityClassifier on the UCI Human Activity Recognition dataset.

CLI:
    python models/train_activity_classifier.py                     # train + evaluate
    python models/train_activity_classifier.py --model <pkl>       # custom output path

Behavior:
  - Uses the official test split shipped with the UCI HAR dataset (2,947 rows)
    as the final held-out test.
  - Carves a validation split out of the official train set (90/10, stratified)
    to select random-forest hyperparameters before the final test evaluation.
  - Excludes the per-sample ids (subject, Activity) from the feature matrix.

Usage:
    python models/train_activity_classifier.py
"""

import argparse
import glob
import os
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from ai_modules.activity_classifier import ActivityClassifier

UCI_DIR = os.path.join(BASE_DIR, "data", "external", "UCI_HAR_Dataset")
DEFAULT_MODEL = os.path.join(BASE_DIR, "data", "activity_classifier.pkl")

LABEL_KEYS = ("subject", "Activity")

PARAM_CANDIDATES = [
    ("rf_100_depth24", {"n_estimators": 100, "max_depth": 24}),
    ("rf_200_depth24", {"n_estimators": 200, "max_depth": 24}),
    ("rf_150_depth16", {"n_estimators": 150, "max_depth": 16}),
]


def load_split(name: str) -> tuple[np.ndarray, np.ndarray, list[str]]:
    path = glob.glob(os.path.join(UCI_DIR, f"{name}.csv"))
    if not path:
        raise FileNotFoundError(f"UCI HAR split not found: {os.path.join(UCI_DIR, name + '.csv')}")
    df = pd.read_csv(path[0])
    x = df.drop(columns=[col for col in LABEL_KEYS if col in df.columns]).to_numpy(dtype=float)
    labels = df["Activity"].tolist()
    return x, labels


def main():
    parser = argparse.ArgumentParser(
        description="Train/evaluate ActivityClassifier on the UCI HAR dataset."
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model output path.")
    args = parser.parse_args()

    train_x, train_labels = load_split("train")
    test_x, test_labels = load_split("test")
    print(f"Official train: {train_x.shape}  official test: {test_x.shape}")

    train_x, val_x, train_labels, val_labels = train_test_split(
        train_x, train_labels,
        test_size=0.1,
        random_state=42,
        stratify=train_labels,
    )
    print(f"Splits -> train: {train_x.shape[0]}, val: {val_x.shape[0]}, test: {len(test_labels)}")

    best_name, best_acc = None, None
    for name, params in PARAM_CANDIDATES:
        candidate = ActivityClassifier()
        candidate.train(train_x, train_labels, **params)
        val_predictions = [candidate.predict(vector) for vector in val_x]
        accuracy = accuracy_score(val_labels, val_predictions)
        print(f"  val accuracy {name:16s}: {accuracy:.4f}")
        if best_acc is None or accuracy > best_acc:
            best_name, best_acc, best_params = name, accuracy, params
    print(f"Selected hyperparameters: {best_name} (val accuracy {best_acc:.4f})")

    classifier = ActivityClassifier()
    classifier.train(train_x, train_labels, **best_params)

    test_predictions = [classifier.predict(vector) for vector in test_x]
    accuracy = accuracy_score(test_labels, test_predictions)
    print(f"\nFinal held-out test accuracy ({len(test_labels)} rows): {accuracy:.4f}")
    print(classification_report(test_labels, test_predictions, digits=4, zero_division=0))

    classifier.save_model(args.model)
    print(f"Saved model to {args.model}")


if __name__ == "__main__":
    main()