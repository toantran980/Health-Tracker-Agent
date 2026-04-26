"""Shared config, logging, and cache for external API clients."""

import logging
import os
import time

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10

TTL_SHORT = 300
TTL_MEDIUM = 900
TTL_LONG = 3600

USDA_API_KEY = os.getenv("USDA_API_KEY", "DEMO_KEY")
RAPIDAPI_KEY = os.getenv("EXERCISEDB_API_KEY", "")

FOOD_FACTS_BASE = "https://world.openfoodfacts.org"
WGER_BASE = "https://wger.de/api/v2"
OPEN_METEO_BASE = "https://api.open-meteo.com/v1"
USDA_BASE = "https://api.nal.usda.gov/fdc/v1"
EXERCISEDB_HOST = "exercisedb.p.rapidapi.com"

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
