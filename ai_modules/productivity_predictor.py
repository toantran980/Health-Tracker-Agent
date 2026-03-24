"""Productivity Predictor - Machine Learning model for study optimization"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import math
from dataclasses import dataclass


@dataclass
class Features:
    """Feature vector for productivity prediction"""
    hour_of_day: int
    day_of_week: int  # 0=Monday, 6=Sunday
    sleep_quality: float  # 0-10
    sleep_hours: float
    nutrition_score: float  # 0-100, based on macro balance
    energy_level: int  # 1-10 self-reported
    previous_session_duration: int  # minutes
    task_difficulty: int  # 1-10
    
    def to_vector(self) -> List[float]:
        """Convert features to vector for ML model"""
        return [
            self.hour_of_day / 24.0,
            self.day_of_week / 7.0,
            self.sleep_quality / 10.0,
            min(self.sleep_hours / 9.0, 1.0),
            self.nutrition_score / 100.0,
            self.energy_level / 10.0,
            min(self.previous_session_duration / 120.0, 1.0),
            self.task_difficulty / 10.0
        ]


class ProductivityPredictor:
    """Machine Learning model for predicting study session focus scores"""
    
    def __init__(self, model_type: str = "linear_regression"):
        self.model_type = model_type
        self.weights: List[float] = [
            0.25,  # hour_of_day - circadian rhythm
            0.10,  # day_of_week
            0.20,  # sleep_quality - strong impact
            0.15,  # sleep_hours
            0.18,  # nutrition_score
            0.22,  # energy_level - strong impact
            0.12,  # previous_session_duration
            0.08   # task_difficulty
        ]
        self.bias: float = 5.0
        self.training_data: List[Tuple[Features, int]] = []
        self.is_trained: bool = False
    
    def add_training_data(self, features: Features, actual_focus_score: int):
        """Add training example"""
        self.training_data.append((features, actual_focus_score))
    
    def train(self):
        """Train model using simple linear regression"""
        if len(self.training_data) < 3:
            # Insufficient data, use default weights
            self.is_trained = False
            return
        
        # Simplified training: adjust weights based on average correlation
        n = len(self.training_data)
        for feature_idx in range(len(self.weights)):
            feature_values = [data[0].to_vector()[feature_idx] for data in self.training_data]
            focus_scores = [data[1] for data in self.training_data]
            
            correlation = self._calculate_correlation(feature_values, focus_scores)
            # Adjust weight based on correlation strength
            self.weights[feature_idx] *= (1.0 + correlation * 0.1)
        
        # Normalize weights to sum to 1
        total_weight = sum(self.weights)
        self.weights = [w / total_weight for w in self.weights]
        
        self.is_trained = True
    
    def predict(self, features: Features) -> int:
        """
        Predict focus score for given features
        
        Returns:
            Focus score 1-10
        """
        if not self.is_trained and len(self.training_data) == 0:
            return self._predict_linear(features)
        
        if self.model_type == "linear_regression":
            return self._predict_linear(features)
        elif self.model_type == "nonlinear":
            return self._predict_nonlinear(features)
        else:
            return self._predict_linear(features)
    
    def _predict_linear(self, features: Features) -> int:
        """Linear regression prediction"""
        feature_vector = features.to_vector()
        
        # Weighted sum
        prediction = self.bias
        for i, feature_val in enumerate(feature_vector):
            prediction += feature_val * self.weights[i] * 10
        
        # Clamp to 1-10 range
        return max(1, min(10, round(prediction)))
    
    def _predict_nonlinear(self, features: Features) -> int:
        """Non-linear prediction using interaction terms"""
        base_score = self._predict_linear(features)
        
        # Add interaction effects
        # Good sleep + good nutrition = synergistic effect
        sleep_nutrition_boost = (features.sleep_quality / 10) * (features.nutrition_score / 100) * 2
        
        # High energy + suitable task difficulty = better focus
        difficulty_energy_match = 1.0 - abs((features.task_difficulty / 10) - (features.energy_level / 10))
        difficulty_boost = difficulty_energy_match * 1.5
        
        # Optimal hours (10-11am, 4-6pm)
        optimal_hours = [10, 11, 16, 17]
        hour_bonus = 2.0 if features.hour_of_day in optimal_hours else -1.0
        
        final_score = base_score + sleep_nutrition_boost + difficulty_boost + hour_bonus
        return max(1, min(10, round(final_score)))
    
    def _calculate_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient"""
        if len(x) < 2 or len(x) != len(y):
            return 0.0
        
        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denom_x = sum((xi - mean_x) ** 2 for xi in x)
        denom_y = sum((yi - mean_y) ** 2 for yi in y)
        
        denominator = math.sqrt(denom_x * denom_y)
        
        if denominator == 0:
            return 0.0
        return numerator / denominator
    
    def suggest_optimal_time(self, user_earliest: int = 8, user_latest: int = 22, 
                            available_hours: Optional[List[int]] = None) -> Tuple[int, int, float]:
        """
        Suggest optimal hour for study session
        
        Returns:
            (best_hour, day_of_week, predicted_focus_score)
        """
        best_hour = user_earliest
        best_day = 0
        best_focus = 0.0
        
        for day in range(5):  # Weekdays only
            for hour in range(user_earliest, user_latest):
                if available_hours and hour not in available_hours:
                    continue
                
                test_features = Features(
                    hour_of_day=hour,
                    day_of_week=day,
                    sleep_quality=7.0,  # Assume normal sleep
                    sleep_hours=8.0,
                    nutrition_score=75.0,  # Assume decent nutrition
                    energy_level=7,
                    previous_session_duration=60,
                    task_difficulty=5
                )
                
                focus = self.predict(test_features)
                if focus > best_focus:
                    best_focus = focus
                    best_hour = hour
                    best_day = day
        
        return best_hour, best_day, best_focus
    
    def estimate_session_duration(self, difficulty: int, energy_level: int, focus_prediction: int) -> int:
        """Estimate optimal session duration in minutes"""
        # Base: 60 minutes
        base_duration = 60
        
        # Difficulty adjustment
        if difficulty > 7:
            base_duration = 45  # Shorter for harder tasks
        elif difficulty < 3:
            base_duration = 90  # Longer for easier tasks
        
        # Energy adjustment
        energy_factor = energy_level / 10.0
        base_duration = int(base_duration * (0.8 + energy_factor * 0.4))
        
        # Focus adjustment
        focus_factor = focus_prediction / 10.0
        base_duration = int(base_duration * (0.9 + focus_factor * 0.2))
        
        # Clamp to reasonable range (25-180 minutes)
        return max(25, min(180, base_duration))
    
    def get_model_info(self) -> Dict:
        """Get model information and performance"""
        return {
            "model_type": self.model_type,
            "is_trained": self.is_trained,
            "training_samples": len(self.training_data),
            "weights": {
                "hour_of_day": self.weights[0],
                "day_of_week": self.weights[1],
                "sleep_quality": self.weights[2],
                "sleep_hours": self.weights[3],
                "nutrition_score": self.weights[4],
                "energy_level": self.weights[5],
                "previous_session_duration": self.weights[6],
                "task_difficulty": self.weights[7]
            }
        }
