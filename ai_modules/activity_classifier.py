"""Activity Classifier — supervised model for smartphone-sensor human activity recognition.

Trained on the UCI Human Activity Recognition dataset (561 sensor features, 6 activities).
"""

from __future__ import annotations

import pickle

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder


class ActivityClassifier:
    """Random Forest classifier mapping 561 raw sensor features to an activity label."""

    def __init__(self, model_type: str = "random_forest"):
        self.model_type = model_type
        self.is_trained: bool = False
        self.classifier: RandomForestClassifier | None = None
        self.label_encoder = LabelEncoder()
        self.feature_names: list[str] | None = None
        self.classes_: list[str] = []

    def train(self, features: np.ndarray | list, labels: list[str], **params) -> None:
        """Fit the classifier on a feature matrix and aligned activity labels.

        Extra keyword arguments override the default random-forest hyperparameters.
        """
        X = np.asarray(features, dtype=float)
        y = self.label_encoder.fit_transform(labels)
        self.classes_ = list(self.label_encoder.classes_)
        hyperparameters = {
            "n_estimators": 200,
            "max_depth": 24,
            "min_samples_leaf": 1,
            "random_state": 42,
            "n_jobs": -1,
        }
        hyperparameters.update(params)
        self.classifier = RandomForestClassifier(**hyperparameters)
        self.classifier.fit(X, y)
        self.is_trained = True

    def _model(self) -> RandomForestClassifier:
        if not self.is_trained or self.classifier is None:
            raise RuntimeError("ActivityClassifier is not trained.")
        return self.classifier

    def predict(self, vector: np.ndarray | list) -> str:
        """Return the predicted activity label for a single feature vector."""
        index = self._model().predict([np.asarray(vector, dtype=float)])[0]
        return self.label_encoder.inverse_transform([index])[0]

    def predict_proba(self, vector: np.ndarray | list) -> dict[str, float]:
        """Return {activity_label: probability} sorted by probability (descending)."""
        probabilities = self._model().predict_proba([np.asarray(vector, dtype=float)])[0]
        ranked = sorted(
            zip(self.classes_, [float(p) for p in probabilities]),
            key=lambda item: item[1],
            reverse=True,
        )
        return dict(ranked)

    def top_activities(self, vector: np.ndarray | list, n: int = 3) -> list[dict]:
        """Return the n most likely activities with their probabilities."""
        return [
            {"activity": label, "probability": round(prob, 4)}
            for label, prob in list(self.predict_proba(vector).items())[:n]
        ]

    def save_model(self, path: str) -> None:
        """Serialize model to disk."""
        with open(path, "wb") as fh:
            pickle.dump({
                "model_type": self.model_type,
                "is_trained": self.is_trained,
                "classifier": self.classifier,
                "label_encoder": self.label_encoder,
                "feature_names": self.feature_names,
                "classes_": self.classes_,
            }, fh)

    @classmethod
    def load_model(cls, path: str) -> ActivityClassifier:
        """Deserialize model from disk."""
        with open(path, "rb") as fh:
            payload = pickle.load(fh)
        classifier = cls(model_type=payload.get("model_type", "random_forest"))
        classifier.is_trained = payload.get("is_trained", False)
        classifier.classifier = payload.get("classifier", None)
        classifier.label_encoder = payload.get("label_encoder", LabelEncoder())
        classifier.feature_names = payload.get("feature_names", None)
        classifier.classes_ = payload.get("classes_", [])
        return classifier