"""AI Modules Package"""

from .activity_classifier import ActivityClassifier
from .activity_recommendation_engine import ActivityRecommendationEngine
from .goal_tracker import GoalTracker
from .health_risk_assessor import HealthRiskAssessor, HealthWarning
from .knowledge_base import BehavioralAnalyzer, KnowledgeBase
from .meal_recommendation_engine import MealRecommendationEngine
from .nutrition_analyzer import NutritionAnalyzer
from .productivity_predictor import Features, ProductivityPredictor
from .recovery_predictor import RecoveryFeatures, RecoveryPredictor
from .scheduler_optimizer import ScheduleOptimizer, TimeSlot
from .sleep_quality_predictor import SleepFeatures, SleepQualityPredictor
from .weekly_digest import WeeklyDigestGenerator

__all__ = [
    'ActivityClassifier',
    'ActivityRecommendationEngine',
    'BehavioralAnalyzer',
    'Features',
    'GoalTracker',
    'HealthRiskAssessor',
    'HealthWarning',
    'KnowledgeBase',
    'MealRecommendationEngine',
    'NutritionAnalyzer',
    'ProductivityPredictor',
    'RecoveryFeatures',
    'RecoveryPredictor',
    'ScheduleOptimizer',
    'SleepFeatures',
    'SleepQualityPredictor',
    'TimeSlot',
    'WeeklyDigestGenerator',
]

