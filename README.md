# AI Health & Wellness Tracker

AI Health & Wellness Tracker is a Flask-based project that combines nutrition tracking, study schedule optimization, productivity prediction, and rule-based wellness recommendations. It includes a REST API and a built-in frontend dashboard.

## What Is Included

- Flask backend API with user, nutrition, schedule, productivity, chatbot, and external API routes
- Built-in frontend at `/` (served by Flask)
- Live trend charts (Chart.js) for calories, macros, and focus score
- Task Builder UI for schedule optimization (no raw JSON needed)
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
|   `-- external_apis.py
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

## Frontend Dashboard

The frontend is served by Flask and includes:

- User creation and profile fetch
- Meal logging and nutrition analysis
- Macro recommendations and meal recommendations
- Schedule optimization with row-based Task Builder
- Productivity prediction and optimal time suggestion
- Health chatbot and session reset
- Knowledge base recommendations and health insights
- Trend charts:
  - Calories trend
  - Macros trend (protein, carbs, fat)
  - Focus trend

## API Endpoints

### User

- `POST /api/user/create`
- `GET /api/user/<user_id>`

### Nutrition

- `POST /api/nutrition/log-meal/<user_id>`
- `GET /api/nutrition/analysis/<user_id>`
- `GET /api/nutrition/recommendations/<user_id>`
- `GET /api/nutrition/meal-recommendations/<user_id>`

### Schedule

- `POST /api/schedule/optimize/<user_id>`
- `GET /api/schedule/available-slots/<user_id>`

### Productivity

- `POST /api/productivity/predict/<user_id>`
- `GET /api/productivity/optimal-time/<user_id>`

### Recommendations and Insights

- `POST /api/recommendations/<user_id>`
- `GET /api/insights/<user_id>`

### Chatbot

- `POST /api/chat/<user_id>`
- `POST /api/chat/<user_id>/reset`

### External Data

- `GET /api/food/search?q=<term>&limit=<n>`
- `GET /api/food/barcode/<barcode>`
- `POST /api/food/log-text/<user_id>`
- `GET /api/exercise/search?q=<term>`
- `GET /api/exercisedb/search?q=<term>`
- `GET /api/wger/<endpoint>`
- `GET /api/weather/context?lat=<lat>&lon=<lon>`

### System

- `GET /api/health`

## Task Payload Compatibility

Schedule optimization now accepts both shapes below (backend normalizes automatically):

1. Frontend-style tasks:

```json
{
  "title": "Essay Draft",
  "duration_minutes": 60,
  "difficulty": 6,
  "deadline_days": 2
}
```

1. Optimizer-style tasks:

```json
{
  "name": "Essay Draft",
  "duration_min": 60,
  "difficulty": 6,
  "deadline": "2030-01-01T10:00:00"
}
```

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

- Data is currently stored in-memory while the server is running.
- Restarting the server resets users, logs, and sessions.
- Food database is loaded from `dataset_loader_v2` during startup.
