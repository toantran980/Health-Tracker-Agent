"""Recovery & Readiness Predictor — Machine Learning model for athletic readiness and stress recovery."""

from __future__ import annotations

import pickle
from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import RandomForestRegressor


@dataclass
class RecoveryFeatures:
    """Feature vector for physical readiness and stress recovery."""
    sleep_quality: float          # 1-10
    sleep_hours: float            # e.g. 7.5
    workout_load_3d_minutes: int  # cumulative workout minutes over past 3 days
    stress_level: int             # 1-10 self-reported stress
    current_energy: int           # 1-10
    days_since_rest: int          # consecutive active days without rest

    def to_vector(self) -> list[float]:
        v = [
            min(max(self.sleep_quality, 1.0) / 10.0, 1.0),
            min(max(self.sleep_hours, 0.0) / 10.0, 1.0),
            min(self.workout_load_3d_minutes / 240.0, 1.0),
            min(max(self.stress_level, 1) / 10.0, 1.0),
            min(max(self.current_energy, 1) / 10.0, 1.0),
            min(self.days_since_rest / 7.0, 1.0),
        ]
        # Interaction terms:
        # High sleep + high energy = recovery synergy
        v.append(v[0] * v[4])
        # High workout load + high stress = high fatigue penalty
        v.append(v[2] * v[3])
        # Consecutive active days without rest penalizes energy
        v.append(v[5] * (1.0 - v[4]))
        return v


class RecoveryPredictor:
    """
    ML model (Random Forest) predicting daily physical readiness (1-10) and training load advice.
    Bootstrapped with empirical athletic recovery heuristics.
    """

    def __init__(self, model_type: str = "random_forest"):
        self.model_type = model_type
        self.training_data: list[tuple[RecoveryFeatures, int]] = []
        self.is_trained: bool = False
        self.rf_model: RandomForestRegressor | None = None
        self.bootstrap_synthetic_data()

    def bootstrap_synthetic_data(self) -> None:
        """Seed training data for physical readiness."""
        samples = [
            # High readiness: great sleep, moderate load, low stress, high energy
            (RecoveryFeatures(9.0, 8.5, 60, 2, 9, 1), 10),
            (RecoveryFeatures(8.0, 8.0, 90, 3, 8, 2), 9),
            (RecoveryFeatures(7.5, 7.5, 45, 4, 8, 0), 8),
            # Moderate readiness
            (RecoveryFeatures(6.5, 7.0, 120, 5, 6, 3), 6),
            (RecoveryFeatures(7.0, 6.5, 100, 4, 6, 2), 6),
            (RecoveryFeatures(6.0, 6.0, 80, 6, 5, 4), 5),
            # Low readiness / over-trained
            (RecoveryFeatures(4.0, 5.0, 180, 8, 3, 5), 3),
            (RecoveryFeatures(3.0, 4.5, 200, 9, 2, 6), 2),
            (RecoveryFeatures(5.0, 5.5, 150, 7, 4, 5), 4),
            # High stress, minimal workout
            (RecoveryFeatures(5.0, 6.0, 20, 9, 4, 1), 4),
            # Post-rest day recovery
            (RecoveryFeatures(8.5, 9.0, 0, 2, 9, 0), 10),
        ]
        for feat, score in samples:
            self.add_training_data(feat, score)
        self.train()

    def add_training_data(self, features: RecoveryFeatures, score: int) -> None:
        score_clamped = max(1, min(10, int(score)))
        self.training_data.append((features, score_clamped))

    def train(self) -> None:
        if len(self.training_data) < 3:
            self.is_trained = False
            return
        X = np.array([f.to_vector() for f, _ in self.training_data])
        y = np.array([target for _, target in self.training_data])
        self.rf_model = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
        self.rf_model.fit(X, y)
        self.is_trained = True

    def predict(self, features: RecoveryFeatures) -> int:
        """Predict readiness score (1-10)."""
        if self.is_trained and self.rf_model is not None:
            pred = self.rf_model.predict([features.to_vector()])[0]
            return max(1, min(10, round(float(pred))))

        # Fallback heuristic calculation
        base = (features.sleep_quality * 0.35) + (features.current_energy * 0.35)
        base -= (features.stress_level * 0.2)
        if features.workout_load_3d_minutes > 150:
            base -= 1.5
        if features.days_since_rest >= 5:
            base -= 1.0
        return max(1, min(10, round(base)))


    def assess_readiness(self, features: RecoveryFeatures) -> dict[str, any]:
        """
        Produce a full readiness assessment report with training guidance.
        """
        score = self.predict(features)
        if score >= 8:
            status = "optimal"
            recommendation = "High intensity workouts and heavy resistance training are recommended."
            max_intensity = "high"
        elif score >= 6:
            status = "good"
            recommendation = "Standard training loads appropriate; monitor hydration and pacing."
            max_intensity = "moderate"
        elif score >= 4:
            status = "reduced"
            recommendation = "Active recovery suggested (e.g. yoga, light walking, mobility work)."
            max_intensity = "light"
        else:
            status = "exhausted"
            recommendation = "Full rest or recovery day strongly advised to prevent injury and burnout."
            max_intensity = "rest_only"

        return {
            "readiness_score": score,
            "status": status,
            "recommendation": recommendation,
            "max_intensity": max_intensity,
            "features_snapshot": {
                "sleep_quality": features.sleep_quality,
                "sleep_hours": features.sleep_hours,
                "workout_load_3d_minutes": features.workout_load_3d_minutes,
                "stress_level": features.stress_level,
                "current_energy": features.current_energy,
                "days_since_rest": features.days_since_rest,
            }
        }

    def save_model(self, path: str) -> None:
        with open(path, "wb") as fh:
            pickle.dump({
                "model_type": self.model_type,
                "is_trained": self.is_trained,
                "training_data": self.training_data,
                "rf_model": self.rf_model,
            }, fh)

    @classmethod
    def load_model(cls, path: str) -> RecoveryPredictor:
        with open(path, "rb") as fh:
            payload = pickle.load(fh)
        predictor = cls(model_type=payload.get("model_type", "random_forest"))
        predictor.is_trained = payload.get("is_trained", False)
        predictor.training_data = payload.get("training_data", [])
        predictor.rf_model = payload.get("rf_model", None)
        return predictor

    def incremental_update(self, new_examples: list[tuple[RecoveryFeatures, int]]) -> bool:
        for features, score in new_examples:
            self.add_training_data(features, score)
        self.train()
        return self.is_trained
