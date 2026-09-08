from datetime import datetime
from uuid import uuid4

from flask import Blueprint, jsonify, request

from api.blueprints import state
from api.blueprints.helpers import (
    attach_meal_to_user_log,
    check_duplicate_submission,
    coerce_float,
    coerce_water_ml,
    error_response,
    require_auth,
    require_fields,
    require_user,
    require_user_and_auth,
    validate_iso_timestamp,
)
from models.meal import FoodItem, Meal, MealType, NutritionInfo

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

    missing = require_fields(data, ["user_id"])
    if missing:
        return missing

    _, err = require_user(user_id)
    if err:
        return err
    auth_err = require_auth(user_id)
    if auth_err:
        return auth_err

    ts, ts_err = validate_iso_timestamp(data.get('timestamp'))
    if ts_err:
        return ts_err

    # 1. Process Food Items with strict range bounds
    food_items_data = data.get('food_items', [])
    food_items = []
    for item in food_items_data:
        calories, cal_err = coerce_float(item.get('calories'), 0, minimum=0, maximum=10000)
        if cal_err:
            return cal_err
        protein, prot_err = coerce_float(item.get('protein_g'), 0, minimum=0, maximum=1000)
        if prot_err:
            return prot_err
        carbs, carbs_err = coerce_float(item.get('carbs_g'), 0, minimum=0, maximum=2000)
        if carbs_err:
            return carbs_err
        fat, fat_err = coerce_float(item.get('fat_g'), 0, minimum=0, maximum=1000)
        if fat_err:
            return fat_err
        food_items.append(FoodItem(
            food_id=item.get('food_id', str(uuid4())),
            name=item.get('name', 'Unknown'),
            nutrition_info=NutritionInfo(
                calories=calories,
                protein_g=protein,
                carbs_g=carbs,
                fat_g=fat,
            )
        ))

    # Duplicate submission prevention
    meal_id = data.get("meal_id") or f"meal_{datetime.now().timestamp()}"
    dupe_key = str(data.get("meal_id") or f"{ts.isoformat()}:{len(food_items)}")
    dupe_err = check_duplicate_submission(user_id, "meal", dupe_key)
    if dupe_err:
        return dupe_err

    meal_type_raw = str(data.get('meal_type', 'lunch')).strip()
    meal_type = MealType(meal_type_raw) if meal_type_raw in MealType._value2member_map_ else MealType.LUNCH

    meal = Meal(
        meal_id=meal_id,
        user_id=user_id,
        meal_type=meal_type,
        timestamp=ts,
        food_items=food_items,
        notes=data.get('notes', ''),
    )

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


@nutrition_bp.route('/api/water/log', methods=['POST'])
def log_water():
    """
    Log water intake with unit validation (auth required).

    Body (JSON):
        user_id   : str    (required)
        amount    : float  (required)
        unit      : str    ('ml', 'oz', 'l', optional, default 'ml')
        timestamp : str    (ISO-8601, optional)
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")

    missing = require_fields(data, ["user_id", "amount"])
    if missing:
        return missing

    _, err = require_user(user_id)
    if err:
        return err
    auth_err = require_auth(user_id)
    if auth_err:
        return auth_err

    ts, ts_err = validate_iso_timestamp(data.get('timestamp'))
    if ts_err:
        return ts_err

    amount_ml, ml_err = coerce_water_ml(data.get('amount'), unit=data.get('unit', 'ml'))
    if ml_err:
        return ml_err

    dupe_err = check_duplicate_submission(user_id, "water", f"{ts.isoformat()}:{amount_ml}")
    if dupe_err:
        return dupe_err

    date_str = ts.date().isoformat()
    from api.blueprints.helpers import get_or_create_daily_log, sync_analyzer_daily_log
    daily_log = get_or_create_daily_log(user_id, date_str)
    daily_log.water_intake_ml += amount_ml
    sync_analyzer_daily_log(user_id, date_str, daily_log)

    if state.mongo_store.enabled:
        from api.blueprints.serialization_helpers import serialize_daily_log
        state.mongo_store.save_daily_log(user_id, date_str, serialize_daily_log(daily_log))

    return jsonify({
        "status": "success",
        "user_id": user_id,
        "logged_ml": amount_ml,
        "total_water_ml": daily_log.water_intake_ml,
        "timestamp": ts.isoformat(),
    }), 201

@nutrition_bp.route('/api/nutrition/analysis/<user_id>', methods=['GET'])
def analyze_nutrition(user_id):
    """Return the full nutrition report for a user (auth required)."""
    _, err = require_user_and_auth(user_id)
    if err: return err

    analyzer = state.nutrition_analyzers.get(user_id)
    if not analyzer:
        return error_response("Analyzer not initialized", "ANALYZER_NOT_INITIALIZED", 400)

    goal = request.args.get('goal')
    report = analyzer.get_nutrition_report(goal=goal)
    return jsonify(clean_report(report)), 200

@nutrition_bp.route('/api/nutrition/recommendations/<user_id>', methods=['GET'])
def get_macro_recommendations(user_id):
    """Return goal-aware macro recommendations for a user (auth required)."""
    _, err = require_user_and_auth(user_id)
    if err: return err

    analyzer = state.nutrition_analyzers.get(user_id)
    if not analyzer:
        return error_response("Analyzer not initialized", "ANALYZER_NOT_INITIALIZED", 400)

    goal = request.args.get('goal')
    recommendations = analyzer.get_macro_recommendations(goal=goal)
    return jsonify(clean_report(recommendations)), 200

@nutrition_bp.route('/api/nutrition/meal-recommendations/<user_id>', methods=['GET'])
def get_meal_recommendations(user_id):
    """Personalized food recommendations from MealRecommendationEngine (auth required)."""
    user, err = require_user_and_auth(user_id)
    if err: return err

    recommender = state.meal_recommenders.get(user_id)
    if not recommender:
        return error_response("Recommender not initialized", "RECOMMENDER_NOT_INITIALIZED", 400)

    target_calories, cal_err = coerce_float(request.args.get('target_calories', user.target_calories), user.target_calories, minimum=1)
    if cal_err:
        return cal_err
    target_protein, prot_err = coerce_float(request.args.get('target_protein', user.target_protein_g), user.target_protein_g, minimum=1)
    if prot_err:
        return prot_err

    mode = request.args.get('mode', 'constraint')
    if mode == 'hybrid':
        results = recommender.get_hybrid_recommendations(target_calories, target_protein)
    elif mode == 'content':
        results = recommender.get_content_based_recommendations()
    else:
        results = recommender.get_constraint_based_recommendations(target_calories, target_protein)

    # Persist recommendation history
    state.mongo_store.save_recommendation({
        "user_id": user_id,
        "recommendations": results,
        "mode": mode
    })

    return jsonify({"recommendations": results, "mode": mode}), 200