"""
external_apis.py

Free external API wrappers for the Health & Wellness Tracker.

APIs Used
---------
Open Food Facts   : food search + barcode lookup (no key needed)
USDA FoodData     : high-accuracy nutrition data (free key or DEMO_KEY)
Nutritionix NLP   : natural language meal parsing (free 500 calls/day)
Wger              : exercise database (no key needed)
Open-Meteo        : weather context (no key needed)

All functions return safe defaults on failure so the app never crashes
during a demo due to network issues or missing keys.

Setup
-----
Create a .env file in the project root:

    NUTRITIONIX_APP_ID=your_id_here
    NUTRITIONIX_APP_KEY=your_key_here
    USDA_API_KEY=your_key_here        # optional — DEMO_KEY works for testing

Sign up:
    Nutritionix : https://www.nutritionix.com/food-api
    USDA        : https://fdc.nal.usda.gov/api-guide.html
"""

import os
import uuid
import requests
from dotenv import load_dotenv

from models.meal import FoodItem, NutritionInfo

load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================

REQUEST_TIMEOUT = 10   # seconds — applies to every API call


NUTRITIONIX_APP_ID  = os.getenv("NUTRITIONIX_APP_ID",  "")
NUTRITIONIX_APP_KEY = os.getenv("NUTRITIONIX_APP_KEY", "")
USDA_API_KEY        = os.getenv("USDA_API_KEY",        "DEMO_KEY")

FOOD_FACTS_BASE  = "https://world.openfoodfacts.org"
NUTRITIONIX_BASE = "https://trackapi.nutritionix.com/v2"
WGER_BASE        = "https://wger.de/api/v2"
OPEN_METEO_BASE  = "https://api.open-meteo.com/v1"
USDA_BASE        = "https://api.nal.usda.gov/fdc/v1"
EXERCISEDB_HOST  = "exercisedb.p.rapidapi.com"
RAPIDAPI_KEY     = os.getenv("EXERCISEDB_API_KEY", "")


# ============================================================
# 1. OPEN FOOD FACTS
#    No API key needed. 3M+ products worldwide.
#    Docs: https://world.openfoodfacts.org/data
# ============================================================

def search_food_by_name(query: str, page_size: int = 5) -> list[dict]:
    """
    Search foods by name via Open Food Facts.

    Filters out products with missing calorie data to prevent
    zero-nutrition entries from corrupting recommendation scoring.

    Returns:
        List of parsed nutrition dicts, or [] on failure.
    """
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
        return [
            parse_food_facts_product(p)
            for p in products
            if p.get("product_name")
            and p.get("nutriments", {}).get("energy-kcal_100g", 0) > 0
        ]

    except requests.exceptions.Timeout:
        print(f"[OpenFoodFacts] Timeout for query: {query}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[OpenFoodFacts] API error: {e}")
        return []


def get_food_by_barcode(barcode: str) -> dict | None:
    """
    Look up a single product by EAN-13 / UPC barcode.

    Returns:
        Parsed nutrition dict, or None if not found.
    """
    url = f"{FOOD_FACTS_BASE}/api/v2/product/{barcode}.json"

    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != 1:
            return None
        return parse_food_facts_product(data["product"])

    except requests.exceptions.RequestException as e:
        print(f"[OpenFoodFacts] Barcode lookup error: {e}")
        return None


def parse_food_facts_product(p: dict) -> dict:
    """
    Normalise a raw Open Food Facts product dict into a flat nutrition dict.
    Public (no leading underscore) so converters can call it directly.
    """
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


# ============================================================
# 2. USDA FOODDATA CENTRAL
#    Free — use DEMO_KEY for testing or register for higher limits.
#    Register: https://fdc.nal.usda.gov/api-guide.html
#    DEMO_KEY limit: 30 requests/hour, 50/day.
# ============================================================

def search_usda_food(query: str, page_size: int = 5) -> list[dict]:
    """
    Search USDA FoodData Central — highest accuracy for whole foods.

    Preferred over Open Food Facts for items like "chicken breast"
    or "brown rice" where USDA verified data is more reliable.

    Returns:
        List of raw USDA food dicts, or [] on failure.
    """
    url    = f"{USDA_BASE}/foods/search"
    params = {
        "query":    query,
        "pageSize": page_size,
        "api_key":  USDA_API_KEY,
    }

    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("foods", [])

    except requests.exceptions.RequestException as e:
        print(f"[USDA] API error: {e}")
        return []


# ============================================================
# 3. NUTRITIONIX NLP
#    Free tier: 500 calls/day.
#    Register: https://www.nutritionix.com/food-api
# ============================================================

def log_natural_language_meal(text: str) -> list[dict]:
    """
    Parse a plain-English meal description into structured nutrition data.

    Example:
        log_natural_language_meal("2 scrambled eggs and a cup of oatmeal")

    Returns:
        List of per-food nutrition dicts, or [] if keys are missing / call fails.
    """
    if not NUTRITIONIX_APP_ID or not NUTRITIONIX_APP_KEY:
        print(
            "[Nutritionix] Skipping — NUTRITIONIX_APP_ID / NUTRITIONIX_APP_KEY "
            "not set in .env. Sign up free at https://www.nutritionix.com/food-api"
        )
        return []

    url     = f"{NUTRITIONIX_BASE}/natural/nutrients"
    headers = {
        "x-app-id":    NUTRITIONIX_APP_ID,
        "x-app-key":   NUTRITIONIX_APP_KEY,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            url,
            json={"query": text},
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()

        return [
            {
                "name":      f["food_name"],
                "quantity":  f["serving_qty"],
                "unit":      f["serving_unit"],
                "calories":  round(f["nf_calories"], 1),
                "protein_g": round(f.get("nf_protein",              0), 1),
                "carbs_g":   round(f.get("nf_total_carbohydrate",   0), 1),
                "fat_g":     round(f.get("nf_total_fat",            0), 1),
                "fiber_g":   round(f.get("nf_dietary_fiber",        0), 1),
            }
            for f in resp.json().get("foods", [])
        ]

    except requests.exceptions.RequestException as e:
        print(f"[Nutritionix] API error: {e}")
        return []


# ============================================================
# 4. WGER EXERCISE DATABASE
#    No key needed for read operations.
#    Docs: https://wger.de/api/v2/
# ============================================================

def search_exercise(name: str, language: int = 2) -> list[dict]:
    """
    Search the Wger exercise database by name.

    Args:
        name:     Exercise name (e.g. "bench press").
        language: Language ID — 2 = English.

    Returns:
        List of exercise summary dicts, or [] on failure.
    """
    url    = f"{WGER_BASE}/exercise/search/"
    params = {"term": name, "language": language, "format": "json"}

    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        return [
            {
                "name":        s["value"],
                "exercise_id": s["data"]["id"],
                "category":    s["data"].get("category", {}).get("name", ""),
            }
            for s in resp.json().get("suggestions", [])
        ]

    except requests.exceptions.RequestException as e:
        print(f"[Wger] Search error: {e}")
        return []


def get_exercise_detail(exercise_id: int) -> dict:
    """
    Fetch full exercise detail including primary and secondary muscles.

    Returns:
        Detail dict, or {} on failure.
    """
    url = f"{WGER_BASE}/exerciseinfo/{exercise_id}/"

    try:
        resp = requests.get(url, params={"format": "json"}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        description = ""
        for trans in data.get("translations", []):
            if trans.get("language") == 2:
                description = trans.get("description", "")
                break

        return {
            "name":               data.get("name", ""),
            "category":           data.get("category", {}).get("name", ""),
            "muscles_primary":    [m["name_en"] for m in data.get("muscles",           [])],
            "muscles_secondary":  [m["name_en"] for m in data.get("muscles_secondary", [])],
            "description":        description,
        }

    except requests.exceptions.RequestException as e:
        print(f"[Wger] Detail error: {e}")
        return {}


def proxy_wger_endpoint(endpoint: str, params: dict = None) -> dict:
    """
    Generic proxy to fetch data from any Wger API v2 endpoint.
    Provides access to routines, equipment, muscles, etc.
    """
    # Quick fix to prevent double slashes if endpoint already has one
    endpoint = endpoint.strip("/")
    url = f"{WGER_BASE}/{endpoint}/"
    
    try:
        resp = requests.get(url, params=params or {}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        print(f"[Wger] Proxy error for {endpoint}: {e}")
        return {"error": str(e)}


# ============================================================
# 4.5. EXERCISEDB (RapidAPI)
# ============================================================

def search_exercisedb(name: str) -> list[dict]:
    """
    Search exercises using ExerciseDB from RapidAPI.
    
    Args:
        name: Exercise name (e.g. "bench").
        
    Returns:
        List of detailed exercise dicts, or [] on failure.
    """
    url = f"https://{EXERCISEDB_HOST}/exercises/name/{name}"
    headers = {
        "x-rapidapi-host": EXERCISEDB_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        
        return [
            {
                "exercise_id": str(item.get("id", "")),
                "name":        item.get("name", "").title(),
                "body_part":   item.get("bodyPart", ""),
                "equipment":   item.get("equipment", ""),
                "target":      item.get("target", ""),
                "gif_url":     item.get("gifUrl", ""),
                "instructions": item.get("instructions", []),
            }
            for item in data[:10]  # limit to top 10 to avoid huge payloads
        ]

    except requests.exceptions.RequestException as e:
        print(f"[ExerciseDB] API error: {e}")
        return []



# ============================================================
# 5. OPEN-METEO WEATHER
#    No key needed. 10,000 calls/day free.
#    Docs: https://open-meteo.com/en/docs
# ============================================================

def get_weather_context(latitude: float, longitude: float) -> dict:
    """
    Fetch current weather and UV index for context-aware recommendations.

    Returns a safe default dict (temp 20°C, no rain) on failure so
    callers don't need to handle None.
    Returns:
        Weather context dict including recommendation_hints list.
    """
    _default = {
        "temperature_c":      20.0,
        "precipitation_mm":   0.0,
        "uv_index":           0.0,
        "wind_speed_kmh":     0.0,
        "is_raining":         False,
        "high_uv":            False,
        "recommendation_hints": [],
    }

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

        return {
            "temperature_c":      temp,
            "precipitation_mm":   current.get("precipitation",    0),
            "uv_index":           uv_index,
            "wind_speed_kmh":     current.get("wind_speed_10m",   0),
            "is_raining":         is_raining,
            "high_uv":            uv_index >= 6,
            "recommendation_hints": weather_hints(is_raining, uv_index, temp),
        }

    except requests.exceptions.RequestException as e:
        print(f"[Weather] API error: {e}")
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


def get_calorie_adjustment_from_weather(latitude: float, longitude: float) -> float:
    """
    Return a calorie multiplier based on ambient temperature.

    Integrates with UserProfile.target_calories so recommendations
    adapt to the user's environment:

        adjusted_calories = user.target_calories * get_calorie_adjustment_from_weather(lat, lng)

    Returns:
        1.10 (cold, +10 %), 0.95 (hot, -5 %), or 1.0 (neutral / fallback).
    """
    try:
        weather = get_weather_context(latitude, longitude)
        if weather["temperature_c"] <= 5:
            return 1.10
        if weather["temperature_c"] >= 30:
            return 0.95
        return 1.0
    except Exception:
        return 1.0


# ============================================================
# FOODITEM CONVERTERS  (Engine bridge)
#
# These functions translate raw API dicts into FoodItem objects
# so external data feeds directly into MealRecommendationEngine
# and NutritionAnalyzer without any changes to those classes.
# ============================================================

def food_facts_to_fooditem(api_dict: dict) -> FoodItem:
    """
    Convert an Open Food Facts nutrition dict to a FoodItem.

    Uses parse_food_facts_product output as input — call chain:
        search_food_by_name() -> parse_food_facts_product() -> food_facts_to_fooditem()
    """
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


def nutritionix_to_fooditem(api_dict: dict) -> FoodItem:
    """
    Convert a Nutritionix NLP result dict to a FoodItem.

    Uses log_natural_language_meal() output as input.
    """
    return FoodItem(
        food_id=f"nix_{uuid.uuid4().hex[:8]}",
        name=api_dict.get("name", "Unknown"),
        nutrition_info=NutritionInfo(
            calories=  api_dict.get("calories",  0),
            protein_g= api_dict.get("protein_g", 0),
            carbs_g=   api_dict.get("carbs_g",   0),
            fat_g=     api_dict.get("fat_g",     0),
            fiber_g=   api_dict.get("fiber_g",   0),
        ),
        category="external",
        tags=["nlp_parsed", "nutritionix"],
    )


def usda_to_fooditem(usda_dict: dict) -> FoodItem:
    """
    Convert a USDA FoodData Central search result to a FoodItem.

    USDA returns nutrients as a list of {nutrientName, value} objects
    rather than a flat dict, so this function extracts by name.

    Uses search_usda_food() output as input.
    """
    # Build a name → value lookup from the nutrients list
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


# ============================================================
# UNIFIED SEARCH  (recommended entry point for the main app)
# ============================================================

def search_all_sources(query: str, page_size: int = 5) -> list[FoodItem]:
    """
    Search all available food APIs and return a deduplicated list of FoodItems.

    Priority order (highest accuracy first):
        1. USDA FoodData Central
        2. Open Food Facts

    Nutritionix is excluded here because it requires a natural-language
    sentence rather than a keyword query — call log_natural_language_meal()
    directly for NLP-style input.

    Deduplication is name-based (case-insensitive) so the same food
    returned by multiple APIs doesn't inflate the database.
    """
    results:    list[FoodItem] = []
    seen_names: set[str]       = set()

    # ── 1. USDA — most accurate for whole foods ──────────────────────────
    for item in search_usda_food(query, page_size):
        food = usda_to_fooditem(item)
        key  = food.name.lower().strip()
        if key not in seen_names and food.nutrition_info.calories > 0:
            results.append(food)
            seen_names.add(key)

    # ── 2. Open Food Facts — broader packaged product coverage ───────────
    for item in search_food_by_name(query, page_size):
        food = food_facts_to_fooditem(item)
        key  = food.name.lower().strip()
        if key not in seen_names and food.nutrition_info.calories > 0:
            results.append(food)
            seen_names.add(key)

    return results[:page_size]


# ============================================================
# QUICK TEST — run: python api/external_apis.py
# ============================================================

if __name__ == "__main__":

    print("\n=== Open Food Facts — Name Search ===")
    foods = search_food_by_name("oatmeal", page_size=2)
    for f in foods:
        print(f"  {f['name']} — {f['calories_per_100g']} kcal/100g")

    print("\n=== Open Food Facts — Barcode Lookup ===")
    product = get_food_by_barcode("0737628064502")   # correct 13-digit EAN
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

    print("\n=== Wger — Exercise Detail ===")
    if exercises:
        detail = get_exercise_detail(exercises[0]["exercise_id"])
        print(f"  Name:            {detail.get('name')}")
        print(f"  Category:        {detail.get('category')}")
        print(f"  Primary muscles: {detail.get('muscles_primary')}")

    print("\n=== Open-Meteo — Weather Context ===")
    weather = get_weather_context(3.1390, 101.6869)   # Kuala Lumpur
    print(f"  Temp: {weather['temperature_c']}°C | UV: {weather['uv_index']}")
    adj = get_calorie_adjustment_from_weather(3.1390, 101.6869)
    print(f"  Calorie adjustment multiplier: {adj}")
    for hint in weather["recommendation_hints"]:
        print(f"  Hint: {hint}")

    print("\n=== FoodItem Converter Test ===")
    if usda_results:
        item = usda_to_fooditem(usda_results[0])
        print(f"  {item.name} | {item.nutrition_info.calories} kcal | "
              f"P:{item.nutrition_info.protein_g}g "
              f"C:{item.nutrition_info.carbs_g}g "
              f"F:{item.nutrition_info.fat_g}g")

    # Nutritionix NLP — only runs if keys are in .env
    if NUTRITIONIX_APP_ID and NUTRITIONIX_APP_KEY:
        print("\n=== Nutritionix — NLP Meal Parsing ===")
        meals = log_natural_language_meal("2 boiled eggs and a banana")
        for m in meals:
            print(f"  {m['name']}: {m['calories']} kcal | "
                  f"P:{m['protein_g']}g C:{m['carbs_g']}g F:{m['fat_g']}g")
        # Convert first result to FoodItem
        if meals:
            fi = nutritionix_to_fooditem(meals[0])
            print(f"  → FoodItem: {fi.name} ({fi.food_id})")
    else:
        print("\n=== Nutritionix NLP ===")
        print("  Skipped — add NUTRITIONIX_APP_ID and NUTRITIONIX_APP_KEY to .env")