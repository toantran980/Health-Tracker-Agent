"""External API wrappers with safe fallbacks and lightweight TTL caching."""

import os
import logging
import time
import uuid
import requests
from dotenv import load_dotenv

from models.meal import FoodItem, NutritionInfo

load_dotenv()
logger = logging.getLogger(__name__)

# Configuration

REQUEST_TIMEOUT = 10   # seconds — applies to every API call

TTL_SHORT = 300    # 5 min
TTL_MEDIUM = 900   # 15 min
TTL_LONG = 3600    # 60 min

_TTL_CACHE: dict[str, tuple[float, object]] = {}


def cache_get(key: str):
    cached = _TTL_CACHE.get(key)
    if not cached:
        return None
    expires_at, value = cached
    if expires_at <= time.time():
        _TTL_CACHE.pop(key, None)
        return None
    return value


def cache_set(key: str, value: object, ttl_seconds: int) -> object:
    _TTL_CACHE[key] = (time.time() + ttl_seconds, value)
    return value

USDA_API_KEY = os.getenv("USDA_API_KEY", "DEMO_KEY")

FOOD_FACTS_BASE = "https://world.openfoodfacts.org"
WGER_BASE       = "https://wger.de/api/v2"
OPEN_METEO_BASE  = "https://api.open-meteo.com/v1"
USDA_BASE        = "https://api.nal.usda.gov/fdc/v1"
EXERCISEDB_HOST  = "exercisedb.p.rapidapi.com"
RAPIDAPI_KEY     = os.getenv("EXERCISEDB_API_KEY", "")


# Open Food Facts

def search_food_by_name(query: str, page_size: int = 5) -> list[dict]:
    """Search foods by name via Open Food Facts."""
    cache_key = f"off:search:{query.strip().lower()}:{page_size}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url    = f"{FOOD_FACTS_BASE}/cgi/search.pl"
    params = {
        "search_terms":  query,
        "search_simple": 1,
        "action":        "process",
        "json":          1,
        "page_size":     page_size,
    }

    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        products = resp.json().get("products", [])
        results = [
            parse_food_facts_product(p)
            for p in products
            if p.get("product_name")
            and p.get("nutriments", {}).get("energy-kcal_100g", 0) > 0
        ]
        return cache_set(cache_key, results, TTL_SHORT)

    except requests.exceptions.Timeout:
        logger.warning("[OpenFoodFacts] Timeout for query: %s", query)
        return []
    except requests.exceptions.RequestException as e:
        logger.warning("[OpenFoodFacts] API error: %s", e)
        return []


def get_food_by_barcode(barcode: str) -> dict | None:
    """Look up a single product by EAN-13 / UPC barcode."""
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
        result = parse_food_facts_product(data["product"])
        return cache_set(cache_key, result, TTL_LONG)

    except requests.exceptions.RequestException as e:
        logger.warning("[OpenFoodFacts] Barcode lookup error: %s", e)
        return None


def parse_food_facts_product(p: dict) -> dict:
    """Normalize a raw Open Food Facts product dict into a flat nutrition dict."""
    nutrients = p.get("nutriments", {})
    return {
        "name":              p.get("product_name", "Unknown"),
        "brand":             p.get("brands", ""),
        "calories_per_100g": nutrients.get("energy-kcal_100g", 0),
        "protein_g":         nutrients.get("proteins_100g",       0),
        "carbs_g":           nutrients.get("carbohydrates_100g",  0),
        "fat_g":             nutrients.get("fat_100g",            0),
        "fiber_g":           nutrients.get("fiber_100g",          0),
        "serving_size":      p.get("serving_size", "100g"),
        "image_url":         p.get("image_small_url", ""),
    }


# USDA FoodData Central

def search_usda_food(query: str, page_size: int = 5) -> list[dict]:
    """Search USDA FoodData Central for food items."""
    cache_key = f"usda:search:{query.strip().lower()}:{page_size}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url    = f"{USDA_BASE}/foods/search"
    params = {
        "query":    query,
        "pageSize": page_size,
        "api_key":  USDA_API_KEY,
    }

    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        results = resp.json().get("foods", [])
        return cache_set(cache_key, results, TTL_MEDIUM)

    except requests.exceptions.RequestException as e:
        logger.warning("[USDA] API error: %s", e)
        return []


# Wger exercise APIs

def search_exercise(name: str, language: int = 2) -> list[dict]:
    """Search the Wger exercise database by name."""
    cache_key = f"wger:search:{name.strip().lower()}:{language}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url    = f"{WGER_BASE}/exercise/search/"
    params = {"term": name, "language": language, "format": "json"}

    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        results = [
            {
                "name":        s["value"],
                "exercise_id": s["data"]["id"],
                "category":    s["data"].get("category", {}).get("name", ""),
            }
            for s in resp.json().get("suggestions", [])
        ]
        return cache_set(cache_key, results, TTL_MEDIUM)

    except requests.exceptions.RequestException as e:
        logger.warning("[Wger] Search error: %s", e)
        return []


def proxy_wger_endpoint(endpoint: str, params: dict = None) -> dict:
    """
    Generic proxy to fetch data from any Wger API v2 endpoint.
    Provides access to routines, equipment, muscles, etc.
    """
    # Avoid double slashes in the composed endpoint URL.
    endpoint = endpoint.strip("/")
    url = f"{WGER_BASE}/{endpoint}/"
    
    try:
        resp = requests.get(url, params=params or {}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        logger.warning("[Wger] Proxy error for %s: %s", endpoint, e)
        return {"error": str(e)}


# ExerciseDB (RapidAPI)

def search_exercisedb(name: str) -> list[dict]:
    """Search exercises via ExerciseDB (RapidAPI)."""
    cache_key = f"exercisedb:search:{name.strip().lower()}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"https://{EXERCISEDB_HOST}/exercises/name/{name}"
    headers = {
        "x-rapidapi-host": EXERCISEDB_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        
        results = [
            {
                "exercise_id": str(item.get("id", "")),
                "name":        item.get("name", "").title(),
                "body_part":   item.get("bodyPart", ""),
                "equipment":   item.get("equipment", ""),
                "target":      item.get("target", ""),
                "gif_url":     item.get("gifUrl", ""),
                "instructions": item.get("instructions", []),
            }
            for item in data[:10]
        ]
        return cache_set(cache_key, results, TTL_MEDIUM)

    except requests.exceptions.RequestException as e:
        logger.warning("[ExerciseDB] API error: %s", e)
        return []



# Open-Meteo weather

def get_weather_context(latitude: float, longitude: float) -> dict:
    """Fetch current weather and UV context with safe defaults on failure."""
    _default = {
        "temperature_c":      20.0,
        "precipitation_mm":   0.0,
        "uv_index":           0.0,
        "wind_speed_kmh":     0.0,
        "is_raining":         False,
        "high_uv":            False,
        "recommendation_hints": [],
    }

    cache_key = f"weather:context:{round(latitude, 3)}:{round(longitude, 3)}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url    = f"{OPEN_METEO_BASE}/forecast"
    params = {
        "latitude":  latitude,
        "longitude": longitude,
        "current":   "temperature_2m,precipitation,uv_index,wind_speed_10m,weather_code",
        "timezone":  "auto",
    }

    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        current = resp.json().get("current", {})

        weather_code = current.get("weather_code", 0)
        is_raining   = weather_code in range(51, 100)
        uv_index     = current.get("uv_index",        0)
        temp         = current.get("temperature_2m",  20)

        result = {
            "temperature_c":      temp,
            "precipitation_mm":   current.get("precipitation",    0),
            "uv_index":           uv_index,
            "wind_speed_kmh":     current.get("wind_speed_10m",   0),
            "is_raining":         is_raining,
            "high_uv":            uv_index >= 6,
            "recommendation_hints": weather_hints(is_raining, uv_index, temp),
        }
        return cache_set(cache_key, result, TTL_SHORT)

    except requests.exceptions.RequestException as e:
        logger.warning("[Weather] API error: %s", e)
        return _default


def weather_hints(is_raining: bool, uv: float, temp: float) -> list[str]:
    """Generate human-readable recommendation hints from weather data."""
    hints = []
    if is_raining:
        hints.append("Rainy today — suggest indoor workout alternatives.")
    if uv >= 6:
        hints.append(f"High UV index ({uv:.0f}) — increase water intake.")
    if temp >= 30:
        hints.append("Hot weather — recommend electrolytes in meal plan.")
    if temp <= 5:
        hints.append("Cold weather — suggest higher-calorie warming meals.")
    return hints


# FoodItem converters

def food_facts_to_fooditem(api_dict: dict) -> FoodItem:
    """Convert an Open Food Facts nutrition dict to a FoodItem."""
    return FoodItem(
        food_id=f"off_{uuid.uuid4().hex[:8]}",
        name=api_dict.get("name", "Unknown"),
        nutrition_info=NutritionInfo(
            calories=  api_dict.get("calories_per_100g", 0),
            protein_g= api_dict.get("protein_g",         0),
            carbs_g=   api_dict.get("carbs_g",           0),
            fat_g=     api_dict.get("fat_g",             0),
            fiber_g=   api_dict.get("fiber_g",           0),
        ),
        category="external",
        tags=["api_imported", "open_food_facts"],
    )


def usda_to_fooditem(usda_dict: dict) -> FoodItem:
    """Convert a USDA FoodData Central search result to a FoodItem."""
    # Build a nutrient-name to value lookup.
    nutrients = {
        n["nutrientName"]: n["value"]
        for n in usda_dict.get("foodNutrients", [])
        if "nutrientName" in n and "value" in n
    }

    return FoodItem(
        food_id=f"usda_{usda_dict.get('fdcId', uuid.uuid4().hex[:8])}",
        name=usda_dict.get("description", "Unknown"),
        nutrition_info=NutritionInfo(
            calories=  nutrients.get("Energy",                      0),
            protein_g= nutrients.get("Protein",                     0),
            carbs_g=   nutrients.get("Carbohydrate, by difference", 0),
            fat_g=     nutrients.get("Total lipid (fat)",           0),
            fiber_g=   nutrients.get("Fiber, total dietary",        0),
        ),
        category="external",
        tags=["usda_imported"],
    )


# Unified search

def search_all_sources(query: str, page_size: int = 5) -> list[FoodItem]:
    """Search USDA and Open Food Facts and return deduplicated FoodItems."""
    results:    list[FoodItem] = []
    seen_names: set[str]       = set()

    # USDA first for better whole-food nutrient quality.
    for item in search_usda_food(query, page_size):
        food = usda_to_fooditem(item)
        key  = food.name.lower().strip()
        if key not in seen_names and food.nutrition_info.calories > 0:
            results.append(food)
            seen_names.add(key)

    # Open Food Facts second for broader packaged-food coverage.
    for item in search_food_by_name(query, page_size):
        food = food_facts_to_fooditem(item)
        key  = food.name.lower().strip()
        if key not in seen_names and food.nutrition_info.calories > 0:
            results.append(food)
            seen_names.add(key)

    return results[:page_size]


# Quick manual test: python api/external_apis.py

if __name__ == "__main__":

    print("\n=== Open Food Facts — Name Search ===")
    foods = search_food_by_name("oatmeal", page_size=2)
    for f in foods:
        print(f"  {f['name']} — {f['calories_per_100g']} kcal/100g")

    print("\n=== Open Food Facts — Barcode Lookup ===")
    product = get_food_by_barcode("0737628064502")
    if product:
        print(f"  {product['name']} ({product['brand']})")
    else:
        print("  Product not found.")

    print("\n=== USDA Food Search ===")
    usda_results = search_usda_food("chicken breast", page_size=2)
    for f in usda_results:
        print(f"  {f.get('description', 'N/A')}")

    print("\n=== Unified Search (all sources) ===")
    unified = search_all_sources("brown rice", page_size=4)
    for f in unified:
        print(f"  [{f.tags[0]}] {f.name} — {f.nutrition_info.calories} kcal")

    print("\n=== Wger — Exercise Search ===")
    exercises = search_exercise("squat")
    for e in exercises[:3]:
        print(f"  {e['name']} (id: {e['exercise_id']}, category: {e['category']})")

    print("\n=== Open-Meteo — Weather Context ===")
    weather = get_weather_context(3.1390, 101.6869)
    print(f"  Temp: {weather['temperature_c']}°C | UV: {weather['uv_index']}")
    for hint in weather["recommendation_hints"]:
        print(f"  Hint: {hint}")

    print("\n=== FoodItem Converter Test ===")
    if usda_results:
        item = usda_to_fooditem(usda_results[0])
        print(f"  {item.name} | {item.nutrition_info.calories} kcal | "
              f"P:{item.nutrition_info.protein_g}g "
              f"C:{item.nutrition_info.carbs_g}g "
              f"F:{item.nutrition_info.fat_g}g")

