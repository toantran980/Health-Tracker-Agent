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

- Frontend: <http://localhost:5001/>
- Health check: <http://localhost:5001/api/health>

Stop:

```powershell
docker compose down
```

## Project Structure

Key files and folders:

- [main.py](main.py): app entry point
- [api/routes.py](api/routes.py): Flask app + blueprint registration
- [api/blueprints](api/blueprints): domain route modules and shared helpers/state
- [api/external_apis.py](api/external_apis.py): external API wrappers
- [api/mongo_store.py](api/mongo_store.py): MongoDB persistence helper
- [ai_modules](ai_modules): recommendation, prediction, and rule engines
- [models](models): user, meal, and activity models
- [data](data): food dataset loading utilities
- [templates/index.html](templates/index.html): frontend page
- [static/app.js](static/app.js): frontend logic
- [static/styles.css](static/styles.css): frontend styling
- [tests/test_ai_modules.py](tests/test_ai_modules.py): AI module tests

## Core Components

## API Layer

- Flask routes are split by domain under [api/blueprints](api/blueprints).
- In-memory caches are used for live runtime objects.
- When MongoDB is available, users and daily meal logs are persisted and rehydrated.
- Error responses are standardized as `{"error": "...", "code": "..."}`.
- External API wrappers include lightweight TTL caching (USDA, Open Food Facts, Wger, Open-Meteo).
- **Removed:** Nutritionix NLP (required paid keys); use food search instead.

### AI Modules

- [ai_modules/knowledge_base.py](ai_modules/knowledge_base.py): rule-based recommendations.
- [ai_modules/scheduler_optimizer.py](ai_modules/scheduler_optimizer.py): schedule optimization.
- [ai_modules/productivity_predictor.py](ai_modules/productivity_predictor.py): focus score prediction (now uses Random Forest via scikit-learn for best results).
- [ai_modules/nutrition_analyzer.py](ai_modules/nutrition_analyzer.py): nutrition trends and adherence.
- [ai_modules/recommendation_engine.py](ai_modules/recommendation_engine.py): meal recommendations.

### Persistence

- [api/mongo_store.py](api/mongo_store.py) handles MongoDB connectivity.
- Uses environment variables:
  - MONGO_URI
  - MONGO_DB_NAME
- Falls back to in-memory behavior if MongoDB is unavailable.

## Endpoints Overview

Primary route groups:

- User: create and fetch profile
- Nutrition: log meal, analysis, macro recommendations, meal recommendations
- Schedule: optimize tasks, available slots
- Productivity: predict focus, optimal study time
- Chatbot and insights
- External data: food, exercise, weather
- Health: liveness and service status

For exact endpoint list, see [README.md](README.md).

## Validation and Testing

- API health endpoint: <http://localhost:5001/api/health>
- Unit tests:

```powershell
python -m unittest tests/test_ai_modules.py -v
```

## Notes

- This file is intentionally concise.
- Operational commands are maintained in [QUICKSTART.md](QUICKSTART.md).
- High-level feature and endpoint documentation is in [README.md](README.md).
- Docker startup is hardened with service healthchecks and Mongo connection retries.
