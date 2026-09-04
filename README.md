# AI Health & Wellness Tracker

## Contributions & Project History

**Original Project:**
* Toan Tran - ttran8276@csu.fullerton.edu
* Chris Ramon - chrisramon1@csu.fullerton.edu
* Shaik Amin - smamin@csu.fullerton.edu
  
**Solo Updates (Post-Graduation):** All commits and updates after May 15, 2026 were completed independently by me for skill development.

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

- Python 3.10+ (the Dockerfile uses Python 3.14)
- Flask, scikit-learn, XGBoost, pandas, and NumPy
- Requests, python-dotenv, PyMongo, and MongoDB
- Groq (optional hosted chatbot provider)
- Chart.js via CDN
- HTML, CSS, and JavaScript in `templates/` and `static/`

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
python -m pip install -r requirements.txt
```

5. Create the local configuration file:

```powershell
Copy-Item .env.example .env
```

For configuration options, see [CONFIGURATION.md](CONFIGURATION.md) and
[`.env.example`](.env.example).

## Run the Project

Start the server:

```powershell
python main.py
```

Open in browser:

- Frontend dashboard: `http://localhost:5001/`
- Health check: `http://localhost:5001/api/health`

Note: the server runs on port `5001` by default.

## Run with Docker

This repository includes `Dockerfile` and `docker-compose.yml` for running the app with MongoDB. Compose wires up MongoDB and supplies the MongoDB connection string for the app — set any extra keys (e.g. `SECRET_KEY`, external API keys) in `.env` before building.

```powershell
docker compose up --build -d
```

Then open `http://localhost:5001/`.

## Application Areas

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

  For authentication, endpoint details, and request behavior, see
  [IMPLEMENTATION.md](IMPLEMENTATION.md).

## Run Tests

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

## More Documentation

- [QUICKSTART.md](QUICKSTART.md): demo flow, model commands, and troubleshooting
- [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md): reverse-proxy HTTPS, Gunicorn, and secrets setup
- [IMPLEMENTATION.md](IMPLEMENTATION.md): architecture, security, persistence, and API behavior
- [CONFIGURATION.md](CONFIGURATION.md): environment variables and deployment settings
- [TODO.md](TODO.md): active roadmap and completed work
- [SPARK_IDEAS.md](SPARK_IDEAS.md): future feature ideas
