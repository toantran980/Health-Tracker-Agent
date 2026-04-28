"""external.py — External API proxy endpoints (food, exercise)."""

from flask import Blueprint, request, jsonify

from api.blueprints.helpers import error_response
from api.external_apis import (
    get_food_by_barcode,
    search_exercise,
    search_exercisedb,
    proxy_wger_endpoint,
    search_all_sources,
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