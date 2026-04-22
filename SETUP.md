# Setup Guide

This guide reflects the current project state (Flask API + built-in frontend dashboard).

## Prerequisites

- Python 3.10+
- pip
- PowerShell (Windows)

## Install

1. Open PowerShell at the project root.
1. Create and activate virtual environment.
1. Install requirements.

```powershell
cd <path-to-Health-Tracker-Agent>
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

Default address: `http://localhost:5001`

## Open in Browser

- Frontend: `http://localhost:5001/`
- Health endpoint: `http://localhost:5001/api/health`

## Run Tests

```powershell
python -m unittest tests/test_ai_modules.py -v
```

## Main Endpoints

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

### Chat and Insights

- `POST /api/chat/<user_id>`
- `POST /api/chat/<user_id>/reset`
- `GET /api/insights/<user_id>`
- `POST /api/recommendations/<user_id>`

### External APIs

- `GET /api/food/search`
- `GET /api/food/barcode/<barcode>`
- `POST /api/food/log-text/<user_id>`
- `GET /api/exercise/search`
- `GET /api/exercisedb/search`
- `GET /api/wger/<endpoint>`
- `GET /api/weather/context`

## Optional .env Keys

External features depend on API keys in `.env` (for example Nutritionix, USDA, RapidAPI). Core features run without them.

## Troubleshooting

### Execution policy issue on PowerShell

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

### Port already in use

Set a different port before run:

```powershell
$env:PORT=5002
python main.py
```

### Import or dependency errors

```powershell
pip install -r requirements.txt
```

## Notes

- In-memory stores are used currently; restarting clears runtime data.
- Food database is loaded at startup from `data/dataset_loader_v2.py`.
