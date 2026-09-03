# AI Health & Wellness Tracker - Implementation Guide

## Summary

This project is a Flask-based health and productivity platform with:

- user profile management
- nutrition logging and analysis
- study schedule optimization
- productivity prediction
- chatbot interactions
- external food and exercise API integrations
- optional MongoDB persistence
- Docker-based local deployment

## Start Here

For setup and run commands, use [QUICKSTART.md](QUICKSTART.md).

Quick Docker start:

```powershell
docker compose up --build -d
```

Open:

- Frontend: [http://localhost:5001/](http://localhost:5001/)
- Health check: [http://localhost:5001/api/health](http://localhost:5001/api/health)

Stop:

```powershell
docker compose down
```

- Flask routes are split by domain under [api/blueprints](api/blueprints).
- In-memory caches are used for live runtime objects.
- When MongoDB is available, users, daily meal logs, schedules, productivity sessions, and activity logs are persisted and rehydrated.
- Error responses are standardized as `{"error": "...", "code": "..."}` — see `api/blueprints/helpers.py:error_response`.
- External API wrappers include lightweight TTL caching (USDA, Open Food Facts, Wger, Open-Meteo) and a shared sliding-window rate limiter (`api/rate_limiter.py`), pluggable between an in-process backend and Redis.

### AI Modules

- [ai_modules/knowledge_base.py](ai_modules/knowledge_base.py): rule-based recommendations, behavioral analysis.
- [ai_modules/scheduler_optimizer.py](ai_modules/scheduler_optimizer.py): schedule optimization.
- [ai_modules/productivity_predictor.py](ai_modules/productivity_predictor.py): focus score prediction (uses Random Forest via scikit-learn for best results).
- [ai_modules/nutrition_analyzer.py](ai_modules/nutrition_analyzer.py): nutrition trends and adherence.
- [ai_modules/meal_recommendation_engine.py](ai_modules/meal_recommendation_engine.py): meal recommendations.
- [ai_modules/activity_recommendation_engine.py](ai_modules/activity_recommendation_engine.py): activity recommendations.
- [ai_modules/health_chatbot.py](ai_modules/health_chatbot.py): AI health chatbot (Groq-powered).

### Authentication

- Passwords are hashed with Werkzeug (`generate_password_hash`) and stored on the user document; the hash is never exposed by API responses (see `models/user_profile.py:to_public_dict`).
- `POST /api/auth/login` sets a signed Flask session cookie (`app.secret_key` from `config.SECRET_KEY`); `POST /api/auth/logout` clears it; `GET /api/auth/me` reports the session state.
- Nutrition logging/analysis and the chatbot endpoints call `require_auth(user_id)` (`api/blueprints/helpers.py`) and return `401 AUTH_REQUIRED` when no matching session exists.
- Session cookies are hardened via `SESSION_COOKIE_SECURE`/`SESSION_COOKIE_SAMESITE`/`SESSION_COOKIE_HTTPONLY` (`api/routes.py`, `config.py`).
- CSRF: a per-session token is stored in the cookie (`get_csrf_token` in helpers). `api/routes.py:before_request` rejects state-changing requests that carry an active session but the wrong `X-CSRF-Token` header (`403 CSRF_FAILED`). Pre-auth endpoints (`/api/auth/login`, `/api/user/create`) are exempt. The dashboard sends the header automatically from the token exposed by `/api/auth/me` and the login response.

### Persistence

- [api/mongo_store.py](api/mongo_store.py) handles MongoDB connectivity.
- Falls back to in-memory behavior if MongoDB is unavailable.
- TTL indexes are created on `meals.timestamp` and `daily_logs.updated_at` from `MONGO_MEALS_TTL_DAYS` / `MONGO_DAILY_LOGS_TTL_DAYS`.

## Endpoints Overview

Primary route groups:

- Auth: login, logout, me
- User: create, fetch profile, set password
- Nutrition: log meal, analysis, macro recommendations, meal recommendations (all require a login session)
- Schedule: optimize tasks, available slots, schedule history
- Productivity: predict focus, optimal study time, saved productivity sessions
- Activity: recommendations, log activity, activity logs, trend analysis
- Chatbot and insights (chatbot requires a login session)
- External data: food, exercise, weather (rate-limited per client IP)
- Health and metrics: liveness, service status, model metrics

For the endpoint implementation, see the blueprint files under
[api/blueprints](api/blueprints).

## Validation and Testing

- API health endpoint: [http://localhost:5001/api/health](http://localhost:5001/api/health)
- Unit tests:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

- Time-based external integrations (rate limiter, TTL caches) are tested deterministically with small windows.
- AI module evaluation data lives under [data/](data) (`training_data.csv`, `eval.csv`); they power the quantitative `ProductivityPredictor` tests.

