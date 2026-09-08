"""Compatibility facade for external API wrappers."""

from api.external_fitness_apis import (
    proxy_wger_endpoint,
    search_exercise,
    search_exercisedb,
)
from api.external_food_apis import (
    food_facts_to_fooditem,
    get_food_by_barcode,
    parse_food_facts_product,
    search_all_sources,
    search_food_by_name,
    search_usda_food,
    usda_to_fooditem,
)

__all__ = [
    "food_facts_to_fooditem",
    "get_food_by_barcode",
    "parse_food_facts_product",
    "proxy_wger_endpoint",
    "search_all_sources",
    "search_exercise",
    "search_exercisedb",
    "search_food_by_name",
    "search_usda_food",
    "usda_to_fooditem",
]
