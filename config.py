import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def get_bool_env(name: str, default: bool = False) -> bool:
    """Parse common boolean env values robustly across shells and Docker.

    Accepts values such as True/False, 1/0, yes/no, y/n, on/off. Unknown values
    fall back to the supplied default to keep configuration safe and predictable.
    """
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    normalized = str(raw_value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off", ""}:
        return False
    return default


ENVIRONMENT = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "development")).lower()
IS_PRODUCTION = ENVIRONMENT == "production"

# Server Settings
PORT = int(os.getenv("PORT", "5001"))
HOST = os.getenv("HOST", "0.0.0.0")
DEBUG = get_bool_env("DEBUG", default=not IS_PRODUCTION)
# Developer mode enables diagnostics such as the raw API output console.
DEVELOPER_MODE = get_bool_env("DEVELOPER_MODE", default=DEBUG)
SHOW_API_OUTPUT = get_bool_env("SHOW_API_OUTPUT", default=DEVELOPER_MODE)

# Secret key for signed session cookies (required for /api/auth/login).
# In production, a real secret must be provided via environment variables.
SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("FLASK_SECRET_KEY")
INSECURE_SECRET_PLACEHOLDERS = {
    "replace-with-a-long-random-secret",
    "secret",
    "changeme",
    "password",
    "dev_secret",
}
if IS_PRODUCTION and (
    not SECRET_KEY
    or SECRET_KEY.strip() in INSECURE_SECRET_PLACEHOLDERS
    or len(SECRET_KEY.strip()) < 32
):
        raise RuntimeError(
            "SECRET_KEY must be set to a strong random string (minimum 32 characters) in production mode."
        )
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)

# Session cookie hardening.
SESSION_COOKIE_SECURE = get_bool_env("SESSION_COOKIE_SECURE", default=IS_PRODUCTION)
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_HTTPONLY = get_bool_env("SESSION_COOKIE_HTTPONLY", default=True)

# Session lifetime (minutes) before an auth session expires. Default 0 keeps
# cookies permanent (current behaviour). Set > 0 to expire idle sessions;
# SESSION_REFRESH extends the TTL on every authenticated request (sliding).
SESSION_LIFETIME_MINUTES = int(os.getenv("SESSION_LIFETIME_MINUTES", "0"))
SESSION_REFRESH = get_bool_env("SESSION_REFRESH", default=True)

# CSRF: enforce an X-CSRF-Token header on state-changing requests that arrive
# with an active session (see api/routes.py). Exemptions: pre-auth endpoints.
CSRF_PROTECTION = get_bool_env("CSRF_PROTECTION", default=True)

# MongoDB Settings
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "health_tracker")
MONGO_CONNECT_RETRIES = int(os.getenv("MONGO_CONNECT_RETRIES", "5"))
MONGO_CONNECT_RETRY_DELAY = float(os.getenv("MONGO_CONNECT_RETRY_DELAY", "2"))

# MongoDB TTL (days) — bounds growth of persisted collections.
MONGO_MEALS_TTL_DAYS = int(os.getenv("MONGO_MEALS_TTL_DAYS", "365"))
MONGO_DAILY_LOGS_TTL_DAYS = int(os.getenv("MONGO_DAILY_LOGS_TTL_DAYS", "365"))
MONGO_ACTIVITY_LOGS_TTL_DAYS = int(os.getenv("MONGO_ACTIVITY_LOGS_TTL_DAYS", "365"))
MONGO_SLEEP_LOGS_TTL_DAYS = int(os.getenv("MONGO_SLEEP_LOGS_TTL_DAYS", "365"))
MONGO_CHAT_HISTORY_TTL_DAYS = int(os.getenv("MONGO_CHAT_HISTORY_TTL_DAYS", "180"))

# Rate limiting for external API proxied endpoints (per client IP).
EXTERNAL_API_RATE_LIMIT = int(os.getenv("EXTERNAL_API_RATE_LIMIT", "30"))
EXTERNAL_API_RATE_WINDOW_SECONDS = int(os.getenv("EXTERNAL_API_RATE_WINDOW_SECONDS", "60"))
# Rate limiter backend: "memory" (default, per-process) or "redis"
# (shared across workers; requires the redis package and a reachable REDIS_URL).
RATE_LIMIT_BACKEND = os.getenv("RATE_LIMIT_BACKEND", "memory")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# API Keys
USDA_API_KEY = os.getenv("USDA_API_KEY", "DEMO_KEY")
EXERCISEDB_API_KEY = os.getenv("EXERCISEDB_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# Max completion tokens for the Groq chatbot. Free-tier models (TPM ~8000)
# reserve this whole output budget per request, so values ≥ 8000 always trip
# rate limits; 4096 covers long structured answers while leaving headroom for
# the input context. Groq truncates the reply when the model hits this cap.
GROQ_MAX_COMPLETION_TOKENS = int(os.getenv("GROQ_MAX_COMPLETION_TOKENS", "4096"))
