"""Wger and ExerciseDB wrappers."""

import requests

from api.external_api_common import (
    WGER_BASE,
    EXERCISEDB_HOST,
    RAPIDAPI_KEY,
    REQUEST_TIMEOUT,
    TTL_MEDIUM,
    cache_get,
    cache_set,
    logger,
)


def search_exercise(name: str, language: int = 2) -> list[dict]:
    cache_key = f"wger:search:{name.strip().lower()}:{language}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{WGER_BASE}/exercise/search/"
    params = {"term": name, "language": language, "format": "json"}

    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        results = [
            {
                "name": s["value"],
                "exercise_id": s["data"]["id"],
                "category": s["data"].get("category", {}).get("name", ""),
            }
            for s in resp.json().get("suggestions", [])
        ]
        return cache_set(cache_key, results, TTL_MEDIUM)
    except requests.exceptions.RequestException as exc:
        logger.warning("[Wger] Search error: %s", exc)
        return []


def proxy_wger_endpoint(endpoint: str, params: dict = None) -> dict:
    endpoint = endpoint.strip("/")
    url = f"{WGER_BASE}/{endpoint}/"
    try:
        resp = requests.get(url, params=params or {}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as exc:
        logger.warning("[Wger] Proxy error for %s: %s", endpoint, exc)
        return {"error": str(exc)}


def search_exercisedb(name: str) -> list[dict]:
    cache_key = f"exercisedb:search:{name.strip().lower()}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"https://{EXERCISEDB_HOST}/exercises/name/{name}"
    headers = {
        "x-rapidapi-host": EXERCISEDB_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY,
    }

    try:
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        results = [
            {
                "exercise_id": str(item.get("id", "")),
                "name": item.get("name", "").title(),
                "body_part": item.get("bodyPart", ""),
                "equipment": item.get("equipment", ""),
                "target": item.get("target", ""),
                "gif_url": item.get("gifUrl", ""),
                "instructions": item.get("instructions", []),
            }
            for item in data[:10]
        ]
        return cache_set(cache_key, results, TTL_MEDIUM)
    except requests.exceptions.RequestException as exc:
        logger.warning("[ExerciseDB] API error: %s", exc)
        return []
