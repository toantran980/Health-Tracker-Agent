import uuid
from datetime import datetime
from typing import Any

from models.user_profile import UserProfile, Goal, BiologicalSex
from models.meal import NutritionInfo, Meal, MealType, FoodItem, DailyNutritionLog


def serialize_food_item(food: FoodItem) -> dict[str, Any]:
    return {
        "food_id": food.food_id,
        "name": food.name,
        "serving_size": food.serving_size,
        "category": food.category,
        "tags": food.tags,
        "is_vegan": food.is_vegan,
        "is_gluten_free": food.is_gluten_free,
        "is_vegetarian": food.is_vegetarian,
        "nutrition_info": {
            "calories": food.nutrition_info.calories,
            "protein_g": food.nutrition_info.protein_g,
            "carbs_g": food.nutrition_info.carbs_g,
            "fat_g": food.nutrition_info.fat_g,
            "fiber_g": food.nutrition_info.fiber_g,
            "sodium_mg": food.nutrition_info.sodium_mg,
            "sugar_g": food.nutrition_info.sugar_g,
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
        "meal_id": meal.meal_id,
        "meal_type": meal.meal_type.value,
        "timestamp": meal.timestamp.isoformat(),
        "notes": meal.notes,
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
        "log_id": log.log_id,
        "date_iso": log.date.isoformat(),
        "meals": [serialize_meal(m) for m in log.meals],
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
