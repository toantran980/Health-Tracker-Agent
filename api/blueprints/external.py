"""external.py — External API proxy endpoints (food, exercise, weather)."""

from datetime import datetime

from flask import Blueprint, request, jsonify

from models.meal import Meal, MealType
from api.blueprints.helpers import require_user, attach_meal_to_user_log, error_response
from api.external_apis import (
    get_food_by_barcode,
    log_natural_language_meal,
    search_exercise,
    search_exercisedb,
    proxy_wger_endpoint,
    get_weather_context,
    search_all_sources,
    nutritionix_to_fooditem,
)

external_bp = Blueprint('external', __name__)


@external_bp.route('/api/food/search', methods=['GET'])
def food_search():
    """
    Search all food sources (USDA + Open Food Facts) and return FoodItems.

    Query params:
        q     : search term (required)
        limit : max results (default 5)
    """
    query = request.args.get("q", "").strip()
    if not query:
        return error_response("q parameter is required", "MISSING_QUERY", 400)

    limit   = request.args.get("limit", 5, type=int)
    results = search_all_sources(query, page_size=limit)

    return jsonify({
        "results": [
            {
                "food_id":   f.food_id,
                "name":      f.name,
                "calories":  f.nutrition_info.calories,
                "protein_g": f.nutrition_info.protein_g,
                "carbs_g":   f.nutrition_info.carbs_g,
                "fat_g":     f.nutrition_info.fat_g,
                "tags":      f.tags,
            }
            for f in results
        ],
        "count": len(results),
    }), 200


@external_bp.route('/api/food/barcode/<barcode>', methods=['GET'])
def food_by_barcode(barcode):
    """Look up a food product by EAN-13 / UPC barcode."""
    result = get_food_by_barcode(barcode)
    if not result:
        return error_response("Product not found", "PRODUCT_NOT_FOUND", 404)
    return jsonify(result), 200


@external_bp.route('/api/food/log-text/<user_id>', methods=['POST'])
def food_log_text(user_id):
    """
    Parse a plain-text meal description via Nutritionix NLP and log it.

    Body: { "text": "2 eggs and a banana", "meal_type": "breakfast" }
    Requires NUTRITIONIX_APP_ID and NUTRITIONIX_APP_KEY in .env.
    """
    user, err = require_user(user_id)
    if err:
        return err

    data = request.json or {}
    text = data.get("text", "").strip()
    if not text:
        return error_response("text is required", "MISSING_TEXT", 400)

    parsed = log_natural_language_meal(text)
    if not parsed:
        return error_response(
            "Could not parse meal. Check Nutritionix keys in .env or try rephrasing.",
            "MEAL_PARSE_FAILED",
            503,
        )

    food_items = [nutritionix_to_fooditem(f) for f in parsed]
    meal = Meal(
        meal_id=f"nlp_{datetime.now().timestamp()}",
        user_id=user_id,
        meal_type=MealType(data.get('meal_type', 'snack')),
        timestamp=datetime.now(),
        food_items=food_items,
        notes=f"NLP parsed: {text}",
    )

    attach_meal_to_user_log(user_id, meal)

    total = meal.get_total_nutrition()
    return jsonify({
        "status":    "success",
        "meal_id":   meal.meal_id,
        "foods":     parsed,
        "nutrition": {
            "calories":  total.calories,
            "protein_g": total.protein_g,
            "carbs_g":   total.carbs_g,
            "fat_g":     total.fat_g,
        },
    }), 201


@external_bp.route('/api/exercise/search', methods=['GET'])
def exercise_search():
    """Search the Wger exercise database by name."""
    query = request.args.get("q", "").strip()
    if not query:
        return error_response("q parameter is required", "MISSING_QUERY", 400)

    results = search_exercise(query)
    return jsonify({"results": results, "count": len(results)}), 200


@external_bp.route('/api/wger/<endpoint>', methods=['GET'])
def wger_proxy_route(endpoint):
    """
    Generic proxy for any WGER API v2 endpoint.
    Examples: /api/wger/muscle, /api/wger/equipment, /api/wger/routine
    """
    params = request.args.to_dict()
    result = proxy_wger_endpoint(endpoint, params)
    if isinstance(result, dict) and len(result) == 1 and "error" in result:
        return error_response(str(result.get("error", "Wger proxy error")), "WGER_PROXY_ERROR", 400)
    return jsonify(result), 200


@external_bp.route('/api/exercisedb/search', methods=['GET'])
def get_exercisedb_search():
    """Search the ExerciseDB database (RapidAPI) by name."""
    query = request.args.get("q", "").strip()
    if not query:
        return error_response("q parameter is required", "MISSING_QUERY", 400)

    results = search_exercisedb(query)
    return jsonify({"results": results, "count": len(results)}), 200


@external_bp.route('/api/weather/context', methods=['GET'])
def weather_context():
    """
    Return weather-based wellness hints via Open-Meteo.

    Query params: lat, lon
    Example: /api/weather/context?lat=3.139&lon=101.686
    """
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    if lat is None or lon is None:
        return error_response("lat and lon are required", "MISSING_COORDINATES", 400)

    return jsonify(get_weather_context(lat, lon)), 200
