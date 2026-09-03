# Configuration

Copy `.env.example` to `.env` for local configuration:

```powershell
Copy-Item .env.example .env
```

The application loads values from environment variables. The settings below
are optional unless noted otherwise.

## Authentication

- `SECRET_KEY`: signs session cookies. The application has a development
  default, but deployments should set a strong, unique value. Generate one
  with:

  ```powershell
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

Use a strong, unique value outside local development. Never commit `.env`.

## Server

- `HOST`: bind address; defaults to `0.0.0.0`.
- `PORT`: application port; defaults to `5001`.
- `DEBUG`: enables Flask debug mode; defaults to `True` locally and is disabled
  by Docker Compose.

## MongoDB

- `MONGO_URI`: database connection string; defaults to
  `mongodb://localhost:27017`.
- `MONGO_DB_NAME`: database name; defaults to `health_tracker`.
- `MONGO_CONNECT_RETRIES` and `MONGO_CONNECT_RETRY_DELAY`: startup retry
  behavior when MongoDB is unavailable.
- `MONGO_MEALS_TTL_DAYS` and `MONGO_DAILY_LOGS_TTL_DAYS`: retention periods for
  the meals and daily logs collections.

The app falls back to in-memory storage when MongoDB is unavailable.

## External Services

- `USDA_API_KEY`: USDA food lookup key.
- `EXERCISEDB_API_KEY`: ExerciseDB lookup key.
- `GROQ_API_KEY`: optional hosted chatbot key. Without it, the local rule-based
  chatbot is used.

External service keys are optional; built-in fallbacks are used when they are
empty.

## Sessions and Rate Limits

- `SESSION_COOKIE_SECURE`: set to `True` when serving over HTTPS.
- `SESSION_COOKIE_SAMESITE` and `SESSION_COOKIE_HTTPONLY`: session cookie
  hardening settings.
- `SESSION_LIFETIME_MINUTES`: session lifetime; `0` keeps sessions permanent.
- `SESSION_REFRESH`: refreshes the session lifetime on authenticated requests.
- `CSRF_PROTECTION`: enables CSRF checks for state-changing authenticated
  requests.
- `EXTERNAL_API_RATE_LIMIT` and `EXTERNAL_API_RATE_WINDOW_SECONDS`: per-client
  rate-limit window for proxied external endpoints.
- `RATE_LIMIT_BACKEND`: `memory` by default or `redis` for shared limits across
  workers.
- `REDIS_URL`: Redis connection string when `RATE_LIMIT_BACKEND=redis`.

See `.env.example` for the complete template and default values.
