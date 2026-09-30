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

Never commit `.env`.

## Server

- `APP_ENV`: application environment (`development` default, or `production`).
  `FLASK_ENV` is accepted as a fallback. Production mode enforces a strong
  `SECRET_KEY` and flips `DEBUG`/`SESSION_COOKIE_SECURE` defaults.
- `HOST`: bind address; defaults to `0.0.0.0`.
- `PORT`: application port; defaults to `5001`.
- `DEBUG`: enables Flask debug mode; defaults to `True` locally and is disabled
  in Docker/production.
- `DEVELOPER_MODE`: enables developer diagnostics; defaults to the value of
  `DEBUG`.
- `SHOW_API_OUTPUT`: shows the raw JSON API console in the dashboard. Defaults
  to `DEVELOPER_MODE`; set it to `true` when API diagnostics are needed without
  enabling the rest of developer mode.

## MongoDB

- `MONGO_URI`: database connection string; defaults to
  `mongodb://localhost:27017`.
- `MONGO_DB_NAME`: database name; defaults to `health_tracker`.
- `MONGO_CONNECT_RETRIES` and `MONGO_CONNECT_RETRY_DELAY`: startup retry
  behavior when MongoDB is unavailable.
- `MONGO_MEALS_TTL_DAYS`, `MONGO_DAILY_LOGS_TTL_DAYS`,
  `MONGO_ACTIVITY_LOGS_TTL_DAYS`, `MONGO_SLEEP_LOGS_TTL_DAYS` (default `365`),
  and `MONGO_CHAT_HISTORY_TTL_DAYS` (default `180`): retention periods for the
  corresponding MongoDB collections.

The app falls back to in-memory storage when MongoDB is unavailable.

## External Services

- `USDA_API_KEY`: USDA food lookup key.
- `EXERCISEDB_API_KEY`: ExerciseDB lookup key.
- `GROQ_API_KEY`: optional hosted chatbot key. Without it, the local rule-based
  chatbot is used.
- `GROQ_MAX_COMPLETION_TOKENS`: max output tokens per Groq reply (default
  `4096`). Free-tier models reserve this whole budget per request against their
  TPM, so values ≥ `8000` always trip rate limits; on a `413` the chatbot
  retries once with a reduced budget and truncated context.

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
