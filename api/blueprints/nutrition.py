"""nutrition.py — Meal logging and nutrition analysis endpoints."""

from datetime import datetime

from flask import Blueprint, request, jsonify

from models.meal import NutritionInfo, Meal, MealType, FoodItem
from api.blueprints import state
from api.blueprints.helpers import (
    require_user,
    attach_meal_to_user_log,
    error_response,
)

nutrition_bp = Blueprint('nutrition', __name__)


@nutrition_bp.route('/api/nutrition/log-meal/<user_id>', methods=['POST'])
def log_meal(user_id):
    """
    Log a meal for a user and attach it to that day's DailyNutritionLog.

    Body (JSON):
        meal_type   : "breakfast" | "lunch" | "dinner" | "snack"
        timestamp   : ISO-8601 string (optional, defaults to now)
        notes       : free text (optional)
        food_items  : list of {name, calories, protein_g, carbs_g, fat_g}
    """
    user, err = require_user(user_id)
    if err:
        return err

    data = request.json or {}

    raw_items  = data.get('food_items', [])
    food_items = []
    for item in raw_items:
        food_items.append(FoodItem(
            food_id=f"manual_{datetime.now().timestamp()}",
            name=item.get('name', 'Unknown food'),
            nutrition_info=NutritionInfo(
                calories=item.get('calories',  0),
                protein_g=item.get('protein_g', 0),
                carbs_g=item.get('carbs_g',   0),
                fat_g=item.get('fat_g',     0),
            ),
        ))

    ts = datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat()))
    meal = Meal(
        meal_id=f"meal_{datetime.now().timestamp()}",
        user_id=user_id,
        meal_type=MealType(data.get('meal_type', 'lunch')),
        timestamp=ts,
        food_items=food_items,
        notes=data.get('notes', ''),
    )

    attach_meal_to_user_log(user_id, meal)

    total = meal.get_total_nutrition()
    return jsonify({
        "status":    "success",
        "meal_id":   meal.meal_id,
        "timestamp": meal.timestamp.isoformat(),
        "nutrition": {
            "calories":  total.calories,
            "protein_g": total.protein_g,
            "carbs_g":   total.carbs_g,
            "fat_g":     total.fat_g,
        },
    }), 201


@nutrition_bp.route('/api/nutrition/analysis/<user_id>', methods=['GET'])
def analyze_nutrition(user_id):
    """
    Return the full nutrition report for a user.

    Optional query params:
        goal          : e.g. "MUSCLE_GAIN"
        focus_scores  : comma-separated integers, e.g. "7,8,6,9"
    """
    user, err = require_user(user_id)
    if err:
        return err

    analyzer = state.nutrition_analyzers.get(user_id)
    if not analyzer:
        return error_response("Nutrition analyzer not initialized", "ANALYZER_NOT_INITIALIZED", 400)

    goal = request.args.get('goal')

    focus_raw = request.args.get('focus_scores', '')
    focus_scores = None
    if focus_raw:
        try:
            focus_scores = [int(s) for s in focus_raw.split(',')]
        except ValueError:
            return error_response(
                "focus_scores must be comma-separated integers",
                "INVALID_FOCUS_SCORES",
                400,
            )

    report = analyzer.get_nutrition_report(goal=goal, focus_scores=focus_scores)
    return jsonify(report), 200


@nutrition_bp.route('/api/nutrition/recommendations/<user_id>', methods=['GET'])
def get_nutrition_recommendations(user_id):
    """Return goal-aware macro recommendations."""
    user, err = require_user(user_id)
    if err:
        return err

    analyzer = state.nutrition_analyzers.get(user_id)
    if not analyzer:
        return error_response("Nutrition analyzer not initialized", "ANALYZER_NOT_INITIALIZED", 400)

    goal = request.args.get('goal')
    return jsonify(analyzer.get_macro_recommendations(goal=goal)), 200


@nutrition_bp.route('/api/nutrition/meal-recommendations/<user_id>', methods=['GET'])
def get_meal_recommendations(user_id):
    """
    Return personalised food recommendations from MealRecommendationEngine.

    Query params:
        target_calories : float (required)
        target_protein  : float (required)
        n               : int, number of results (default 5)
        mode            : "constraint" | "content" | "hybrid" (default "constraint")
    """
    user, err = require_user(user_id)
    if err:
        return err

    recommender = state.meal_recommenders.get(user_id)
    if not recommender:
        return error_response("Meal recommender not initialized", "RECOMMENDER_NOT_INITIALIZED", 400)

    try:
        target_calories = float(request.args.get('target_calories', user.target_calories))
        target_protein  = float(request.args.get('target_protein',  user.target_protein_g))
    except ValueError:
        return error_response(
            "target_calories and target_protein must be numbers",
            "INVALID_NUMERIC_QUERY",
            400,
        )

    n    = request.args.get('n', 5, type=int)
    mode = request.args.get('mode', 'constraint')

    if mode == 'content':
        results = recommender.get_content_based_recommendations(n=n)
    elif mode == 'hybrid':
        results = recommender.get_hybrid_recommendations(target_calories, target_protein, n=n)
    else:
        results = recommender.get_constraint_based_recommendations(target_calories, target_protein, n=n)

    return jsonify({"recommendations": results, "mode": mode, "count": len(results)}), 200
