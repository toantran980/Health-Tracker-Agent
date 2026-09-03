"""
state.py

Shared in-memory stores and singletons used across all blueprint modules.
All dicts are module-level so mutations are visible everywhere.
"""

import logging

from ai_modules import (
    KnowledgeBase,
    MealRecommendationEngine,
    NutritionAnalyzer,
    RecoveryPredictor,
    SleepQualityPredictor,
)
from ai_modules.health_chatbot import HealthChatbot
from api.mongo_store import MongoStore
from data.dataset_loader_v2 import load_food_database
from models.meal import DailyNutritionLog
from models.user_profile import UserProfile

# Load food DB once at startup
log = logging.getLogger(__name__)

try:
    GLOBAL_FOOD_DB_V2 = load_food_database()
    if not GLOBAL_FOOD_DB_V2:
        log.warning("[state] Food DB loaded but is empty!")
    else:
        log.info("[state] Food DB loaded OK: %d items", len(GLOBAL_FOOD_DB_V2))
except Exception as exc:
    log.error("[state] Failed to load food DB: %s", exc, exc_info=True)
    GLOBAL_FOOD_DB_V2 = []
    
# MongoDB (gracefully disabled if unavailable)
mongo_store = MongoStore.from_env()

# In-memory stores
users:                 dict[str, UserProfile]                  = {}
daily_logs:            dict[str, dict[str, DailyNutritionLog]] = {}  # user_id -> date_str -> log
knowledge_bases:       dict[str, KnowledgeBase]                = {}
nutrition_analyzers:   dict[str, NutritionAnalyzer]            = {}
meal_recommenders:     dict[str, MealRecommendationEngine]     = {}
bot_sessions:          dict[str, HealthChatbot]                = {}
schedule_history:      dict[str, list]                         = {}  # user_id -> saved schedules
productivity_sessions: dict[str, list]                         = {}  # user_id -> saved predictions
activity_logs:         dict[str, list]                         = {}  # user_id -> ActivityLog dicts
sleep_logs:            dict[str, list]                         = {}  # user_id -> sleep log dicts
sleep_predictors:      dict[str, SleepQualityPredictor]        = {}  # user_id -> SleepQualityPredictor
recovery_predictors:   dict[str, RecoveryPredictor]            = {}  # user_id -> RecoveryPredictor
