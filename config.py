import os
import secrets
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

ENVIRONMENT = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "development")).lower()
IS_PRODUCTION = ENVIRONMENT == "production"

# Server Settings
PORT = int(os.getenv("PORT", "5001"))
HOST = os.getenv("HOST", "0.0.0.0")
DEBUG = os.getenv("DEBUG", str(not IS_PRODUCTION)).lower() == "true"
# Developer mode enables diagnostics such as the raw API output console.
DEVELOPER_MODE = os.getenv("DEVELOPER_MODE", str(DEBUG)).lower() == "true"
SHOW_API_OUTPUT = os.getenv("SHOW_API_OUTPUT", str(DEVELOPER_MODE)).lower() == "true"

# Secret key for signed session cookies (required for /api/auth/login).
# In production, a real secret must be provided via environment variables.
SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("FLASK_SECRET_KEY")
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise RuntimeError("SECRET_KEY must be set in production mode.")
    SECRET_KEY = secrets.token_hex(32)

# Session cookie hardening.
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", str(IS_PRODUCTION).lower()).lower() == "true"
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_HTTPONLY = os.getenv("SESSION_COOKIE_HTTPONLY", "true").lower() == "true"

# Session lifetime (minutes) before an auth session expires. Default 0 keeps
# cookies permanent (current behaviour). Set > 0 to expire idle sessions;
# SESSION_REFRESH extends the TTL on every authenticated request (sliding).
SESSION_LIFETIME_MINUTES = int(os.getenv("SESSION_LIFETIME_MINUTES", "0"))
SESSION_REFRESH = os.getenv("SESSION_REFRESH", "true").lower() == "true"

# CSRF: enforce an X-CSRF-Token header on state-changing requests that arrive
# with an active session (see api/routes.py). Exemptions: pre-auth endpoints.
CSRF_PROTECTION = os.getenv("CSRF_PROTECTION", "true").lower() == "true"

# MongoDB Settings
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "health_tracker")
MONGO_CONNECT_RETRIES = int(os.getenv("MONGO_CONNECT_RETRIES", "5"))
MONGO_CONNECT_RETRY_DELAY = float(os.getenv("MONGO_CONNECT_RETRY_DELAY", "2"))

# MongoDB TTL (days) — bounds growth of the meals and daily_logs collections.
MONGO_MEALS_TTL_DAYS = int(os.getenv("MONGO_MEALS_TTL_DAYS", "365"))
MONGO_DAILY_LOGS_TTL_DAYS = int(os.getenv("MONGO_DAILY_LOGS_TTL_DAYS", "365"))

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
