"""Open-Meteo weather context wrapper."""

import requests

from api.external_api_common import (
    OPEN_METEO_BASE,
    REQUEST_TIMEOUT,
    TTL_SHORT,
    cache_get,
    cache_set,
    logger,
)


def weather_hints(is_raining: bool, uv: float, temp: float) -> list[str]:
    hints = []
    if is_raining:
        hints.append("Rainy today - suggest indoor workout alternatives.")
    if uv >= 6:
        hints.append(f"High UV index ({uv:.0f}) - increase water intake.")
    if temp >= 30:
        hints.append("Hot weather - recommend electrolytes in meal plan.")
    if temp <= 5:
        hints.append("Cold weather - suggest higher-calorie warming meals.")
    return hints


def get_weather_context(latitude: float, longitude: float) -> dict:
    default = {
        "temperature_c": 20.0,
        "precipitation_mm": 0.0,
        "uv_index": 0.0,
        "wind_speed_kmh": 0.0,
        "is_raining": False,
        "high_uv": False,
        "recommendation_hints": [],
    }

    cache_key = f"weather:context:{round(latitude, 3)}:{round(longitude, 3)}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{OPEN_METEO_BASE}/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,precipitation,uv_index,wind_speed_10m,weather_code",
        "timezone": "auto",
    }

    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        current = resp.json().get("current", {})
        weather_code = current.get("weather_code", 0)
        is_raining = weather_code in range(51, 100)
        uv_index = current.get("uv_index", 0)
        temp = current.get("temperature_2m", 20)

        result = {
            "temperature_c": temp,
            "precipitation_mm": current.get("precipitation", 0),
            "uv_index": uv_index,
            "wind_speed_kmh": current.get("wind_speed_10m", 0),
            "is_raining": is_raining,
            "high_uv": uv_index >= 6,
            "recommendation_hints": weather_hints(is_raining, uv_index, temp),
        }
        return cache_set(cache_key, result, TTL_SHORT)
    except requests.exceptions.RequestException as exc:
        logger.warning("[Weather] API error: %s", exc)
        return default
