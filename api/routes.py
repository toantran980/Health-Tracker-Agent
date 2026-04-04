"""
routes.py

REST API routes for the Health & Wellness Tracker.
All endpoints return JSON.  Global in-memory dicts act as the data
store; swap for a real DB when ready.
"""

from flask import Flask, Blueprint, request, jsonify
from datetime import datetime
from typing import Dict

from models.user_profile import UserProfile, Goal, BiologicalSex
from models.meal import NutritionInfo, Meal, MealType, FoodItem, DailyNutritionLog
from models.activity import StudySession, ScheduledActivity, ActivityType
from ai_modules import (
    KnowledgeBase,
    ScheduleOptimizer,
    ProductivityPredictor,
    Features,
    NutritionAnalyzer,
    MealRecommendationEngine,
)
from ai_modules.chatbot import HealthChatbot, UserHealthSnapshot
from api.external_apis import (
    search_food_by_name,
    get_food_by_barcode,
    log_natural_language_meal,
    search_exercise,
    get_weather_context,
    search_all_sources,
    food_facts_to_fooditem,
    nutritionix_to_fooditem,
)
from data.dataset_loader import load_kaggle_food_dataset

print("Initializing global food database from Kaggle...")
GLOBAL_FOOD_DB = load_kaggle_food_dataset(limit=2500)

app = Flask(__name__)

# ── In-memory stores (replace with DB in production) ──────────────────────
users:               Dict[str, UserProfile]              = {}
daily_logs:          Dict[str, Dict[str, DailyNutritionLog]] = {}  # user_id -> date_str -> log
knowledge_bases:     Dict[str, KnowledgeBase]            = {}
nutrition_analyzers: Dict[str, NutritionAnalyzer]        = {}
meal_recommenders:   Dict[str, MealRecommendationEngine] = {}
bot_sessions:        Dict[str, HealthChatbot]            = {}


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _get_or_create_daily_log(user_id: str, date_str: str) -> DailyNutritionLog:
    """Return today's DailyNutritionLog, creating it if it doesn't exist yet."""
    user_logs = daily_logs.setdefault(user_id, {})
    if date_str not in user_logs:
        user_logs[date_str] = DailyNutritionLog(
            log_id=f"log_{user_id}_{date_str}",
            user_id=user_id,
            date=datetime.fromisoformat(date_str),
        )
    return user_logs[date_str]


def _require_user(user_id: str):
    """Return (user, None) or (None, error_response)."""
    user = users.get(user_id)
    if not user:
        return None, (jsonify({"error": "User not found"}), 404)
    return user, None


# ═══════════════════════════════════════════════════════════════════════════
# USER PROFILE
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/user/create', methods=['POST'])
def create_user():
    """
    Create a new user profile and initialise all AI modules.

    Body (JSON):
        user_id, name, age, weight_kg, height_cm, biological_sex,
        goals, target_calories, target_protein_g, target_carbs_g, target_fat_g
    """
    data    = request.json or {}
    user_id = data.get('user_id', f"user_{len(users) + 1}")

    sex_str = data.get('biological_sex', 'male').lower()
    bio_sex = BiologicalSex.FEMALE if sex_str == 'female' else BiologicalSex.MALE

    user = UserProfile(
        user_id        = user_id,
        name           = data.get('name', 'Unknown'),
        age            = data.get('age', 25),
        weight_kg      = data.get('weight_kg', 70),
        height_cm      = data.get('height_cm', 175),
        biological_sex = bio_sex,
        goals          = [Goal(g) for g in data.get('goals', ['general_wellness'])],
        target_calories  = data.get('target_calories',  2000),
        target_protein_g = data.get('target_protein_g', 150.0),
        target_carbs_g   = data.get('target_carbs_g',   200.0),
        target_fat_g     = data.get('target_fat_g',     65.0),
    )

    users[user_id] = user

    # Initialise AI modules
    target_nutrition = NutritionInfo(
        calories  = user.target_calories,
        protein_g = user.target_protein_g,
        carbs_g   = user.target_carbs_g,
        fat_g     = user.target_fat_g,
    )
    knowledge_bases[user_id]     = KnowledgeBase(user)
    nutrition_analyzers[user_id] = NutritionAnalyzer(target_nutrition)
    meal_recommenders[user_id]   = MealRecommendationEngine(user, GLOBAL_FOOD_DB)

    return jsonify({"status": "success", "user": user.to_dict()}), 201


@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """Return a user profile by ID."""
    user, err = _require_user(user_id)
    if err:
        return err
    return jsonify(user.to_dict()), 200


# ═══════════════════════════════════════════════════════════════════════════
# NUTRITION — MEAL LOGGING
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/nutrition/log-meal/<user_id>', methods=['POST'])
def log_meal(user_id):
    """
    Log a meal for a user and attach it to today's DailyNutritionLog.
    Also feeds the log into NutritionAnalyzer so analysis stays current.

    Body (JSON):
        meal_type   : "breakfast" | "lunch" | "dinner" | "snack"
        timestamp   : ISO-8601 string (optional, defaults to now)
        notes       : free text (optional)
        food_items  : list of {name, calories, protein_g, carbs_g, fat_g}
    """
    user, err = _require_user(user_id)
    if err:
        return err

    data = request.json or {}

    # ── Parse food items from request ───────────────────────────────────
    raw_items  = data.get('food_items', [])
    food_items = []
    for item in raw_items:
        food_items.append(FoodItem(
            food_id  = f"manual_{datetime.now().timestamp()}",
            name     = item.get('name', 'Unknown food'),
            nutrition_info = NutritionInfo(
                calories  = item.get('calories',  0),
                protein_g = item.get('protein_g', 0),
                carbs_g   = item.get('carbs_g',   0),
                fat_g     = item.get('fat_g',     0),
            ),
        ))

    # ── Build Meal object ────────────────────────────────────────────────
    ts = datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat()))
    meal = Meal(
        meal_id    = f"meal_{datetime.now().timestamp()}",
        user_id    = user_id,
        meal_type  = MealType(data.get('meal_type', 'lunch')),
        timestamp  = ts,
        food_items = food_items,
        notes      = data.get('notes', ''),
    )

    # ── Attach to today's DailyNutritionLog ─────────────────────────────
    date_str  = ts.date().isoformat()
    daily_log = _get_or_create_daily_log(user_id, date_str)
    daily_log.meals.append(meal)

    # ── Feed updated log into NutritionAnalyzer ──────────────────────────
    analyzer = nutrition_analyzers.get(user_id)
    if analyzer:
        # Replace or add the log for this date in analyzer history
        existing = next(
            (i for i, l in enumerate(analyzer.history) if l.date.date().isoformat() == date_str),
            None
        )
        if existing is not None:
            analyzer.history[existing] = daily_log
        else:
            analyzer.add_daily_log(daily_log)

    total = meal.get_total_nutrition()
    return jsonify({
        "status":     "success",
        "meal_id":    meal.meal_id,
        "timestamp":  meal.timestamp.isoformat(),
        "nutrition":  {
            "calories":  total.calories,
            "protein_g": total.protein_g,
            "carbs_g":   total.carbs_g,
            "fat_g":     total.fat_g,
        },
    }), 201


# ═══════════════════════════════════════════════════════════════════════════
# NUTRITION — ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/nutrition/analysis/<user_id>', methods=['GET'])
def analyze_nutrition(user_id):
    """
    Return the full nutrition report for a user.

    Optional query params:
        goal          : e.g. "MUSCLE_GAIN"
        focus_scores  : comma-separated integers, e.g. "7,8,6,9"
    """
    user, err = _require_user(user_id)
    if err:
        return err

    analyzer = nutrition_analyzers.get(user_id)
    if not analyzer:
        return jsonify({"error": "Nutrition analyzer not initialized"}), 400

    goal = request.args.get('goal')

    focus_raw = request.args.get('focus_scores', '')
    focus_scores = None
    if focus_raw:
        try:
            focus_scores = [int(s) for s in focus_raw.split(',')]
        except ValueError:
            return jsonify({"error": "focus_scores must be comma-separated integers"}), 400

    report = analyzer.get_nutrition_report(goal=goal, focus_scores=focus_scores)
    return jsonify(report), 200


@app.route('/api/nutrition/recommendations/<user_id>', methods=['GET'])
def get_nutrition_recommendations(user_id):
    """Return goal-aware macro recommendations."""
    user, err = _require_user(user_id)
    if err:
        return err

    analyzer = nutrition_analyzers.get(user_id)
    if not analyzer:
        return jsonify({"error": "Nutrition analyzer not initialized"}), 400

    goal = request.args.get('goal')
    return jsonify(analyzer.get_macro_recommendations(goal=goal)), 200


@app.route('/api/nutrition/meal-recommendations/<user_id>', methods=['GET'])
def get_meal_recommendations(user_id):
    """
    Return personalised food recommendations from MealRecommendationEngine.

    Query params:
        target_calories : float (required)
        target_protein  : float (required)
        n               : int, number of results (default 5)
        mode            : "constraint" | "content" | "hybrid" (default "constraint")
    """
    user, err = _require_user(user_id)
    if err:
        return err

    recommender = meal_recommenders.get(user_id)
    if not recommender:
        return jsonify({"error": "Meal recommender not initialized"}), 400

    try:
        target_calories = float(request.args.get('target_calories', user.target_calories))
        target_protein  = float(request.args.get('target_protein',  user.target_protein_g))
    except ValueError:
        return jsonify({"error": "target_calories and target_protein must be numbers"}), 400

    n    = request.args.get('n', 5, type=int)
    mode = request.args.get('mode', 'constraint')

    if mode == 'content':
        results = recommender.get_content_based_recommendations(n=n)
    elif mode == 'hybrid':
        results = recommender.get_hybrid_recommendations(target_calories, target_protein, n=n)
    else:
        results = recommender.get_constraint_based_recommendations(target_calories, target_protein, n=n)

    return jsonify({"recommendations": results, "mode": mode, "count": len(results)}), 200


# ═══════════════════════════════════════════════════════════════════════════
# SCHEDULE OPTIMISATION
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/schedule/optimize/<user_id>', methods=['POST'])
def optimize_schedule(user_id):
    """Optimise a list of study tasks for a user."""
    user, err = _require_user(user_id)
    if err:
        return err

    data      = request.json or {}
    optimizer = ScheduleOptimizer(user.earliest_study_time, user.latest_study_time)
    tasks     = data.get('tasks', [])
    optimized = optimizer.optimize_schedule(tasks)

    return jsonify({
        "status":    "success",
        "schedule":  optimized,
        "num_tasks": len(optimized),
    }), 200


@app.route('/api/schedule/available-slots/<user_id>', methods=['GET'])
def get_available_slots(user_id):
    """Return available time slots for a given session duration."""
    user, err = _require_user(user_id)
    if err:
        return err

    duration  = request.args.get('duration_minutes', 60, type=int)
    optimizer = ScheduleOptimizer(user.earliest_study_time, user.latest_study_time)
    slots     = optimizer.get_available_slots(duration)

    return jsonify({
        "slots": [
            {
                "day":                  slot.day_name,
                "start_hour":           slot.start_hour,
                "end_hour":             slot.end_hour,
                "productivity_factor":  slot.productivity_factor,
            }
            for slot in slots
        ]
    }), 200


# ═══════════════════════════════════════════════════════════════════════════
# PRODUCTIVITY PREDICTION
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/productivity/predict/<user_id>', methods=['POST'])
def predict_productivity(user_id):
    """Predict focus score and recommended session duration."""
    _, err = _require_user(user_id)
    if err:
        return err

    data = request.json or {}
    features = Features(
        hour_of_day               = data.get('hour_of_day',               10),
        day_of_week               = data.get('day_of_week',               0),
        sleep_quality             = data.get('sleep_quality',             7.0),
        sleep_hours               = data.get('sleep_hours',               8.0),
        nutrition_score           = data.get('nutrition_score',           75.0),
        energy_level              = data.get('energy_level',              7),
        previous_session_duration = data.get('previous_session_duration', 60),
        task_difficulty           = data.get('task_difficulty',           5),
    )

    predictor   = ProductivityPredictor()
    focus_score = predictor.predict(features)
    duration    = predictor.estimate_session_duration(
        data.get('task_difficulty', 5),
        data.get('energy_level', 7),
        focus_score,
    )

    return jsonify({
        "predicted_focus_score":       focus_score,
        "recommended_duration_minutes": duration,
        "model_info":                  predictor.get_model_info(),
    }), 200


@app.route('/api/productivity/optimal-time/<user_id>', methods=['GET'])
def get_optimal_study_time(user_id):
    """Return the optimal hour and day for a study session."""
    user, err = _require_user(user_id)
    if err:
        return err

    predictor        = ProductivityPredictor()
    hour, day, focus = predictor.suggest_optimal_time(
        user.earliest_study_time, user.latest_study_time
    )
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    return jsonify({
        "optimal_hour":          hour,
        "optimal_day":           days[day],
        "predicted_focus_score": focus,
    }), 200


# ═══════════════════════════════════════════════════════════════════════════
# KNOWLEDGE BASE RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/recommendations/<user_id>', methods=['POST'])
def get_recommendations(user_id):
    """Run the knowledge base inference engine and return top recommendations."""
    user, err = _require_user(user_id)
    if err:
        return err

    kb = knowledge_bases.get(user_id)
    if not kb:
        return jsonify({"error": "Knowledge base not initialized"}), 400

    data = request.json or {}
    kb.add_facts({
        "daily_calories":            data.get("daily_calories",            2000),
        "daily_protein":             data.get("daily_protein",             150),
        "energy_level":              data.get("energy_level",              5),
        "sleep_hours":               data.get("sleep_hours",               8),
        "upcoming_difficulty":       data.get("upcoming_difficulty",       5),
        "recent_session_duration":   data.get("recent_session_duration",   60),
        "macro_balance":             data.get("macro_balance",             "balanced"),
        "macro_balance_details":     data.get("macro_balance_details",     {}),
        "correlation_nutrition_study": data.get("correlation_nutrition_study", 0.0),
        "adherence_rate":            data.get("adherence_rate",            0.5),
    })

    recommendations = kb.get_top_recommendations(n=3)
    kb.clear_facts()

    return jsonify({
        "status":          "success",
        "recommendations": recommendations,
        "count":           len(recommendations),
    }), 200


# ═══════════════════════════════════════════════════════════════════════════
# HEALTH INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/insights/<user_id>', methods=['GET'])
def get_health_insights(user_id):
    """Return a combined summary of the user's health metrics and module status."""
    user, err = _require_user(user_id)
    if err:
        return err

    return jsonify({
        "user_profile": {
            "name":       user.name,
            "age":        user.age,
            "weight_kg":  user.current_weight_kg,
            "goals":      [g.value for g in user.goals],
        },
        "nutritional_metrics": {
            "bmr":             round(user.get_bmr(), 1),
            "tdee":            user.get_tdee(),
            "target_calories": user.target_calories,
        },
        "ai_modules_status": {
            "knowledge_base":    user_id in knowledge_bases,
            "nutrition_analyzer": user_id in nutrition_analyzers,
            "meal_recommender":  user_id in meal_recommenders,
        },
    }), 200


# ═══════════════════════════════════════════════════════════════════════════
# AI CHATBOT
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/chat/<user_id>', methods=['POST'])
def chat(user_id):
    """
    Send a message to the AI health chatbot.

    Body (JSON):
        message              : str  (required)
        calories_today       : int
        protein_g            : float
        carbs_g              : float
        fat_g                : float
        water_ml             : int
        study_hours_today    : float
        focus_score          : float
        sleep_hours          : float
        dietary_restrictions : list[str]
        active_insights      : list[str]
    """
    user, err = _require_user(user_id)
    if err:
        return err

    data    = request.json or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    snapshot = UserHealthSnapshot(
        name                   = user.name,
        calories_today         = data.get("calories_today",      0),
        calorie_target         = user.target_calories,
        protein_g              = data.get("protein_g",           0),
        protein_target_g       = user.target_protein_g,
        carbs_g                = data.get("carbs_g",             0),
        fat_g                  = data.get("fat_g",               0),
        water_ml               = data.get("water_ml",            0),
        study_hours_today      = data.get("study_hours_today",   0),
        focus_score            = data.get("focus_score"),
        sleep_hours_last_night = data.get("sleep_hours"),
        health_goal            = user.goals[0].value if user.goals else "general wellness",
        dietary_restrictions   = data.get("dietary_restrictions", []),
        active_insights        = data.get("active_insights",     []),
    )

    if user_id not in bot_sessions:
        bot_sessions[user_id] = HealthChatbot(snapshot)
    else:
        bot_sessions[user_id].update_snapshot(snapshot)

    reply = bot_sessions[user_id].chat(message)
    return jsonify({"reply": reply}), 200


@app.route('/api/chat/<user_id>/reset', methods=['POST'])
def reset_chat(user_id):
    """Wipe the conversation history for a user's chatbot session."""
    if user_id in bot_sessions:
        bot_sessions[user_id].reset()
    return jsonify({"status": "ok"}), 200


# ═══════════════════════════════════════════════════════════════════════════
# EXTERNAL API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/food/search', methods=['GET'])
def food_search():
    """
    Search all food sources (USDA + Open Food Facts) and return FoodItems.

    Query params:
        q     : search term (required)
        limit : max results (default 5)
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "q parameter is required"}), 400

    limit   = request.args.get("limit", 5, type=int)
    results = search_all_sources(query, page_size=limit)

    return jsonify({
        "results": [
            {
                "food_id":   f.food_id,
                "name":      f.name,
                "calories":  f.nutrition_info.calories,
                "protein_g": f.nutrition_info.protein_g,
                "carbs_g":   f.nutrition_info.carbs_g,
                "fat_g":     f.nutrition_info.fat_g,
                "tags":      f.tags,
            }
            for f in results
        ],
        "count": len(results),
    }), 200


@app.route('/api/food/barcode/<barcode>', methods=['GET'])
def food_by_barcode(barcode):
    """Look up a food product by EAN-13 / UPC barcode."""
    result = get_food_by_barcode(barcode)
    if not result:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(result), 200


@app.route('/api/food/log-text/<user_id>', methods=['POST'])
def food_log_text(user_id):
    """
    Parse a plain-text meal description via Nutritionix NLP and
    immediately log the resulting foods as a meal for the user.

    Body: { "text": "2 eggs and a banana", "meal_type": "breakfast" }
    Requires NUTRITIONIX_APP_ID and NUTRITIONIX_APP_KEY in .env.
    """
    user, err = _require_user(user_id)
    if err:
        return err

    data = request.json or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    parsed = log_natural_language_meal(text)
    if not parsed:
        return jsonify({
            "error": "Could not parse meal. Check Nutritionix keys in .env or try rephrasing."
        }), 503

    # Convert to FoodItems and log as a meal
    food_items = [nutritionix_to_fooditem(f) for f in parsed]
    meal = Meal(
        meal_id    = f"nlp_{datetime.now().timestamp()}",
        user_id    = user_id,
        meal_type  = MealType(data.get('meal_type', 'snack')),
        timestamp  = datetime.now(),
        food_items = food_items,
        notes      = f"NLP parsed: {text}",
    )

    date_str  = meal.timestamp.date().isoformat()
    daily_log = _get_or_create_daily_log(user_id, date_str)
    daily_log.meals.append(meal)

    analyzer = nutrition_analyzers.get(user_id)
    if analyzer:
        existing = next(
            (i for i, l in enumerate(analyzer.history) if l.date.date().isoformat() == date_str),
            None
        )
        if existing is not None:
            analyzer.history[existing] = daily_log
        else:
            analyzer.add_daily_log(daily_log)

    total = meal.get_total_nutrition()
    return jsonify({
        "status":   "success",
        "meal_id":  meal.meal_id,
        "foods":    parsed,
        "nutrition": {
            "calories":  total.calories,
            "protein_g": total.protein_g,
            "carbs_g":   total.carbs_g,
            "fat_g":     total.fat_g,
        },
    }), 201


@app.route('/api/exercise/search', methods=['GET'])
def exercise_search():
    """Search the Wger exercise database by name."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "q parameter is required"}), 400

    results = search_exercise(query)
    return jsonify({"results": results, "count": len(results)}), 200


@app.route('/api/weather/context', methods=['GET'])
def weather_context():
    """
    Return weather-based wellness hints via Open-Meteo.

    Query params: lat, lon
    Example: /api/weather/context?lat=3.139&lon=101.686
    """
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    if lat is None or lon is None:
        return jsonify({"error": "lat and lon are required"}), 400

    return jsonify(get_weather_context(lat, lon)), 200


# ═══════════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/health', methods=['GET'])
def health_check():
    """Liveness probe — returns 200 when the server is running."""
    return jsonify({
        "status":    "healthy",
        "timestamp": datetime.now().isoformat(),
        "users":     len(users),
    }), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)