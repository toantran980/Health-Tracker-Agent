"""
state.py

Shared in-memory stores and singletons used across all blueprint modules.
All dicts are module-level so mutations are visible everywhere.
"""

from typing import Dict

from models.user_profile import UserProfile
from models.meal import DailyNutritionLog
from ai_modules import KnowledgeBase, NutritionAnalyzer, MealRecommendationEngine
from ai_modules.health_chatbot import HealthChatbot
from api.mongo_store import MongoStore
from data.dataset_loader_v2 import load_food_database

import logging

# Load food DB once at startup
_log = logging.getLogger(__name__)

try:
    GLOBAL_FOOD_DB_V2 = load_food_database()
    if not GLOBAL_FOOD_DB_V2:
        _log.warning("[state] Food DB loaded but is empty!")
    else:
        _log.info("[state] Food DB loaded OK: %d items", len(GLOBAL_FOOD_DB_V2))
except Exception as exc:
    _log.error("[state] Failed to load food DB: %s", exc, exc_info=True)
    GLOBAL_FOOD_DB_V2 = []
    
# MongoDB (gracefully disabled if unavailable)
mongo_store = MongoStore.from_env()

# In-memory stores
users:               Dict[str, UserProfile]                  = {}
daily_logs:          Dict[str, Dict[str, DailyNutritionLog]] = {}  # user_id -> date_str -> log
knowledge_bases:     Dict[str, KnowledgeBase]                = {}
nutrition_analyzers: Dict[str, NutritionAnalyzer]            = {}
meal_recommenders:   Dict[str, MealRecommendationEngine]     = {}
bot_sessions:        Dict[str, HealthChatbot]                = {}
