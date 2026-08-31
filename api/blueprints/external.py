"""external.py — External API proxy endpoints (food, exercise)."""

import time

from flask import Blueprint, request, jsonify

from api.blueprints.helpers import error_response
from api.rate_limiter import default_limiter
from api.external_apis import (
    get_food_by_barcode,
    search_exercise,
    search_exercisedb,
    proxy_wger_endpoint,
    search_all_sources,
)

external_bp = Blueprint('external', __name__)


def rate_limit_headers(client_id: str) -> dict:
    """Expose the active client's limit/remaining/reset as Flask headers."""
    s = default_limiter.status(client_id)
    return {
        "X-RateLimit-Limit": str(s["limit"]),
        "X-RateLimit-Remaining": str(s["remaining"]),
        "X-RateLimit-Reset": str(int(time.time() + s["reset"])),
    }


@external_bp.after_request
def attach_rate_limit_headers(response):
    """Stamp rate-limit headers on every external endpoint response."""
    client_id = request.remote_addr or "unknown"
    for k, v in rate_limit_headers(client_id).items():
        response.headers[k] = v
    return response


def check_rate_limit() -> tuple | None:
    """Record a hit; return a 429 error_response if the client exceeded the limit."""
    client_id = request.remote_addr or "unknown"
    if not default_limiter.allow(client_id):
        return error_response(
            "Rate limit exceeded. Please retry shortly.",
            "RATE_LIMITED",
            429,
        )
    return None


@external_bp.route('/api/food/search', methods=['GET'])
def food_search():
    """
    Search all food sources (USDA + Open Food Facts) and return FoodItems.

    Query params:
        q     : search term (required)
        limit : max results (default 5)
    """
    limited = check_rate_limit()
    if limited:
        return limited

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
    limited = check_rate_limit()
    if limited:
        return limited

    result = get_food_by_barcode(barcode)
    if not result:
        return error_response("Product not found", "PRODUCT_NOT_FOUND", 404)
    return jsonify(result), 200


@external_bp.route('/api/exercise/search', methods=['GET'])
def exercise_search():
    """Search the Wger exercise database by name."""
    limited = check_rate_limit()
    if limited:
        return limited

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
    limited = check_rate_limit()
    if limited:
        return limited

    params = request.args.to_dict()
    result = proxy_wger_endpoint(endpoint, params)
    if isinstance(result, dict) and len(result) == 1 and "error" in result:
        return error_response(str(result.get("error", "Wger proxy error")), "WGER_PROXY_ERROR", 400)
    return jsonify(result), 200


@external_bp.route('/api/exercisedb/search', methods=['GET'])
def get_exercisedb_search():
    """Search the ExerciseDB database (RapidAPI) by name."""
    limited = check_rate_limit()
    if limited:
        return limited

    query = request.args.get("q", "").strip()
    if not query:
        return error_response("q parameter is required", "MISSING_QUERY", 400)

    results = search_exercisedb(query)
    return jsonify({"results": results, "count": len(results)}), 200