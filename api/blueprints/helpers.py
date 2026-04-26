"""
helpers.py

Shared helper functions used across blueprint modules:
  - Serialisation / deserialisation
  - User lookup and AI module initialisation
  - Daily log management
  - Schedule task normalisation
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

from flask import jsonify

from models.user_profile import UserProfile, Goal, BiologicalSex
from models.meal import NutritionInfo, Meal, MealType, FoodItem, DailyNutritionLog
from ai_modules import KnowledgeBase, NutritionAnalyzer, MealRecommendationEngine

from api.blueprints import state


def error_response(message: str, code: str, status: int = 400, details: dict[str, Any] | None = None):
    """Create a consistent API error envelope."""
    payload: dict[str, Any] = {
        "error": message,
        "code": code,
    }
    if details:
        payload["details"] = details
    return jsonify(payload), status


# ── Serialisation ──────────────────────────────────────────────────────────

def serialize_food_item(food: FoodItem) -> dict[str, Any]:
    return {
        "food_id":       food.food_id,
        "name":          food.name,
        "serving_size":  food.serving_size,
        "category":      food.category,
        "tags":          food.tags,
        "is_vegan":      food.is_vegan,
        "is_gluten_free": food.is_gluten_free,
        "is_vegetarian": food.is_vegetarian,
        "nutrition_info": {
            "calories":   food.nutrition_info.calories,
            "protein_g":  food.nutrition_info.protein_g,
            "carbs_g":    food.nutrition_info.carbs_g,
            "fat_g":      food.nutrition_info.fat_g,
            "fiber_g":    food.nutrition_info.fiber_g,
            "sodium_mg":  food.nutrition_info.sodium_mg,
            "sugar_g":    food.nutrition_info.sugar_g,
        },
    }


def deserialize_food_item(doc: dict[str, Any]) -> FoodItem:
    info = doc.get("nutrition_info", {})
    return FoodItem(
        food_id=doc.get("food_id", f"food_{uuid.uuid4().hex[:8]}"),
        name=doc.get("name", "Unknown food"),
        serving_size=doc.get("serving_size", "100g"),
        category=doc.get("category", "other"),
        tags=doc.get("tags", []),
        is_vegan=doc.get("is_vegan", False),
        is_gluten_free=doc.get("is_gluten_free", False),
        is_vegetarian=doc.get("is_vegetarian", False),
        nutrition_info=NutritionInfo(
            calories=info.get("calories", 0),
            protein_g=info.get("protein_g", 0),
            carbs_g=info.get("carbs_g", 0),
            fat_g=info.get("fat_g", 0),
            fiber_g=info.get("fiber_g", 0),
            sodium_mg=info.get("sodium_mg", 0),
            sugar_g=info.get("sugar_g", 0),
        ),
    )


def serialize_meal(meal: Meal) -> dict[str, Any]:
    return {
        "meal_id":    meal.meal_id,
        "meal_type":  meal.meal_type.value,
        "timestamp":  meal.timestamp.isoformat(),
        "notes":      meal.notes,
        "food_items": [serialize_food_item(f) for f in meal.food_items],
    }


def deserialize_meal(user_id: str, doc: dict[str, Any]) -> Meal:
    timestamp = doc.get("timestamp") or datetime.now().isoformat()
    return Meal(
        meal_id=doc.get("meal_id", f"meal_{uuid.uuid4().hex[:8]}"),
        user_id=user_id,
        meal_type=MealType(doc.get("meal_type", "lunch")),
        timestamp=datetime.fromisoformat(timestamp),
        notes=doc.get("notes", ""),
        food_items=[deserialize_food_item(f) for f in doc.get("food_items", [])],
    )


def serialize_daily_log(log: DailyNutritionLog) -> dict[str, Any]:
    return {
        "log_id":   log.log_id,
        "date_iso": log.date.isoformat(),
        "meals":    [serialize_meal(m) for m in log.meals],
    }


def deserialize_daily_log(user_id: str, doc: dict[str, Any]) -> DailyNutritionLog:
    date_iso = doc.get("date_iso") or datetime.now().isoformat()
    return DailyNutritionLog(
        log_id=doc.get("log_id", f"log_{user_id}_{doc.get('date', datetime.now().date().isoformat())}"),
        user_id=user_id,
        date=datetime.fromisoformat(date_iso),
        meals=[deserialize_meal(user_id, m) for m in doc.get("meals", [])],
    )


def user_from_doc(doc: dict[str, Any]) -> UserProfile:
    goals_raw = doc.get("goals", ["general_wellness"])
    safe_goals = []
    for goal in goals_raw:
        try:
            safe_goals.append(Goal(goal))
        except ValueError:
            safe_goals.append(Goal.GENERAL_WELLNESS)

    sex_raw = str(doc.get("biological_sex", "male")).lower()
    bio_sex = BiologicalSex.FEMALE if sex_raw == "female" else BiologicalSex.MALE

    return UserProfile(
        user_id=doc["user_id"],
        name=doc.get("name", "Unknown"),
        age=doc.get("age", 25),
        weight_kg=doc.get("weight_kg", 70),
        height_cm=doc.get("height_cm", 175),
        biological_sex=bio_sex,
        goals=safe_goals,
        target_calories=doc.get("target_calories", 2000),
        target_protein_g=doc.get("target_protein_g", 150.0),
        target_carbs_g=doc.get("target_carbs_g", 200.0),
        target_fat_g=doc.get("target_fat_g", 65.0),
        dietary_restrictions=doc.get("dietary_restrictions", []),
        allergies=doc.get("allergies", []),
    )


# ── AI module management ───────────────────────────────────────────────────

def ensure_ai_modules(user_id: str, user: UserProfile) -> None:
    if (user_id in state.knowledge_bases
            and user_id in state.nutrition_analyzers
            and user_id in state.meal_recommenders):
        return

    target_nutrition = NutritionInfo(
        calories=user.target_calories,
        protein_g=user.target_protein_g,
        carbs_g=user.target_carbs_g,
        fat_g=user.target_fat_g,
    )
    state.knowledge_bases[user_id]    = KnowledgeBase(user)
    state.nutrition_analyzers[user_id] = NutritionAnalyzer(target_nutrition)
    state.meal_recommenders[user_id]   = MealRecommendationEngine(user, state.GLOBAL_FOOD_DB_V2)


def hydrate_logs_for_user(user_id: str) -> None:
    if user_id in state.daily_logs or not state.mongo_store.enabled:
        return

    docs = state.mongo_store.get_daily_logs(user_id)
    if not docs:
        return

    user_logs: dict[str, DailyNutritionLog] = {}
    for doc in docs:
        date_str = doc.get("date") or datetime.now().date().isoformat()
        user_logs[date_str] = deserialize_daily_log(user_id, doc)

    state.daily_logs[user_id] = user_logs
    analyzer = state.nutrition_analyzers.get(user_id)
    if analyzer:
        analyzer.history = [user_logs[k] for k in sorted(user_logs)]


# ── Request helpers ────────────────────────────────────────────────────────

def require_user(user_id: str):
    """Return (user, None) or (None, error_response)."""
    user = state.users.get(user_id)
    if not user and state.mongo_store.enabled:
        doc = state.mongo_store.get_user(user_id)
        if doc:
            user = user_from_doc(doc)
            state.users[user_id] = user

    if not user:
        return None, error_response("User not found", "USER_NOT_FOUND", 404)

    ensure_ai_modules(user_id, user)
    hydrate_logs_for_user(user_id)
    return user, None


def get_or_create_daily_log(user_id: str, date_str: str) -> DailyNutritionLog:
    hydrate_logs_for_user(user_id)
    user_logs = state.daily_logs.setdefault(user_id, {})
    if date_str not in user_logs:
        user_logs[date_str] = DailyNutritionLog(
            log_id=f"log_{user_id}_{date_str}",
            user_id=user_id,
            date=datetime.fromisoformat(date_str),
        )
    return user_logs[date_str]


def sync_analyzer_daily_log(user_id: str, date_str: str, daily_log: DailyNutritionLog) -> None:
    analyzer = state.nutrition_analyzers.get(user_id)
    if not analyzer:
        return
    existing = next(
        (i for i, log in enumerate(analyzer.history)
         if log.date.date().isoformat() == date_str),
        None,
    )
    if existing is not None:
        analyzer.history[existing] = daily_log
    else:
        analyzer.add_daily_log(daily_log)


def attach_meal_to_user_log(user_id: str, meal: Meal) -> DailyNutritionLog:
    date_str = meal.timestamp.date().isoformat()
    daily_log = get_or_create_daily_log(user_id, date_str)
    daily_log.meals.append(meal)
    sync_analyzer_daily_log(user_id, date_str, daily_log)
    state.mongo_store.save_daily_log(user_id, date_str, serialize_daily_log(daily_log))
    return daily_log


# ── Schedule helpers ───────────────────────────────────────────────────────

def normalize_schedule_tasks(raw_tasks):
    """Map frontend schedule task payloads to ScheduleOptimizer's expected shape."""
    normalized = []
    for task in raw_tasks or []:
        name         = task.get('name') or task.get('title') or 'Untitled Task'
        duration_min = task.get('duration_min', task.get('duration_minutes', 60))
        difficulty   = task.get('difficulty', 5)
        deadline     = task.get('deadline')
        deadline_days = task.get('deadline_days')

        if deadline:
            try:
                deadline_dt = datetime.fromisoformat(deadline)
            except ValueError:
                deadline_dt = datetime.now() + timedelta(days=7)
        elif deadline_days is not None:
            try:
                deadline_dt = datetime.now() + timedelta(days=int(deadline_days))
            except (TypeError, ValueError):
                deadline_dt = datetime.now() + timedelta(days=7)
        else:
            deadline_dt = datetime.now() + timedelta(days=7)

        try:
            duration_min = int(duration_min)
        except (TypeError, ValueError):
            duration_min = 60

        try:
            difficulty = float(difficulty)
        except (TypeError, ValueError):
            difficulty = 5.0

        normalized.append({
            'name':         str(name),
            'duration_min': max(duration_min, 1),
            'difficulty':   difficulty,
            'deadline':     deadline_dt,
        })

    return normalized
