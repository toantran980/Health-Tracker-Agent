# Installation & Setup Guide

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

## Installation

### 1. Clone/Download the Project

```bash
cd c:\Users\toant\OneDrive\Desktop\CPSC481-Artificial-Intelligence\Project\Health-Agent
```

### 2. Create Virtual Environment (Optional but Recommended)

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Running the Application

### Option A: Run Flask API Server

```bash
python main.py
```

The server will start at `http://localhost:5000`

### Option B: Run Examples

```bash
python examples.py
```

This demonstrates all key features of the system.

### Option C: Run Unit Tests

```bash
python -m pytest tests/test_ai_modules.py -v
```

Or:

```bash
python tests/test_ai_modules.py
```

## API Endpoints

### User Management

- `POST /api/user/create` - Create new user
- `GET /api/user/<user_id>` - Get user profile

### Insights

- `GET /api/insights/<user_id>` - Get comprehensive health insights

### Nutrition

- `POST /api/nutrition/log-meal` - Log a meal
- `GET /api/nutrition/analysis/<user_id>` - Get nutrition report
- `GET /api/nutrition/recommendations/<user_id>` - Get macro recommendations

### Scheduling

- `GET /api/schedule/available-slots/<user_id>` - Find available study slots
- `POST /api/schedule/optimize/<user_id>` - Optimize weekly schedule

### Productivity

- `POST /api/productivity/predict/<user_id>` - Predict focus score
- `GET /api/productivity/optimal-time/<user_id>` - Get optimal study time

### Recommendations

- `POST /api/recommendations/<user_id>` - Get AI recommendations

### System

- `GET /api/health` - Health check

## Project Structure

```
Health-Agent/
├── models/                    # Data models
│   ├── __init__.py
│   ├── user_profile.py       # User profile & goals
│   ├── activity.py           # Study sessions & activities
│   └── meal.py               # Meals & nutrition info
│
├── ai_modules/               # AI & ML implementations
│   ├── __init__.py
│   ├── knowledge_base.py     # Rule-based reasoning
│   ├── scheduler_optimizer.py # CSP solver
│   ├── productivity_predictor.py # ML model
│   ├── nutrition_analyzer.py  # Pattern analysis
│   └── recommendation_engine.py # Recommendations
│
├── api/                       # Flask API
│   ├── __init__.py
│   └── routes.py             # API endpoints
│
├── data/                      # Data utilities
│   ├── __init__.py
│   └── sample_data.py        # Sample food database
│
├── tests/                     # Unit tests
│   ├── __init__.py
│   └── test_ai_modules.py    # Comprehensive tests
│
├── main.py                    # Application entry point
├── examples.py                # Usage examples
├── requirements.txt           # Dependencies
└── SETUP.md                   # This file
```

## Usage Examples

### 1. Create User

```python
from models.user_profile import UserProfile, Goal

user = UserProfile(
    user_id="user_001",
    name="John Doe",
    age=22,
    weight_kg=75,
    height_cm=180,
    goals=[Goal.ENERGY_OPTIMIZATION, Goal.MUSCLE_GAIN]
)
```

### 2. Predict Study Productivity

```python
from ai_modules import ProductivityPredictor, Features

predictor = ProductivityPredictor()
features = Features(
    hour_of_day=10,
    day_of_week=2,
    sleep_quality=8.0,
    sleep_hours=8.0,
    nutrition_score=80.0,
    energy_level=7,
    previous_session_duration=60,
    task_difficulty=6
)
focus_score = predictor.predict(features)
print(f"Expected Focus: {focus_score}/10")
```

### 3. Optimize Study Schedule

```python
from ai_modules import ScheduleOptimizer
from datetime import datetime, timedelta

optimizer = ScheduleOptimizer()
tasks = [
    {
        "subject": "Math",
        "duration_min": 90,
        "difficulty": 8,
        "deadline": datetime.now() + timedelta(days=2)
    }
]
schedule = optimizer.optimize_schedule(tasks)
```

### 4. Analyze Nutrition

```python
from ai_modules import NutritionAnalyzer
from models.meal import NutritionInfo

target = NutritionInfo(calories=2000, protein_g=150, carbs_g=250, fat_g=65)
analyzer = NutritionAnalyzer(target)
report = analyzer.get_nutrition_report()
```

### 5. Get AI Recommendations

```python
from ai_modules import KnowledgeBase

kb = KnowledgeBase(user)
kb.add_facts({
    "daily_calories": 2500,
    "energy_level": 5,
    "sleep_hours": 6
})
recommendations = kb.get_top_recommendations(n=3)
```

## AI Modules Overview

### Knowledge Base (Rule-based Reasoning)

- Inference engine using forward chaining
- 7+ built-in rules for health optimization
- Extensible rule system
- Confidence scoring for recommendations

### Schedule Optimizer (CSP Solver)

- Constraint Satisfaction Problem solver with backtracking
- Productivity-aware time slot allocation
- Task prioritization (difficulty, deadline, duration)
- Supports scheduling constraints

### Productivity Predictor (ML)

- Linear and non-linear prediction models
- Features: sleep, nutrition, energy, time of day, task difficulty
- Recommended session duration estimation
- Optimal study time suggestions

### Nutrition Analyzer (Pattern Recognition)

- Macro balance analysis
- Adherence tracking
- Anomaly detection
- Meal pattern identification
- Correlation analysis with performance

### Recommendation Engines

- Content-based meal filtering
- Constraint-based meal selection
- Activity timing optimization
- Dietary preference satisfaction

## Evaluation Metrics Implemented

1. **Study Effectiveness Score** = (Focus × Duration × Completion) / 100
2. **Nutrition Adherence Rate** = % of days within ±10% of targets
3. **ML Model Accuracy** = MAE < 1.5, Cross-validation > 75%
4. **Pattern Correlation** = Pearson correlation for lifestyle factors
5. **Schedule Optimization Score** = Based on productivity factors

## Troubleshooting

### Import Errors

Ensure all files are in correct directories and dependencies are installed:

```bash
pip install -r requirements.txt
```

### Flask Port Already in Use

Change port in `main.py`:

```python
app.run(port=5001)  # Use different port
```

### Missing Data

Sample data available in `data/sample_data.py`:

```python
from data.sample_data import SAMPLE_FOODS, create_sample_user
```

## Performance Notes

- CSP solver runs ~50 trials for optimization (configurable)
- ML models use simplified linear regression for speed
- Production deployments should use proper database (not in-memory)
- Scale up sample size for better ML model accuracy

## Future Enhancements

- Database integration (PostgreSQL/MongoDB)
- Real-time data ingestion from wearables
- Computer vision for food recognition
- Advanced NLP for study content analysis
- Mobile app development
- Advanced ensemble ML models
- Real-time notification system

## Contributing

Extend the system by:

1. Adding new rules in `knowledge_base.py`
2. Adding new predictive models in `productivity_predictor.py`
3. Extending schedulers in `scheduler_optimizer.py`
4. Adding new API endpoints in `api/__init__.py`
