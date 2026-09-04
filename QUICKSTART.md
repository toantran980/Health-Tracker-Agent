# Quick Start

This project runs as a Flask web app with a MongoDB-backed data layer, nutrition/activity tracking, scheduling, AI recommendations, and a frontend dashboard.

## Recommended setup

Use one of these two paths:

1. Local development
2. Docker-based development / deployment

---

## 1) Local development

### 1.1 Create and activate a virtual environment

Windows PowerShell:

```powershell
cd <path-to-Health-Tracker-Agent>
python -m venv venv
.\venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
cd <path-to-Health-Tracker-Agent>
python -m venv venv
source venv/bin/activate
```

### 1.2 Install dependencies

```powershell
pip install -r requirements.txt
```

### 1.3 Configure environment variables

Copy the sample file:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` and set the values you need.

Important notes:

- `SECRET_KEY` is required for signed Flask sessions.
- `MONGO_URI` should normally point to `mongodb://localhost:27017` when running locally.
- `USDA_API_KEY` is optional; if you do not want to request a USDA key, leave it blank and the app will still work using fallback data sources.
- `GROQ_API_KEY`, `EXERCISEDB_API_KEY`, and `USDA_API_KEY` are optional external API keys.

### 1.4 Start MongoDB locally

Make sure MongoDB is running before starting the app.

Typical local connection:

```dotenv
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=health_tracker
```

### 1.5 Run the app

```powershell
python main.py
```

Open:

- Frontend: http://localhost:5001/
- Health check: http://localhost:5001/api/health

---

## 2) Docker development / deployment

This project includes Docker support for the app and MongoDB.

### 2.1 Start the stack

```powershell
docker compose up --build -d
```

### 2.2 View logs

```powershell
docker compose logs -f app
```

### 2.3 Stop the stack

```powershell
docker compose down
```

### 2.4 Remove MongoDB data volume

```powershell
docker compose down -v
```

---

## 3) Production-style environment

For a non-local deployment, use the production template:

```powershell
Copy-Item .env.production.example .env.production
```

Then edit `.env.production` and set:

- a strong `SECRET_KEY`
- production MongoDB connection
- real API keys if needed
- secure cookie settings
- `DEBUG=False`

Then run:

```powershell
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml up --build -d
```

To stop it:

```powershell
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.production.yml down
```

---

## 4) Quick demo flow

1. Open the app and create a user from the User tab.
2. Set a password when creating the account.
3. Log in using the session login form.
4. Go to Nutrition and log one meal.
5. Run nutrition analysis and macro recommendations.
6. Go to Schedule and optimize a task list.
7. Run productivity prediction and review saved sessions.
8. Log an activity in the Activity tab and review trends.
9. Open the Chatbot tab and send a message.
10. Check the Trends tab for generated charts and health insights.

---

## 5) Useful commands

Run the full unit test suite:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Retrain the productivity model:

```powershell
python models/train_model.py --save
```

Incrementally update the saved model:

```powershell
python models/train_model.py --incremental
```

---

## 6) Notes

- Nutrition logging, scheduling endpoints, and chat features require a valid logged-in session.
- Passwords are hashed before storage and are never returned by API responses.
- User, meal, schedule, and activity data are persisted in MongoDB when available.
- If MongoDB is unavailable, the app falls back to in-memory storage.
- External APIs use TTL caching and rate limiting.
- API responses follow a consistent error format: `{ "error": "...", "code": "..." }`.
- The app supports both local host runs and Docker-based runs.

---

## 7) Troubleshooting

### PowerShell execution policy on Windows

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

### Port already in use

If port 5001 is already occupied:

```powershell
$env:PORT=5002
python main.py
```

On macOS/Linux:

```bash
export PORT=5002
python main.py
```

### Dependency/import errors

```powershell
pip install -r requirements.txt
```

### MongoDB connection issues

- Check that MongoDB is running.
- Confirm the `MONGO_URI` in `.env` is correct.
- If running in Docker, use the container service name instead of `localhost`.

### Docker startup delays

Wait for health checks and container readiness:

```powershell
docker compose ps
```

---
