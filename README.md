## Contributions & Project History

**Original Project:**
* Toan Tran - ttran8276@csu.fullerton.edu
* Chris Ramon - chrisramon1@csu.fullerton.edu
* Shaik Amin - smamin@csu.fullerton.edu
  
**Solo Updates (Post-Graduation):** All commits and updates after May 15, 2026 were completed independently by me for skill development.

# AI Health & Wellness Tracker

AI Health & Wellness Tracker is a Flask-based project that combines nutrition tracking, personalized meal and activity recommendations, study schedule optimization, productivity prediction, behavioral pattern analysis, and rule-based wellness recommendations. It includes a REST API and a built-in frontend dashboard for interactive health and productivity management.

## What Is Included

- Flask backend API split by domain blueprints (auth, user, nutrition, schedule, activity, chat, external, health, metrics)
- Session-based authentication (login/logout) with password hashing; nutrition and chat endpoints are protected
- CSRF protection for state-changing requests (token echoed via `X-CSRF-Token` header; dashboard handles it automatically)
- Session cookie hardening flags (`SESSION_COOKIE_SECURE`, `SameSite`, `HttpOnly`)
- Built-in frontend dashboard with tab-based section navigation
- Live trend charts (Chart.js) for calories, macros, and focus score
- Task Builder UI for schedule optimization (no raw JSON needed)
- Standardized API error envelope: `{"error": "...", "code": "..."}` and shared rate limiting for external API routes (in-memory or Redis backend)
- TTL caching for external food/exercise lookups
- Persistence for schedules, productivity sessions, activity logs, meals, and daily logs (MongoDB, with in-memory fallback)
- MongoDB TTL indexes keep the meals and daily_logs collections bounded
- Docker healthchecks + MongoDB connection retry on startup
- AI modules:
  - `KnowledgeBase` (rule-based recommendations)
  - `BehavioralAnalyzer` (behavioral pattern analysis)
  - `ScheduleOptimizer` (CSP + heuristics)
  - `ProductivityPredictor` (focus score + session duration, now uses Random Forest via scikit-learn for improved accuracy and RAE metrics, replacing simple linear regression)
  - `NutritionAnalyzer` (statistical analysis and anomaly detection)
  - `MealRecommendationEngine` (personalized content-based and constraint-based meal recommendations)
  - `ActivityRecommendationEngine` (heuristic rule-based activity recommendations)

## Tech Stack

* Python 3.10+ (Dockerfile uses Python 3.12)
* Flask (web framework)
* scikit-learn (Random Forest, ML)
* xgboost (ML)
* pandas (data analysis)
* numpy (numerical computing)
* requests (HTTP requests)
* python-dotenv
* pymongo (MongoDB integration)
* groq (AI/ML - health chatbot)
* Chart.js (frontend charts, via CDN)
* HTML/CSS/JavaScript (frontend, static folder)

## Setup (Windows PowerShell)

1. Open PowerShell in the project root.
2. Create a virtual environment (optional if you already have one):

```powershell
python -m venv venv
```

3. Activate virtual environment:

```powershell
.\venv\Scripts\Activate.ps1
```

4. Install dependencies:

```powershell
pip install -r requirements.txt
```

5. Configure environment variables:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` and set at minimum `SECRET_KEY` (see below). The file is git-ignored and never committed.

### Environment Variables

Secret keys and external API keys come from `.env` (see `.env.example` for the full list):

- `SECRET_KEY` — signs session cookies used by `/api/auth/login`. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"`.
- `MONGO_URI`, `MONGO_DB_NAME` — MongoDB connection; defaults to `mongodb://localhost:27017` / `health_tracker`.
- `MONGO_CONNECT_RETRIES`, `MONGO_CONNECT_RETRY_DELAY` — startup reconnect retry window when MongoDB is unreachable.
- `USDA_API_KEY`, `EXERCISEDB_API_KEY`, `GROQ_API_KEY` — external service keys. Optional; endpoints degrade to built-in data when empty. The chatbot uses a keyless rule-based responder when `GROQ_API_KEY` is empty, and the Groq LLM when it's set.
- `MONGO_MEALS_TTL_DAYS`, `MONGO_DAILY_LOGS_TTL_DAYS` — TTL for the meals/daily_logs collections.
- `EXTERNAL_API_RATE_LIMIT`, `EXTERNAL_API_RATE_WINDOW_SECONDS` — sliding-window rate limit for proxied external endpoints (per client IP). Backend is chosen by `RATE_LIMIT_BACKEND` (`memory` or `redis` + `REDIS_URL`).- `SESSION_COOKIE_SECURE` (set `True` when serving HTTPS), `SESSION_COOKIE_SAMESITE`, `SESSION_COOKIE_HTTPONLY` — session cookie hardening.
- `CSRF_PROTECTION` — enables the `X-CSRF-Token` requirement for state-changing requests on authenticated sessions.

## Run the Project

Start the server:

```powershell
python main.py
```

Open in browser:

- Frontend dashboard: `http://localhost:5001/`
- Health check: `http://localhost:5001/api/health`

Note: the server runs on port `5001` by default.

## Run With Docker

This repository includes `Dockerfile` and `docker-compose.yml` for running the app with MongoDB. Compose wires up MongoDB and supplies the MongoDB connection string for the app — set any extra keys (e.g. `SECRET_KEY`, external API keys) in `.env` before building.

```powershell
docker compose up --build -d
```

Then open `http://localhost:5001/`.

## Authentication (Sessions)

Nutrition logging/analysis and the chatbot require a logged-in session:

1. Create a user with a password (`POST /api/user/create` with a `password` field).
2. Log in via `POST /api/auth/login` (`{ "user_id": ..., "password": ... }`) — the server sets a signed session cookie.
3. Authenticated request: `GET /api/auth/me`, log out with `POST /api/auth/logout`.

Passwords are stored hashed (Werkzeug `generate_password_hash`) and are never returned by API responses. The browser dashboard signs in through the User section's *Session Login* form.

State-changing requests made through the dashboard automatically echo the session's CSRF token via the `X-CSRF-Token` header (`GET /api/auth/me` exposes it); with an active session, requests missing the header are rejected with `403 CSRF_FAILED`. Bare-bones API clients must read the token from `/api/auth/me` (or the login response) and resend it on `POST/PUT/PATCH/DELETE`.

> Note: the login flow uses the same origin as the API. If the dashboard is served separately from the API, enable CORS with credentials on your deployment so the session cookie is preserved.

## Frontend Dashboard

The frontend is served by Flask and includes:

- User creation (with optional password) and profile fetch
- Session login/logout and login status indicator
- Meal logging and nutrition analysis (session required)
- Macro recommendations and meal recommendations
- Schedule optimization with row-based Task Builder, plus schedule history
- Productivity prediction, optimal time suggestion, and saved productivity sessions
- Activity recommendations, activity logging, activity logs view, and trend analysis
- Health chatbot and session reset (session required)
- Knowledge base recommendations and health insights
- Loading states and disabled controls during API calls
- Inline status banner for clearer API errors
- Trend charts:
  - Calories trend
  - Macros trend (protein, carbs, fat)
  - Focus trend

## API Endpoints

Main endpoint groups:

- User profile management (create, get, set password)
- Authentication (login, logout, me)
- Nutrition logging, analysis, and meal recommendations
- Schedule optimization and schedule history
- Productivity prediction and productivity sessions
- Activity recommendations, logging, logs, and trends
- Recommendations and insights
- Chatbot interactions
- External food, exercise, and weather data (rate-limited)
- System health checks and model metrics

For implementation details and route behavior, see [IMPLEMENTATION.md](IMPLEMENTATION.md).

## Task Payload Compatibility

Schedule optimization accepts both frontend-style and optimizer-style task payloads.
See [QUICKSTART.md](QUICKSTART.md) for usage flow.

## Run Tests

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

## Retrain the Productivity Model

`models/train_model.py` trains/evaluates `ProductivityPredictor` and supports incremental updates:

```powershell
python models\train_model.py              # train fresh + evaluate
python models\train_model.py --save       # also persist to data/productivity_model.pkl
python models\train_model.py --incremental --save   # merge new rows into the saved model
```

Run `python models\train_model.py --help` for all options.

## Notes

- User profiles, daily meal logs, schedules, productivity sessions, and activity logs are persisted in MongoDB when available.
- If MongoDB is unavailable, the app falls back to in-memory storage.
- The server starts even when MongoDB is unreachable (after a retry window); meal/daily-log collections gain TTL indexes on connect.
- Food database is loaded from `dataset_loader_v2` during startup.
- External API responses are cached in-memory with short TTLs to reduce latency, and proxied endpoints are rate-limited per client IP (in-memory by default, Redis for multi-worker deployments).
- Session cookie flags and CSRF protection are configurable via `.env` (see `.env.example`).
