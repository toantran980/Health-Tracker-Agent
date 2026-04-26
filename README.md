# AI Health & Wellness Tracker

AI Health & Wellness Tracker is a Flask-based project that combines nutrition tracking, study schedule optimization, productivity prediction, and rule-based wellness recommendations. It includes a REST API and a built-in frontend dashboard.

## What Is Included

- Flask backend API split by domain blueprints (user, nutrition, schedule, chat, external, health)
- Built-in frontend dashboard with tab-based section navigation
- Live trend charts (Chart.js) for calories, macros, and focus score
- Task Builder UI for schedule optimization (no raw JSON needed)
- Standardized API error envelope: `{"error": "...", "code": "..."}`
- TTL caching for external weather/food/exercise lookups
- Docker healthchecks + MongoDB connection retry on startup
- AI modules:
  - `KnowledgeBase` (rule-based recommendations)
  - `ScheduleOptimizer` (CSP + heuristics)
  - `ProductivityPredictor` (focus score + session duration)
  - `NutritionAnalyzer`
  - `MealRecommendationEngine`

## Tech Stack

- Python 3.10+
- Flask
- scikit-learn, xgboost, pandas, numpy
- Chart.js (frontend charts)

## Project Structure

```text
Health-Tracker-Agent/
|-- main.py
|-- requirements.txt
|-- README.md
|-- api/
|   |-- routes.py
|   |-- external_apis.py
|   |-- mongo_store.py
|   `-- blueprints/
|-- ai_modules/
|-- models/
|-- data/
|-- templates/
|   `-- index.html
|-- static/
|   |-- app.js
|   `-- styles.css
`-- tests/
    `-- test_ai_modules.py
```

## Setup (Windows PowerShell)

1. Open PowerShell in the project root.
1. Create a virtual environment (optional if you already have one):

```powershell
python -m venv venv
```

1. Activate virtual environment:

```powershell
.\venv\Scripts\Activate.ps1
```

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

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

This repository includes `Dockerfile` and `docker-compose.yml` for running the app with MongoDB.

```powershell
docker compose up --build -d
```

Then open `http://localhost:5001/`.

## Frontend Dashboard

The frontend is served by Flask and includes:

- User creation and profile fetch
- Meal logging and nutrition analysis
- Macro recommendations and meal recommendations
- Schedule optimization with row-based Task Builder
- Productivity prediction and optimal time suggestion
- Health chatbot and session reset
- Knowledge base recommendations and health insights
- Loading states and disabled controls during API calls
- Inline status banner for clearer API errors
- Trend charts:
  - Calories trend
  - Macros trend (protein, carbs, fat)
  - Focus trend

## API Endpoints

Main endpoint groups:

- User profile management
- Nutrition logging, analysis, and meal recommendations
- Schedule optimization
- Productivity prediction
- Recommendations and insights
- Chatbot interactions
- External food, exercise, and weather data
- System health checks

For implementation details and route behavior, see [IMPLEMENTATION.md](IMPLEMENTATION.md).

## Task Payload Compatibility

Schedule optimization accepts both frontend-style and optimizer-style task payloads.
See [QUICKSTART.md](QUICKSTART.md) for usage flow.

## Run Tests

```powershell
python -m unittest tests/test_ai_modules.py -v
```

## Environment Variables (Optional)

Some external API features require keys in `.env`:

- Nutritionix (NLP meal parsing)
- USDA (food search)
- ExerciseDB / RapidAPI

Core local features still run without these keys.

## Notes

- User profiles and daily meal logs are persisted in MongoDB when available.
- If MongoDB is unavailable, the app falls back to in-memory storage.
- Food database is loaded from `dataset_loader_v2` during startup.
- External API responses are cached in-memory with short TTLs to reduce latency.
