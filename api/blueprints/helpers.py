"""
helpers.py

Shared helper functions used across blueprint modules:
  - Serialisation / deserialisation
  - User lookup and AI module initialisation
  - Daily log management
  - Request validation (numbers, dates, required fields)
  - Session-based authentication guards
  - CSRF token management
  - Schedule task normalisation
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from flask import jsonify, session

from models.user_profile import UserProfile
from models.meal import NutritionInfo, Meal, DailyNutritionLog
from ai_modules import KnowledgeBase, NutritionAnalyzer, MealRecommendationEngine
from api.blueprints.serialization_helpers import (
    serialize_daily_log,
    deserialize_daily_log,
    user_from_doc,
)

from api.blueprints import state


def error_response(message: str, code: str, status: int = 400, details: dict[str, Any] | None = None):
    """Create a consistent API error envelope."""
    payload: dict[str, Any] = {
        "error": message,
        "code": code,
    }
    if details:
        payload["details"] = details
    return jsonify(payload), status


# Request validation helpers (centralised so blueprints stay consistent)

def require_fields(data: dict, fields: list[str]) -> Optional[tuple]:
    """Return an error_response tuple if any required field is missing."""
    missing = [f for f in fields if not data.get(f)]
    if missing:
        return error_response(
            f"Missing required field(s): {', '.join(missing)}",
            "MISSING_FIELD",
            details={"fields": missing},
        )
    return None


def coerce_int(value, default: int = 0, minimum: Optional[int] = None,
               maximum: Optional[int] = None) -> tuple[int, Optional[tuple]]:
    """Parse an int from form/query data; returns (value, error_response or None)."""
    try:
        result = int(value)
    except (TypeError, ValueError):
        return default, None
    if minimum is not None and result < minimum:
        return default, error_response(
            f"Value must be >= {minimum}", "VALUE_OUT_OF_RANGE", details={"min": minimum}
        )
    if maximum is not None and result > maximum:
        return default, error_response(
            f"Value must be <= {maximum}", "VALUE_OUT_OF_RANGE", details={"max": maximum}
        )
    return result, None


def coerce_float(value, default: float = 0.0, minimum: Optional[float] = None,
                 maximum: Optional[float] = None) -> tuple[float, Optional[tuple]]:
    """Parse a float from form/query data; returns (value, error_response or None)."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default, None
    if minimum is not None and result < minimum:
        return default, error_response(
            f"Value must be >= {minimum}", "VALUE_OUT_OF_RANGE", details={"min": minimum}
        )
    if maximum is not None and result > maximum:
        return default, error_response(
            f"Value must be <= {maximum}", "VALUE_OUT_OF_RANGE", details={"max": maximum}
        )
    return result, None


def parse_iso_datetime(value: Optional[str], default: Optional[datetime] = None) -> datetime:
    """Parse an ISO-8601 string into an aware (UTC) datetime; fall back to `default`."""
    if not value:
        return default or datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return default or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# AI module management

def ensure_ai_modules(user_id: str, user: UserProfile) -> None:
    if (user_id in state.knowledge_bases
            and user_id in state.nutrition_analyzers
            and user_id in state.meal_recommenders):
        return

    target_nutrition = NutritionInfo(
        calories=user.target_calories,
        protein_g=user.target_protein_g,
        carbs_g=user.target_carbs_g,
        fat_g=user.target_fat_g,
    )
    state.knowledge_bases[user_id]    = KnowledgeBase(user)
    state.nutrition_analyzers[user_id] = NutritionAnalyzer(target_nutrition)
    state.meal_recommenders[user_id]   = MealRecommendationEngine(user, state.GLOBAL_FOOD_DB_V2)


def hydrate_logs_for_user(user_id: str) -> None:
    if user_id in state.daily_logs or not state.mongo_store.enabled:
        return

    docs = state.mongo_store.get_daily_logs(user_id)
    if not docs:
        return

    user_logs: dict[str, DailyNutritionLog] = {}
    for doc in docs:
        date_str = doc.get("date") or datetime.now().date().isoformat()
        user_logs[date_str] = deserialize_daily_log(user_id, doc)

    state.daily_logs[user_id] = user_logs
    analyzer = state.nutrition_analyzers.get(user_id)
    if analyzer:
        analyzer.history = [user_logs[k] for k in sorted(user_logs)]


# Request helpers

def require_user(user_id: str):
    """Return (user, None) or (None, error_response)."""
    user = state.users.get(user_id)
    if not user and state.mongo_store.enabled:
        doc = state.mongo_store.get_user(user_id)
        if doc:
            user = user_from_doc(doc)
            state.users[user_id] = user

    if not user:
        return None, error_response("User not found", "USER_NOT_FOUND", 404)

    ensure_ai_modules(user_id, user)
    hydrate_logs_for_user(user_id)
    load_all_user_history(user_id)
    return user, None


def get_or_create_daily_log(user_id: str, date_str: str) -> DailyNutritionLog:
    hydrate_logs_for_user(user_id)
    user_logs = state.daily_logs.setdefault(user_id, {})
    if date_str not in user_logs:
        user_logs[date_str] = DailyNutritionLog(
            log_id=f"log_{user_id}_{date_str}",
            user_id=user_id,
            date=datetime.fromisoformat(date_str),
        )
    return user_logs[date_str]


def sync_analyzer_daily_log(user_id: str, date_str: str, daily_log: DailyNutritionLog) -> None:
    analyzer = state.nutrition_analyzers.get(user_id)
    if not analyzer:
        return
    existing = next(
        (i for i, log in enumerate(analyzer.history)
         if log.date.date().isoformat() == date_str),
        None,
    )
    if existing is not None:
        analyzer.history[existing] = daily_log
    else:
        analyzer.add_daily_log(daily_log)


def attach_meal_to_user_log(user_id: str, meal: Meal) -> DailyNutritionLog:
    date_str = meal.timestamp.date().isoformat()
    daily_log = get_or_create_daily_log(user_id, date_str)
    daily_log.meals.append(meal)
    sync_analyzer_daily_log(user_id, date_str, daily_log)
    state.mongo_store.save_daily_log(user_id, date_str, serialize_daily_log(daily_log))
    return daily_log


# Schedule helpers

def normalize_schedule_tasks(raw_tasks):
    """Map frontend schedule task payloads to ScheduleOptimizer's expected shape."""
    normalized = []
    for task in raw_tasks or []:
        name         = task.get('name') or task.get('title') or 'Untitled Task'
        duration_min = task.get('duration_min', task.get('duration_minutes', 60))
        difficulty   = task.get('difficulty', 5)
        deadline     = task.get('deadline')
        deadline_days = task.get('deadline_days')

        if deadline:
            try:
                deadline_dt = datetime.fromisoformat(deadline)
            except ValueError:
                deadline_dt = datetime.now() + timedelta(days=7)
        elif deadline_days is not None:
            try:
                deadline_dt = datetime.now() + timedelta(days=int(deadline_days))
            except (TypeError, ValueError):
                deadline_dt = datetime.now() + timedelta(days=7)
        else:
            deadline_dt = datetime.now() + timedelta(days=7)

        try:
            duration_min = int(duration_min)
        except (TypeError, ValueError):
            duration_min = 60

        try:
            difficulty = float(difficulty)
        except (TypeError, ValueError):
            difficulty = 5.0

        normalized.append({
            'name':         str(name),
            'duration_min': max(duration_min, 1),
            'difficulty':   difficulty,
            'deadline':     deadline_dt,
        })

    return normalized


# Session authentication

def require_auth(user_id: str):
    """
    Return None if the request's session is authenticated for `user_id`,
    otherwise return an error_response tuple (401).

    Uses Flask's signed session cookie set by /api/auth/login. Other
    blueprints call require_user first, then require_auth.
    """
    if session.get("user_id") == user_id:
        return None
    return error_response(
        "Authentication required. Log in via POST /api/auth/login.",
        "AUTH_REQUIRED",
        401,
    )


# CSRF tokens

def get_csrf_token() -> str:
    """
    Return (creating if needed) the per-session CSRF token.

    The token is stored in the signed session cookie and must be echoed back
    via the X-CSRF-Token header on state-changing requests. `api/routes.py`
    verifies it for authenticated POST/PUT/PATCH/DELETE requests.
    """
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_hex(16)
        session["csrf_token"] = token
    return token


def save_user_with_hash(user: UserProfile) -> bool:
    """
    Persist a user profile including its (optional) password hash.

    UserProfile.to_dict() intentionally omits password_hash so it is never
    leaked through API responses; this helper re-attaches it for storage.
    """
    doc = user.to_dict()
    doc["password_hash"] = user.password_hash
    return state.mongo_store.save_user(doc)


def load_all_user_history(user_id: str) -> None:
    """Rehydrate schedule / productivity / activity history for a user."""
    if not state.mongo_store.enabled:
        return
    if user_id not in state.schedule_history:
        state.schedule_history[user_id] = state.mongo_store.get_schedules(user_id)
    if user_id not in state.productivity_sessions:
        state.productivity_sessions[user_id] = state.mongo_store.get_productivity_sessions(user_id)
    if user_id not in state.activity_logs:
        state.activity_logs[user_id] = state.mongo_store.get_activity_logs(user_id)
