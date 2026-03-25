# Quick Start Guide

## One-Line Setup

```bash
pip install -r requirements.txt && python examples.py
```

## What You Get

### ✅ Data Models (7 classes)

- `UserProfile` - Complete user health profile with BMR/TDEE calculations
- `StudySession` - Track study efficiency and focus
- `ScheduledActivity` - Manage calendar events
- `Meal` - Log meals with nutritional data
- `NutritionInfo` - Nutritional information (macros, calories)
- `FoodItem` - Food database entries
- `DailyNutritionLog` - Daily nutrition summaries

### 🤖 AI Modules (6 implementations)

1. **Knowledge Base** - Rule-based inference with 7 health rules

   ```python
   kb = KnowledgeBase(user)
   kb.add_facts({"daily_calories": 2500, "energy_level": 5})
   recommendations = kb.get_top_recommendations()
   ```
2. **Schedule Optimizer** - CSP solver for optimal scheduling

   ```python
   optimizer = ScheduleOptimizer()
   schedule = optimizer.optimize_schedule(tasks, num_trials=100)
   ```
3. **Productivity Predictor** - ML model for focus prediction

   ```python
   predictor = ProductivityPredictor()
   focus = predictor.predict(features)
   optimal_hour = predictor.suggest_optimal_time()[0]
   ```
4. **Nutrition Analyzer** - Pattern recognition & correlation

   ```python
   analyzer = NutritionAnalyzer(target_nutrition)
   analyzer.add_daily_log(log)
   correlations = analyzer.correlate_nutrition_performance(scores)
   ```
5. **Meal Recommender** - Content-based filtering

   ```python
   recommender = MealRecommendationEngine(user, foods)
   meals = recommender.get_constraint_based_recommendations()
   ```
6. **Activity Recommender** - Timing optimization

   ```python
   activity_rec = ActivityRecommendationEngine(user)
   activity_rec.add_productivity_data(hour=10, focus=8, energy=7)
   times = activity_rec.recommend_study_times()
   ```

### 🌐 REST API (12+ Endpoints)

```
POST   /api/user/create                           - Create user
GET    /api/user/<id>                             - Get profile
GET    /api/insights/<id>                         - Health insights
POST   /api/nutrition/log-meal                    - Log meal
GET    /api/nutrition/analysis/<id>               - Nutrition report
GET    /api/nutrition/recommendations/<id>        - Macro advice
GET    /api/schedule/available-slots/<id>         - Free time slots
POST   /api/schedule/optimize/<id>                - Optimize schedule
POST   /api/productivity/predict/<id>             - Predict focus
GET    /api/productivity/optimal-time/<id>        - Best study time
POST   /api/recommendations/<id>                  - AI recommendations
GET    /api/health                                - Health check
```

### 🧪 Tests (23+ Cases)

```bash
python -m pytest tests/test_ai_modules.py -v
```

### 📚 Examples (6 Scenarios)

```bash
python examples.py
```

## File Structure

```
Health-Agent/
├── models/              # Data models
├── ai_modules/          # AI implementations
├── api/                 # Flask REST API
├── data/                # Sample foods & utilities
├── tests/               # Unit tests
├── main.py              # Start server
├── examples.py          # Usage examples
├── requirements.txt     # Dependencies
├── README.md            # Project overview
└── IMPLEMENTATION.md    # Technical details
```

## Run Options

**Option 1: Run Examples**

```bash
python examples.py
```

Shows all features in action:

- User creation
- Productivity prediction
- Schedule optimization
- Nutrition analysis
- Meal recommendations
- AI inference

**Option 2: Start API Server**

```bash
python main.py
```

Server at http://localhost:5000

- Make REST calls with curl
- Integrate with other apps
- Postman/Insomnia compatible

**Option 3: Run Tests**

```bash
python tests/test_ai_modules.py
```

23+ test cases covering:

- Data model calculations
- AI algorithm correctness
- End-to-end workflows

## Key Features Demonstrated

### 🎓 Study Optimization

- Predict focus score for any time/condition
- Suggest optimal study times
- Estimate ideal session duration
- Optimize weekly schedule

### 🥗 Nutrition Tracking

- Log meals with macros
- Track adherence to targets
- Identify eating patterns
- Detect nutritional anomalies
- Correlate nutrition with performance

### ⏰ Time Management

- Find available time slots
- Optimize task scheduling
- Handle constraints
- Prioritize by deadline & difficulty

### 🧠 AI Intelligence

- Rule-based reasoning with 7 rules
- Machine learning (linear/nonlinear)
- Pattern recognition
- Constraint satisfaction solving
- Correlation analysis

### 📊 Analytics

- Weekly/daily reports
- Adherence metrics
- Effectiveness scoring
- Pattern identification
- Statistical correlations

## Sample Output

```
=== Productivity Prediction ===
Morning Study (Tue 10:00):
  Predicted Focus: 9/10
  Recommended Duration: 65 minutes

Evening Study (Fri 20:00):
  Predicted Focus: 5/10  
  Recommended Duration: 40 minutes

=== Optimized Schedule ===
1. Programming Project (150 min) → Wednesday 10:00-12:30
2. Data Structures (120 min) → Monday 10:00-12:00
3. Linear Algebra (90 min) → Tuesday 14:00-15:30
4. Reading (60 min) → Thursday 16:00-17:00

=== Nutrition Analysis ===
Weekly Average: 2400 cal | 150g protein | 250g carbs | 65g fat
Adherence Rate: 78%
Macro Balance: Balanced
Top Meals: Chicken Bowl, Brown Rice, Salads

=== AI Recommendations ===
1. ✓ Reduce calorie intake (currently 2500 vs 2400 target)
2. ✓ Increase protein (140g vs 150g target)
3. ✓ Extend study sessions during high-energy periods
```

## Next Steps

1. **Quick Test**: `python examples.py`
2. **Try API**: `python main.py` then use curl
3. **Review Code**: Check `IMPLEMENTATION.md`
4. **Run Tests**: `python tests/test_ai_modules.py`
5. **Extend**: Add rules, modify algorithms, integrate data

## Troubleshooting

**Import Error?**

```bash
pip install -r requirements.txt
```

**Port 5000 in use?**
Edit `main.py` line 122: `app.run(port=5001)`

**Tests failing?**
Ensure all imports work: `python -c "from ai_modules import *"`

## Tech Stack

- **Language**: Python 3.10+
- **API**: Flask
- **ML**: Custom implementations (no TensorFlow/PyTorch)
- **Database Ready**: SQLite/PostgreSQL compatible
- **Tests**: unittest + pytest compatible

## Project Stats

- 🤖 **6 AI modules** implemented
- 📊 **6 evaluation metrics**
- 🧪 **23+ test cases**
- 📡 **12+ API endpoints**
- 🎯 **Track B compliant** (custom AI, not APIs)

---

🚀 **Ready to use! Start with `python examples.py`**
