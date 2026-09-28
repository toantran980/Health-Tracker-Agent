# AI Health & Wellness Tracker

## Contributions & Project History

**Original Project Contributors:**

- Toan Tran
- Chris Ramon
- Shaik Amin

**Current Maintainer:**

Toan Tran independently completed all commits, updates, and expansions after May 15, 2026.

AI Health & Wellness Tracker is a Flask-based project combining nutrition tracking, personalized meal and activity recommendations, study schedule optimization, productivity prediction, behavioral pattern analysis, and rule-based wellness recommendations. It includes a REST API, a built-in frontend dashboard, and a suite of trained machine-learning models for sleep quality, recovery readiness, productivity, and activity recognition.

## Current Status

- **Tests:** 132 unit and integration tests passing (`pytest`)
- **Training scripts:** `sleep`, `recovery`, and `activity-classifier` models trainable from bundled public datasets
- **Safety boundaries:** wellness guidance labeled as non-diagnostic, with escalation language for concerning symptoms
- **Roadmap:** Phase 1 (foundation, privacy, observability, release process) and comparative analytics complete; Phase 3 (module-specific trained models, external datasets, safety boundaries) largely complete. See [TODO.md](TODO.md).

## What Is Included

- Flask backend API split by domain blueprints (auth, user, nutrition, schedule, activity, chat, external, health, metrics, trends, sleep, comparative analytics)
- Session-based authentication (login/logout) with password hashing; nutrition, chat, and activity endpoints are protected
- CSRF protection for state-changing requests (token echoed via `X-CSRF-Token` header; dashboard handles it automatically)
- Session cookie hardening flags (`SESSION_COOKIE_SECURE`, `SameSite`, `HttpOnly`) and optional session TTL with sliding refresh
- Built-in frontend dashboard with tab-based section navigation
- Live trend charts (Chart.js) for calories, macros, and focus score
- Task Builder UI for schedule optimization (no raw JSON needed)
- Standardized API error envelope: `{"error": "...", "code": "..."}` and per-client rate limiting for external API routes (in-memory or Redis backend)
- TTL caching for external food/exercise lookups
- Persistence for schedules, productivity sessions, activity logs, sleep logs, meals, daily logs, and chat history (MongoDB, with in-memory fallback)
- MongoDB TTL indexes keep `meals`, `daily_logs`, `activity_logs`, `sleep_logs`, and `chat_history` collections bounded
- Docker healthchecks + MongoDB connection retry on startup
- Privacy controls: account deletion, structured data export, documented retention (see [PRIVACY.md](PRIVACY.md))
- AI modules:
  - **Rule-based:** `KnowledgeBase`, `BehavioralAnalyzer`, `ScheduleOptimizer` (CSP + heuristics), `NutritionAnalyzer`, `MealRecommendationEngine`, `ActivityRecommendationEngine`, `HealthRiskAssessor`, `GoalTracker`, `WeeklyDigestGenerator`, keyless `HealthChatbot`
  - **Machine learning:** `ProductivityPredictor`, `SleepQualityPredictor`, `RecoveryPredictor` (random forest regressors), `ActivityClassifier` (random forest classifier)

## Tech Stack

- Python 3.10+ (the Dockerfile and CI run Python 3.14)
- Flask, scikit-learn, XGBoost, pandas, and NumPy
- PyMongo + MongoDB, python-dotenv, requests, kagglehub
- Groq (optional hosted chatbot provider)
- Gunicorn + Nginx (production deployment)
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
- Sleep logging, history, and sleep-quality prediction
- Health chatbot and session reset (session required)
- Knowledge base recommendations and health insights
- Rule-based health-risk warnings, recovery readiness, goal progress, and weekly multi-domain digest
- Week-over-week comparative analytics with explanations
- Loading states and disabled controls during API calls
- Inline status banner for clearer API errors
- Trend charts:

  - Calories trend
  - Macros trend (protein, carbs, fat)
  - Focus trend

For authentication, endpoint details, and request behavior, see
[IMPLEMENTATION.md](IMPLEMENTATION.md).

## Machine Learning Models

The tracker ships four trainable models in `ai_modules/`, produced by the
training scripts in `models/`. Trained artifacts are gitignored and written to
`data/*.pkl`; predictors fall back to synthetic bootstrap data when a model
file is absent, so the app runs without them. See [MODELS.md](MODELS.md) for
datasets, training commands, and evaluation notes.

| Model | Predictor | Type | Training script | Dataset |
| ----- | --------- | ---- | --------------- | ------- |
| Productivity | `ProductivityPredictor` | Random forest regressor | `models/train_model.py` | `data/eval.csv` |
| Sleep quality | `SleepQualityPredictor` | Random forest regressor | `models/train_sleep_model.py` | Sleep Health and Lifestyle |
| Recovery readiness | `RecoveryPredictor` | Random forest regressor | `models/train_recovery_model.py` | FitBit wearable data |
| Activity recognition | `ActivityClassifier` | Random forest classifier | `models/train_activity_classifier.py` | UCI Human Activity Recognition |

## Run Tests

```powershell
python -m pytest tests/ -v
```

The suite covers auth, CSRF, session expiry, persistence, rate limiting,
safety boundaries, rule engines, ML predictors, and comparative analytics.

## Continuous Integration

CI (`.github/workflows/ci.yml`) runs on every push and pull request:

- Ruff linting
- `pip-audit` dependency/security scan
- `py_compile` compile check
- `scripts/migration_check.py` schema readiness
- Full `pytest` suite

## More Documentation

- [MODELS.md](MODELS.md): ML model design, datasets, training commands, fallback behavior
- [QUICKSTART.md](QUICKSTART.md): demo flow, model commands, and troubleshooting
- [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md): reverse-proxy HTTPS, Gunicorn, and secrets setup
- [IMPLEMENTATION.md](IMPLEMENTATION.md): architecture, security, persistence, and API behavior
- [CONFIGURATION.md](CONFIGURATION.md): environment variables and deployment settings
- [PRIVACY.md](PRIVACY.md): health-data privacy policy, retention, and user rights
- [TODO.md](TODO.md): active roadmap and completed work
- [SPARK_IDEAS.md](SPARK_IDEAS.md): future feature ideas

## References

### Data sources

- [Nutrition Details for Most Common Foods](https://www.kaggle.com/datasets/niharika41298/nutrition-details-for-most-common-foods)
- [USDA FoodData Central datasets](https://fdc.nal.usda.gov/download-datasets)
- [Open Food Facts](https://world.openfoodfacts.org)

### Modeling datasets

- [Sleep Health and Lifestyle Dataset](https://www.kaggle.com/datasets/uom190346a/sleep-health-and-lifestyle-dataset)
- [FitBit Fitness Tracker Data](https://www.kaggle.com/datasets/arashnic/fitbit)
- [Human Activity Recognition with Smartphones](https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones)
- [Kaggle mirror](https://www.kaggle.com/datasets/uciml/human-activity-recognition-with-smartphones)

### Optional future datasets

- [PAMAP2 Physical Activity Monitoring](https://archive.ics.uci.edu/dataset/231/pamap2+physical+activity+monitoring)