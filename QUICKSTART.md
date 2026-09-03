# Quick Start

Use this guide to run the latest version of the project (backend + frontend dashboard).

## Run With Docker (Recommended)

Start app + MongoDB:

  docker compose up --build -d

View logs:

  docker compose logs -f app

Stop containers:

  docker compose down

Stop and remove MongoDB volume:

  docker compose down -v

---

## 1) Install (Manual/Python)

  cd `<path-to-Health-Tracker-Agent>`
  python -m venv venv

# On Windows:

  .\venv\Scripts\activate

# On macOS/Linux:

  source venv/bin/activate
  pip install -r requirements.txt

If you already have `venv`, just activate it and run `pip install -r requirements.txt`.

### Configure environment

  Copy-Item .env.example .env   # Windows PowerShell

Edit `.env` and set `SECRET_KEY` (used to sign session cookies). MongoDB, TTL, and external API keys are optional — see `.env.example`.

## 2) Start MongoDB (Recommended)

Make sure MongoDB is running locally before starting the API.

Default connection used by the app (override in `.env`):

- `MONGO_URI=mongodb://localhost:27017`
- `MONGO_DB_NAME=health_tracker`

## **3) Start Server**

  python main.py

Server default: `http://localhost:5001`

## 4) Open App

- Frontend dashboard: `http://localhost:5001/`
- Health check: `http://localhost:5001/api/health`

## 5) Quick Demo Flow

1. Create user from **User** tab — set a **password** when creating.
2. Log in via the **Session Login** form (same tab).
3. Switch to **Nutrition** tab, log one meal (requires the session).
4. Run nutrition analysis and macro recommendations.
5. Switch to **Schedule** tab, add tasks and optimize; view schedule history.
6. Run productivity prediction; view saved productivity sessions.
7. **Activity** tab: log an activity, then view logs and trends.
8. Switch to **Chatbot** tab, send one message (requires the session).
9. View **Trends** tab for charts (updates as you log data).
10. Show final evaluation metrics relative absolute error (RAE).

## 6) Useful Commands

Run tests:

  python -m unittest discover -s tests -p "test_*.py" -v

Retrain the productivity model (supports incremental updates):

  python models/train_model.py --save            # train + evaluate + persist
  python models/train_model.py --incremental     # merge new rows into saved model

## Notes

- Nutrition logging/analysis and the chatbot require a login session (`POST /api/auth/login`). Passwords are hashed and never returned by the API.
- User profiles, daily meal logs, schedules, productivity sessions, and activity logs are persisted in MongoDB when available.
- If MongoDB is unavailable, the app falls back to in-memory storage.
- External API lookups (weather/food/exercise) use in-memory TTL caching and are rate-limited per client IP.
- API errors return a consistent envelope: `{"error": "...", "code": "..."}`.
- Frontend includes Chart.js trend charts and row-based Task Builder.
- Frontend disables controls during requests and shows clearer inline error banners.
- Schedule optimize accepts both task styles:
  - `title` + `duration_minutes` + `deadline_days`
  - `name` + `duration_min` + `deadline`

## Troubleshooting

### PowerShell execution policy issue

# Only needed on Windows PowerShell:

  Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

### Port already in use

# On Windows:

  $env:PORT=5002
  python main.py

# On macOS/Linux:

  export PORT=5002
  python main.py

### Import or dependency errors

  pip install -r requirements.txt

### Docker startup delays

`docker-compose.yml` includes healthchecks and startup ordering; wait until both services are healthy:

  docker compose ps
