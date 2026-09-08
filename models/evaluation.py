"""Evaluation helpers shared by model training scripts and API endpoints."""

from collections.abc import Iterable

import numpy as np
from sklearn.ensemble import (
    ExtraTreesRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.model_selection import KFold, cross_val_score


def compute_metrics(predictor, data: Iterable[tuple[object, int]], baseline: float) -> dict:
    """Return regression and ordinal metrics for a labelled evaluation set."""
    cases = list(data)
    if not cases:
        return {
            "mae": None,
            "rmse": None,
            "r2": None,
            "within_one_accuracy": None,
            "baseline_mae": None,
            "baseline_rmse": None,
            "improvement_vs_baseline_pct": None,
            "n": 0,
        }

    actual = [expected for _, expected in cases]
    predicted = [predictor.predict(features) for features, _ in cases]
    errors = [prediction - expected for prediction, expected in zip(predicted, actual)]
    absolute_errors = [abs(error) for error in errors]
    squared_errors = [error ** 2 for error in errors]

    mean_actual = sum(actual) / len(actual)
    ss_total = sum((value - mean_actual) ** 2 for value in actual)
    mae = sum(absolute_errors) / len(cases)
    rmse = (sum(squared_errors) / len(cases)) ** 0.5
    baseline_errors = [expected - baseline for expected in actual]
    baseline_mae = sum(abs(error) for error in baseline_errors) / len(cases)
    baseline_rmse = (sum(error ** 2 for error in baseline_errors) / len(cases)) ** 0.5

    return {
        "mae": mae,
        "rmse": rmse,
        "r2": 1 - sum(squared_errors) / ss_total if ss_total else 0.0,
        "within_one_accuracy": sum(error <= 1 for error in absolute_errors) / len(cases),
        "baseline_mae": baseline_mae,
        "baseline_rmse": baseline_rmse,
        "improvement_vs_baseline_pct": (
            (baseline_mae - mae) / baseline_mae * 100 if baseline_mae else 0.0
        ),
        "n": len(cases),
    }


def benchmark_regressors(data: Iterable[tuple[object, int]], folds: int = 5) -> dict:
    """Compare tree regressors with shuffled cross-validation on training data."""
    cases = list(data)
    if len(cases) < folds:
        return {}

    features = np.array([item.to_vector() for item, _ in cases])
    targets = np.array([target for _, target in cases])
    split = KFold(n_splits=folds, shuffle=True, random_state=42)
    regressors = {
        "random_forest": RandomForestRegressor(
            n_estimators=300,
            max_depth=6,
            min_samples_leaf=3,
            max_features="sqrt",
            random_state=42,
            n_jobs=-1,
        ),
        "extra_trees": ExtraTreesRegressor(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=2,
            max_features="sqrt",
            random_state=42,
            n_jobs=-1,
        ),
        "hist_gradient_boosting": HistGradientBoostingRegressor(
            max_iter=150,
            max_leaf_nodes=15,
            l2_regularization=1.0,
            early_stopping=True,
            random_state=42,
        ),
    }

    results = {}
    for name, regressor in regressors.items():
        scores = -cross_val_score(
            regressor,
            features,
            targets,
            cv=split,
            scoring="neg_mean_absolute_error",
            n_jobs=1,
        )
        results[name] = {
            "mae_mean": float(scores.mean()),
            "mae_std": float(scores.std()),
            "folds": folds,
        }
    return results