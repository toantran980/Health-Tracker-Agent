"""
external_apis.py
Plug-and-play wrappers for free external APIs used by the Health & Wellness Tracker.
"""

import requests


# ─────────────────────────────────────────────
# 1. OPEN FOOD FACTS  (no API key needed)
# ─────────────────────────────────────────────

FOOD_FACTS_BASE = "https://world.openfoodfacts.org"

def search_food_by_name(query: str, page_size: int = 5) -> list[dict]:
    """Search foods by name. Returns a list of simplified nutrition dicts."""
    url = f"{FOOD_FACTS_BASE}/cgi/search.pl"
    params = {
        "search_terms": query,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": page_size,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    products = resp.json().get("products", [])
    return [_parse_food_facts_product(p) for p in products if p.get("product_name")]


def get_food_by_barcode(barcode: str) -> dict | None:
    """Lookup a single product by barcode (EAN/UPC)."""
    url = f"{FOOD_FACTS_BASE}/api/v2/product/{barcode}.json"
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("status") != 1:
        return None
    return _parse_food_facts_product(data["product"])


def _parse_food_facts_product(p: dict) -> dict:
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


# ─────────────────────────────────────────────
# 2. NUTRITIONIX  (free tier: 500 calls/day)
#    Sign up at https://www.nutritionix.com/food-api
# ─────────────────────────────────────────────

NUTRITIONIX_BASE = "https://trackapi.nutritionix.com/v2"

def log_natural_language_meal(text: str, app_id: str, app_key: str) -> list[dict]:
    """
    Parse a free-text meal description into structured nutrition data.
    Example input: "2 scrambled eggs and a slice of whole wheat toast"
    """
    url = f"{NUTRITIONIX_BASE}/natural/nutrients"
    headers = {
        "x-app-id": app_id,
        "x-app-key": app_key,
        "Content-Type": "application/json",
    }
    resp = requests.post(url, json={"query": text}, headers=headers, timeout=10)
    resp.raise_for_status()
    foods = resp.json().get("foods", [])
    return [
        {
            "name": f["food_name"],
            "quantity": f["serving_qty"],
            "unit": f["serving_unit"],
            "calories": round(f["nf_calories"], 1),
            "protein_g": round(f.get("nf_protein", 0), 1),
            "carbs_g": round(f.get("nf_total_carbohydrate", 0), 1),
            "fat_g": round(f.get("nf_total_fat", 0), 1),
            "fiber_g": round(f.get("nf_dietary_fiber", 0), 1),
        }
        for f in foods
    ]


# ─────────────────────────────────────────────
# 3. WGER WORKOUT MANAGER  (no key for reads)
#    Docs: https://wger.de/api/v2/
# ─────────────────────────────────────────────

WGER_BASE = "https://wger.de/api/v2"

def search_exercise(name: str, language: int = 2) -> list[dict]:
    """Search exercise database by name. language=2 is English."""
    url = f"{WGER_BASE}/exercise/search/"
    params = {"term": name, "language": language, "format": "json"}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    suggestions = resp.json().get("suggestions", [])
    return [
        {
            "name": s["value"],
            "exercise_id": s["data"]["id"],
            "category": s["data"].get("category", {}).get("name", ""),
        }
        for s in suggestions
    ]


def get_exercise_detail(exercise_id: int) -> dict:
    """Get full detail for a single exercise including muscles worked."""
    url = f"{WGER_BASE}/exerciseinfo/{exercise_id}/"
    resp = requests.get(url, params={"format": "json"}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    muscles = [m["name_en"] for m in data.get("muscles", [])]
    muscles_secondary = [m["name_en"] for m in data.get("muscles_secondary", [])]
    category = data.get("category", {}).get("name", "")
    description_html = ""
    for trans in data.get("translations", []):
        if trans.get("language") == 2:
            description_html = trans.get("description", "")
            break
    return {
        "name": data.get("name", ""),
        "category": category,
        "muscles_primary": muscles,
        "muscles_secondary": muscles_secondary,
        "description": description_html,
    }


# ─────────────────────────────────────────────
# 4. OPEN-METEO  (no API key needed)
#    Docs: https://open-meteo.com/en/docs
# ─────────────────────────────────────────────

OPEN_METEO_BASE = "https://api.open-meteo.com/v1"

def get_weather_context(latitude: float, longitude: float) -> dict:
    """
    Fetch current weather + UV index for context-aware recommendations.
    Example: rainy day → suggest indoor workout; hot/sunny → hydration reminder.
    """
    url = f"{OPEN_METEO_BASE}/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,precipitation,uv_index,wind_speed_10m,weather_code",
        "timezone": "auto",
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    current = resp.json().get("current", {})

    weather_code = current.get("weather_code", 0)
    is_raining = weather_code in range(51, 100)   # WMO codes 51-99 = precipitation
    uv_index = current.get("uv_index", 0)

    return {
        "temperature_c": current.get("temperature_2m"),
        "precipitation_mm": current.get("precipitation", 0),
        "uv_index": uv_index,
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "is_raining": is_raining,
        "high_uv": uv_index >= 6,
        "recommendation_hints": _weather_hints(is_raining, uv_index, current.get("temperature_2m", 20)),
    }


def _weather_hints(is_raining: bool, uv: float, temp: float) -> list[str]:
    hints = []
    if is_raining:
        hints.append("Rainy today — suggest indoor workout alternatives.")
    if uv >= 6:
        hints.append(f"High UV index ({uv:.0f}) — remind user to increase water intake.")
    if temp >= 30:
        hints.append("Hot weather — add electrolyte reminder to meal recommendations.")
    if temp <= 5:
        hints.append("Cold weather — suggest warming, higher-calorie meal options.")
    return hints
