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

## 2) Start Server

```powershell
python main.py
```

Server default: `http://localhost:5001`

## 3) Open App

- Frontend dashboard: `http://localhost:5001/`
- Health check: `http://localhost:5001/api/health`

## 4) Quick Demo Flow

1. Create user from dashboard.
1. Log one meal.
1. Run nutrition analysis and macro recommendations.
1. Add tasks in Task Builder and optimize schedule.
1. Run productivity prediction.
1. Send one chatbot message.

## 5) Useful Commands

Run tests:

```powershell
python -m unittest tests/test_ai_modules.py -v
```

Run examples script:

```powershell
python examples.py
```

## Notes

- Data is in-memory for now (restarts clear users/logs/sessions).
- Frontend includes Chart.js trend charts and row-based Task Builder.
- Schedule optimize accepts both task styles:
  - `title` + `duration_minutes` + `deadline_days`
  - `name` + `duration_min` + `deadline`
