# Quick Start

Use this guide to run the latest version of the project (backend + frontend dashboard).

## 1) Install

```powershell
cd <path-to-Health-Tracker-Agent>
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If you already have `venv`, just activate it and run `pip install -r requirements.txt`.

## 2) Start MongoDB (Recommended)

Make sure MongoDB is running locally before starting the API.

Default connection used by the app:

- `MONGO_URI=mongodb://localhost:27017`
- `MONGO_DB_NAME=health_tracker`

Optional `.env` example:

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=health_tracker
```

## 3) Start Server

```powershell
python main.py
```

Server default: `http://localhost:5001`

## 4) Open App

- Frontend dashboard: `http://localhost:5001/`
- Health check: `http://localhost:5001/api/health`

## 5) Quick Demo Flow

1. Create user from **User** tab.
1. Switch to **Nutrition** tab, log one meal.
1. Run nutrition analysis and macro recommendations.
1. Switch to **Schedule** tab, add tasks and optimize.
1. Run productivity prediction.
1. Switch to **Chatbot** tab, send one message.
1. View **Trends** tab for charts (updates as you log data).

## 6) Useful Commands

Run tests:

```powershell
python -m unittest tests/test_ai_modules.py -v
```

Run examples script:

```powershell
python examples.py
```

## 7) Run With Docker

Start app + MongoDB:

```powershell
docker compose up --build -d
```

View logs:

```powershell
docker compose logs -f app
```

Stop containers:

```powershell
docker compose down
```

Stop and remove MongoDB volume:

```powershell
docker compose down -v
```

## Notes

- User profiles and daily meal logs are persisted in MongoDB when available.
- If MongoDB is unavailable, the app falls back to in-memory storage.
- External API lookups (weather/food/exercise) use in-memory TTL caching.
- API errors now return a consistent envelope: `{"error": "...", "code": "..."}`.
- Frontend includes Chart.js trend charts and row-based Task Builder.
- Frontend disables controls during requests and shows clearer inline error banners.
- Schedule optimize accepts both task styles:
  - `title` + `duration_minutes` + `deadline_days`
  - `name` + `duration_min` + `deadline`

## Troubleshooting

### PowerShell execution policy issue

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

### Port already in use

```powershell
$env:PORT=5002
python main.py
```

### Import or dependency errors

```powershell
pip install -r requirements.txt
```

### Docker startup delays

`docker-compose.yml` includes healthchecks and startup ordering; wait until both services are healthy:

```powershell
docker compose ps
```
