"""Compatibility facade for external API wrappers."""

from api.external_food_apis import (
    search_food_by_name,
    get_food_by_barcode,
    parse_food_facts_product,
    search_usda_food,
    food_facts_to_fooditem,
    usda_to_fooditem,
    search_all_sources,
)
from api.external_fitness_apis import (
    search_exercise,
    proxy_wger_endpoint,
    search_exercisedb,
)
from api.external_weather_api import get_weather_context, weather_hints


__all__ = [
    "search_food_by_name",
    "get_food_by_barcode",
    "parse_food_facts_product",
    "search_usda_food",
    "search_exercise",
    "proxy_wger_endpoint",
    "search_exercisedb",
    "get_weather_context",
    "weather_hints",
    "food_facts_to_fooditem",
    "usda_to_fooditem",
    "search_all_sources",
]

