"""Open Food Facts and USDA wrappers, plus FoodItem converters."""

import uuid

import requests

from api.external_api_common import (
    FOOD_FACTS_BASE,
    REQUEST_TIMEOUT,
    TTL_LONG,
    TTL_MEDIUM,
    TTL_SHORT,
    USDA_API_KEY,
    USDA_BASE,
    cache_get,
    cache_set,
    logger,
    record_external_call,
)
from models.meal import FoodItem, NutritionInfo


def parse_food_facts_product(p: dict) -> dict:
    nutrients = p.get("nutriments", {})
    return {
        "name": p.get("product_name", "Unknown"),
        "brand": p.get("brands", ""),
        "calories_per_100g": nutrients.get("energy-kcal_100g", 0),
        "protein_g": nutrients.get("proteins_100g", 0),
        "carbs_g": nutrients.get("carbohydrates_100g", 0),
        "fat_g": nutrients.get("fat_100g", 0),
        "fiber_g": nutrients.get("fiber_100g", 0),
        "serving_size": p.get("serving_size", "100g"),
        "image_url": p.get("image_small_url", ""),
    }


def search_food_by_name(query: str, page_size: int = 5) -> list[dict]:
    cache_key = f"off:search:{query.strip().lower()}:{page_size}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{FOOD_FACTS_BASE}/cgi/search.pl"
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": page_size,
    }

    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        products = resp.json().get("products", [])
        results = [
            parse_food_facts_product(p)
            for p in products
            if p.get("product_name") and p.get("nutriments", {}).get("energy-kcal_100g", 0) > 0
        ]
        record_external_call("openfoodfacts", True)
        return cache_set(cache_key, results, TTL_SHORT)
    except requests.exceptions.Timeout as exc:
        logger.warning("[OpenFoodFacts] Timeout for query: %s", query)
        record_external_call("openfoodfacts", False, f"Timeout: {exc}")
        return []
    except requests.exceptions.RequestException as exc:
        logger.warning("[OpenFoodFacts] API error: %s", exc)
        record_external_call("openfoodfacts", False, str(exc))
        return []


def get_food_by_barcode(barcode: str) -> dict | None:
    cache_key = f"off:barcode:{barcode.strip()}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{FOOD_FACTS_BASE}/api/v2/product/{barcode}.json"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != 1:
            return None
        record_external_call("openfoodfacts", True)
        return cache_set(cache_key, parse_food_facts_product(data["product"]), TTL_LONG)
    except requests.exceptions.RequestException as exc:
        logger.warning("[OpenFoodFacts] Barcode lookup error: %s", exc)
        record_external_call("openfoodfacts", False, str(exc))
        return None


def search_usda_food(query: str, page_size: int = 5) -> list[dict]:
    cache_key = f"usda:search:{query.strip().lower()}:{page_size}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{USDA_BASE}/foods/search"
    params = {"query": query, "pageSize": page_size, "api_key": USDA_API_KEY}
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        results = resp.json().get("foods", [])
        record_external_call("usda", True)
        return cache_set(cache_key, results, TTL_MEDIUM)
    except requests.exceptions.RequestException as exc:
        logger.warning("[USDA] API error: %s", exc)
        record_external_call("usda", False, str(exc))
        return []


def food_facts_to_fooditem(api_dict: dict) -> FoodItem:
    return FoodItem(
        food_id=f"off_{uuid.uuid4().hex[:8]}",
        name=api_dict.get("name", "Unknown"),
        nutrition_info=NutritionInfo(
            calories=api_dict.get("calories_per_100g", 0),
            protein_g=api_dict.get("protein_g", 0),
            carbs_g=api_dict.get("carbs_g", 0),
            fat_g=api_dict.get("fat_g", 0),
            fiber_g=api_dict.get("fiber_g", 0),
        ),
        category="external",
        tags=["api_imported", "open_food_facts"],
    )


def usda_to_fooditem(usda_dict: dict) -> FoodItem:
    nutrients = {
        n["nutrientName"]: n["value"]
        for n in usda_dict.get("foodNutrients", [])
        if "nutrientName" in n and "value" in n
    }
    return FoodItem(
        food_id=f"usda_{usda_dict.get('fdcId', uuid.uuid4().hex[:8])}",
        name=usda_dict.get("description", "Unknown"),
        nutrition_info=NutritionInfo(
            calories=nutrients.get("Energy", 0),
            protein_g=nutrients.get("Protein", 0),
            carbs_g=nutrients.get("Carbohydrate, by difference", 0),
            fat_g=nutrients.get("Total lipid (fat)", 0),
            fiber_g=nutrients.get("Fiber, total dietary", 0),
        ),
        category="external",
        tags=["usda_imported"],
    )


def search_all_sources(query: str, page_size: int = 5) -> list[FoodItem]:
    results: list[FoodItem] = []
    seen_names: set[str] = set()

    for item in search_usda_food(query, page_size):
        food = usda_to_fooditem(item)
        key = food.name.lower().strip()
        if key not in seen_names and food.nutrition_info.calories > 0:
            results.append(food)
            seen_names.add(key)

    for item in search_food_by_name(query, page_size):
        food = food_facts_to_fooditem(item)
        key = food.name.lower().strip()
        if key not in seen_names and food.nutrition_info.calories > 0:
            results.append(food)
            seen_names.add(key)

    return results[:page_size]
