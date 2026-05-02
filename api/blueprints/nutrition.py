from uuid import uuid4
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify

from models.meal import NutritionInfo, Meal, MealType, FoodItem
from api.blueprints import state
from api.blueprints.helpers import (
    require_user,
    attach_meal_to_user_log,
    error_response
)

nutrition_bp = Blueprint('nutrition', __name__)

def clean_report(report):
    """Recursively converts non-serializable types for JSON output."""
    if isinstance(report, dict):
        return {k: clean_report(v) for k, v in report.items()}
    elif isinstance(report, list):
        return [clean_report(i) for i in report]
    elif hasattr(report, 'item'):  # Handles numpy types
        return report.item()
    return report

@nutrition_bp.route('/api/meals/log', methods=['POST'])
def log_user_meal():
    """Logs a detailed meal, persists to Mongo, and updates AI analyzers."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    
    if not user_id:
        return error_response("user_id is required", "MISSING_USER_ID", 400)

    # 1. Process Food Items
    food_items_data = data.get('food_items', [])
    food_items = [
        FoodItem(
            food_id=item.get('food_id', str(uuid4())),
            name=item.get('name', 'Unknown'),
            nutrition_info=NutritionInfo(
                calories=item.get('calories', 0),
                protein_g=item.get('protein_g', 0),
                carbs_g=item.get('carbs_g', 0),
                fat_g=item.get('fat_g', 0)
            )
        ) for item in food_items_data
    ]

    # 2. Create Meal Object
    ts_raw = data.get('timestamp')
    ts = datetime.fromisoformat(ts_raw) if ts_raw else datetime.now(timezone.utc)
    
    meal = Meal(
        meal_id=data.get("meal_id", f"meal_{datetime.now().timestamp()}"),
        user_id=user_id,
        meal_type=MealType(data.get('meal_type', 'lunch')),
        timestamp=ts,
        food_items=food_items,
        notes=data.get('notes', ''),
    )

    # 3. Persist to MongoDB
    total = meal.get_total_nutrition()
    meal_doc = {
        "meal_id": meal.meal_id,
        "user_id": user_id,
        "food_name": ", ".join([f.name for f in food_items]) or "Mixed Meal",
        "calories": total.calories,
        "protein": total.protein_g,
        "timestamp": meal.timestamp
    }
    success = state.mongo_store.save_meal(meal_doc)

    # 4. Sync with AI Module History
    attach_meal_to_user_log(user_id, meal)

    return jsonify({
        "status": "success" if success else "partial_success",
        "meal_id": meal.meal_id,
        "nutrition": {
            "calories": total.calories,
            "protein_g": total.protein_g,
            "carbs_g": total.carbs_g,
            "fat_g": total.fat_g,
        },
    }), 201

@nutrition_bp.route('/api/nutrition/analysis/<user_id>', methods=['GET'])
def analyze_nutrition(user_id):
    """Return the full nutrition report for a user."""
    user, err = require_user(user_id)
    if err: return err

    analyzer = state.nutrition_analyzers.get(user_id)
    if not analyzer:
        # Attempt to auto-initialize if missing
        # initialize_user_ai_modules(user_id)
        analyzer = state.nutrition_analyzers.get(user_id)
        if not analyzer:
            return error_response("Analyzer not initialized", "ANALYZER_NOT_INITIALIZED", 400)

    goal = request.args.get('goal')
    report = analyzer.get_nutrition_report(goal=goal)
    return jsonify(clean_report(report)), 200

@nutrition_bp.route('/api/nutrition/meal-recommendations/<user_id>', methods=['GET'])
def get_meal_recommendations(user_id):
    """Personalized food recommendations from MealRecommendationEngine."""
    user, err = require_user(user_id)
    if err: return err

    recommender = state.meal_recommenders.get(user_id)
    if not recommender:
        return error_response("Recommender not initialized", "RECOMMENDER_NOT_INITIALIZED", 400)

    try:
        target_calories = float(request.args.get('target_calories', user.target_calories))
        target_protein = float(request.args.get('target_protein', user.target_protein_g))
    except (ValueError, TypeError):
        return error_response("Invalid numeric query parameters", "INVALID_NUMERIC_QUERY", 400)

    mode = request.args.get('mode', 'constraint')
    if mode == 'hybrid':
        results = recommender.get_hybrid_recommendations(target_calories, target_protein)
    else:
        results = recommender.get_constraint_based_recommendations(target_calories, target_protein)

    # Persist recommendation history
    state.mongo_store.save_recommendation({
        "user_id": user_id,
        "recommendations": results,
        "mode": mode
    })

    return jsonify({"recommendations": results, "mode": mode}), 200