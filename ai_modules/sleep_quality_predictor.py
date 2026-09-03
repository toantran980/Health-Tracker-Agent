"""Sleep Quality Predictor — Machine Learning model for predicting sleep quality."""

from __future__ import annotations

import pickle
from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import RandomForestRegressor


@dataclass
class SleepFeatures:
    """Feature vector for sleep quality prediction."""
    bedtime_hour: float         # 0-24 (e.g. 23.5 for 11:30pm)
    sleep_duration_h: float     # hours slept, e.g. 7.5
    caffeine_servings: int      # caffeine intake in cups/servings during the day
    exercise_minutes: int       # physical activity minutes on that day
    screen_time_bedtime_min: int # minutes of screen time within 1 hour before sleep
    stress_level: int           # 1-10 self-reported stress

    def to_vector(self) -> list[float]:
        """Normalize features into [0, 1] with interaction terms."""
        # Convert bedtime_hour so around 22:00-23:00 is optimal center
        # Distance from 22.5 (10:30 PM)
        bedtime_dist = abs(self.bedtime_hour - 22.5)
        if bedtime_dist > 12:
            bedtime_dist = 24 - bedtime_dist

        v = [
            min(bedtime_dist / 6.0, 1.0),
            min(max(self.sleep_duration_h, 0.0) / 10.0, 1.0),
            min(self.caffeine_servings / 6.0, 1.0),
            min(self.exercise_minutes / 120.0, 1.0),
            min(self.screen_time_bedtime_min / 60.0, 1.0),
            min(max(self.stress_level, 1) / 10.0, 1.0),
        ]

        # Interaction terms
        # 1) High caffeine + screen time exacerbates sleep quality drop
        v.append(v[2] * v[4])
        # 2) High exercise mitigates moderate stress
        v.append(v[3] * (1.0 - v[5]))
        # 3) Sufficient duration with low stress
        v.append(v[1] * (1.0 - v[5]))
        return v


class SleepQualityPredictor:
    """
    Random Forest Machine Learning model predicting sleep quality scores (1-10).
    Includes synthetic bootstrapping so model is immediately usable before extensive logging.
    """

    def __init__(self, model_type: str = "random_forest"):
        self.model_type = model_type
        self.training_data: list[tuple[SleepFeatures, int]] = []
        self.is_trained: bool = False
        self.rf_model: RandomForestRegressor | None = None
        self.bootstrap_synthetic_data()

    def bootstrap_synthetic_data(self) -> None:
        """Seed reasonable synthetic data reflecting sleep hygiene research."""
        samples = [
            # Ideal conditions: 10:30pm bedtime, 8h sleep, 1 caffeine, 45m exercise, 0 screen, low stress -> 9-10
            (SleepFeatures(22.5, 8.0, 1, 45, 0, 2), 10),
            (SleepFeatures(23.0, 7.5, 2, 30, 15, 3), 8),
            (SleepFeatures(22.0, 8.5, 0, 60, 0, 2), 9),
            # Moderate conditions
            (SleepFeatures(0.5, 6.5, 3, 20, 30, 5), 6),
            (SleepFeatures(23.5, 7.0, 2, 0, 45, 6), 6),
            (SleepFeatures(1.0, 6.0, 4, 15, 60, 7), 5),
            # Poor sleep conditions: late, high caffeine, no exercise, high screen time & stress
            (SleepFeatures(2.5, 4.5, 5, 0, 60, 8), 3),
            (SleepFeatures(3.0, 4.0, 6, 0, 60, 9), 2),
            (SleepFeatures(1.5, 5.0, 4, 10, 45, 8), 4),
            # Oversleeping / disrupted
            (SleepFeatures(4.0, 10.0, 2, 0, 60, 7), 4),
            (SleepFeatures(23.0, 8.0, 1, 40, 10, 3), 9),
            (SleepFeatures(0.0, 7.0, 2, 30, 20, 4), 7),
        ]
        for feat, score in samples:
            self.add_training_data(feat, score)
        self.train()

    def add_training_data(self, features: SleepFeatures, actual_score: int) -> None:
        """Add training example."""
        score_clamped = max(1, min(10, int(actual_score)))
        self.training_data.append((features, score_clamped))

    def train(self) -> None:
        """Fit Random Forest model on collected training examples."""
        if len(self.training_data) < 3:
            self.is_trained = False
            return
        X = np.array([f.to_vector() for f, _ in self.training_data])
        y = np.array([target for _, target in self.training_data])
        self.rf_model = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
        self.rf_model.fit(X, y)
        self.is_trained = True

    def predict(self, features: SleepFeatures) -> int:
        """Predict sleep quality rating (1-10)."""
        if self.is_trained and self.rf_model is not None:
            pred = self.rf_model.predict([features.to_vector()])[0]
            return max(1, min(10, round(float(pred))))

        # Heuristic fallback if untypically not trained
        base = 8.0
        if features.sleep_duration_h < 7.0:
            base -= (7.0 - features.sleep_duration_h) * 1.5
        elif features.sleep_duration_h > 9.0:
            base -= (features.sleep_duration_h - 9.0) * 0.5
        base -= features.caffeine_servings * 0.4
        base += min(features.exercise_minutes / 30.0, 1.5)
        base -= (features.screen_time_bedtime_min / 30.0) * 0.8
        base -= (features.stress_level - 3) * 0.5
        return max(1, min(10, round(base)))


    def get_sleep_hygiene_recommendations(self, features: SleepFeatures) -> list[str]:
        """Generate tailored sleep hygiene tips based on input features."""
        tips: list[str] = []
        if features.caffeine_servings >= 3:
            tips.append("Limit caffeine intake after early afternoon to avoid sleep disruption.")
        if features.screen_time_bedtime_min > 20:
            tips.append("Reduce screen exposure 30–60 minutes before bed or use blue-light filters.")
        if features.exercise_minutes < 20:
            tips.append("Incorporate at least 20–30 minutes of physical activity during the day.")
        if features.stress_level >= 7:
            tips.append("Practice wind-down rituals (e.g. journaling, light stretching, or meditation).")
        if features.sleep_duration_h < 7.0:
            tips.append("Target a window allowing 7–9 hours of dedicated sleep time.")
        if not tips:
            tips.append("Great sleep hygiene practices! Maintain your current sleep schedule.")
        return tips

    def save_model(self, path: str) -> None:
        """Serialize model to disk."""
        with open(path, "wb") as fh:
            pickle.dump({
                "model_type": self.model_type,
                "is_trained": self.is_trained,
                "training_data": self.training_data,
                "rf_model": self.rf_model,
            }, fh)

    @classmethod
    def load_model(cls, path: str) -> SleepQualityPredictor:
        """Deserialize model from disk."""
        with open(path, "rb") as fh:
            payload = pickle.load(fh)
        predictor = cls(model_type=payload.get("model_type", "random_forest"))
        predictor.is_trained = payload.get("is_trained", False)
        predictor.training_data = payload.get("training_data", [])
        predictor.rf_model = payload.get("rf_model", None)
        return predictor

    def incremental_update(self, new_examples: list[tuple[SleepFeatures, int]]) -> bool:
        """Merge new observations and retrain model."""
        for features, score in new_examples:
            self.add_training_data(features, score)
        self.train()
        return self.is_trained
