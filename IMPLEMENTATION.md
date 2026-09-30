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

For setup and run commands, use [README.md](README.md).

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
- [ai_modules/health_chatbot.py](ai_modules/health_chatbot.py): AI health chatbot (Groq-powered, keyless rule-based fallback).
- [ai_modules/health_risk_assessor.py](ai_modules/health_risk_assessor.py): rule-based risk warnings (BMI, calories, protein, sleep, hydration).
- [ai_modules/sleep_quality_predictor.py](ai_modules/sleep_quality_predictor.py): sleep quality prediction (random forest).
- [ai_modules/recovery_predictor.py](ai_modules/recovery_predictor.py): recovery / readiness prediction (random forest).
- [ai_modules/activity_classifier.py](ai_modules/activity_classifier.py): sensor-based activity recognition (random forest).
- [ai_modules/goal_tracker.py](ai_modules/goal_tracker.py): goal milestones and projections.
- [ai_modules/weekly_digest.py](ai_modules/weekly_digest.py): multi-domain weekly digest generator.

See [MODELS.md](MODELS.md) for training data, training scripts, and evaluation notes.

### Authentication

- Passwords are hashed with Werkzeug (`generate_password_hash`) and stored on the user document; the hash is never exposed by API responses (see `models/user_profile.py:to_public_dict`).
- `POST /api/auth/login` sets a signed Flask session cookie (`app.secret_key` from `config.SECRET_KEY`); `POST /api/auth/logout` clears it; `GET /api/auth/me` reports the session state.
- Every endpoint that reads or writes a user's data requires a matching login
  session: nutrition, chatbot, schedule, productivity, activity, and sleep
  endpoints call `require_user_and_auth(user_id)` (or `require_auth(user_id)` via
  the combined helper in `api/blueprints/helpers.py`) and return `401 AUTH_REQUIRED`
  when no matching session exists.
- Session cookies are hardened via `SESSION_COOKIE_SECURE`/`SESSION_COOKIE_SAMESITE`/`SESSION_COOKIE_HTTPONLY` (`api/routes.py`, `config.py`).
- CSRF: a per-session token is stored in the cookie (`get_csrf_token` in helpers). `api/routes.py:before_request` rejects state-changing requests that carry an active session but the wrong `X-CSRF-Token` header (`403 CSRF_FAILED`). Pre-auth endpoints (`/api/auth/login`, `/api/user/create`) are exempt. The dashboard sends the header automatically from the token exposed by `/api/auth/me` and the login response.

### Persistence

- [api/mongo_store.py](api/mongo_store.py) handles MongoDB connectivity.
- Falls back to in-memory behavior if MongoDB is unavailable.
- TTL indexes are created on `meals.timestamp`, `daily_logs.updated_at`, plus
  `activity_logs`, `sleep_logs`, and `chat_history` retention from
  `MONGO_*_TTL_DAYS`.
- Chat history persistence: `MongoStore.save_chat_history` /
  `get_chat_history` / `delete_chat_history`.

## Endpoints Overview

Primary route groups:

- Auth: login, logout, me
- User: create, fetch profile, set password, delete (with cascade + export)
- Nutrition: log meal, analysis, macro recommendations, meal recommendations (all require a login session)
- Schedule: optimize tasks, available slots, schedule history (session required)
- Productivity: predict focus, optimal study time, saved productivity sessions (session required)
- Activity: recommendations, log activity, activity logs, trend analysis (session required)
- Sleep: log sleep, sleep logs, sleep-quality prediction
- Insights: health risks, recovery readiness, goal progress, weekly digest
- Chatbot and insights (chatbot requires a login session)
- External data: food, exercise, weather (rate-limited per client IP)
- Trends: calories/macros/focus trend series
- Comparative analytics: week-over-week deltas with explanations
- Health and metrics: liveness, readiness, dependency metrics, model metrics

For the endpoint implementation, see the blueprint files under
[api/blueprints](api/blueprints).

## Validation and Testing

- API health endpoint: [http://localhost:5001/api/health](http://localhost:5001/api/health)
- Unit tests:

```powershell
python -m pytest tests/ -v
```

- Time-based external integrations (rate limiter, TTL caches) are tested deterministically with small windows.
- AI module evaluation data lives under [data/](data) (`training_data.csv`, `eval.csv`); they power the quantitative `ProductivityPredictor` tests.

