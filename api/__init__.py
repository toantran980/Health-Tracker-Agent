"""REST API Routes using Flask"""
from flask import Flask, Blueprint, request, jsonify
from datetime import datetime, timedelta
from models.user_profile import UserProfile, Goal
from models.meal import NutritionInfo, Meal, MealType, FoodItem, DailyNutritionLog
from models.activity import StudySession, ScheduledActivity, ActivityType
from ai_modules import (
    KnowledgeBase, ScheduleOptimizer, ProductivityPredictor, Features,
    NutritionAnalyzer, MealRecommendationEngine, ActivityRecommendationEngine
)
from typing import Dict, Any

# Create Flask app
app = Flask(__name__)

# Global storage (in production, use database)
users: Dict[str, UserProfile] = {}
knowledge_bases: Dict[str, KnowledgeBase] = {}
nutrition_analyzers: Dict[str, NutritionAnalyzer] = {}
meal_recommenders: Dict[str, MealRecommendationEngine] = {}


# ============ USER PROFILE ENDPOINTS ============

@app.route('/api/user/create', methods=['POST'])
def create_user():
    """Create a new user profile"""
    data = request.json
    
    user_id = data.get('user_id', 'user_' + str(len(users)))
    user = UserProfile(
        user_id=user_id,
        name=data.get('name', 'Unknown'),
        age=data.get('age', 25),
        weight_kg=data.get('weight_kg', 70),
        height_cm=data.get('height_cm', 175),
        goals=[Goal(g) for g in data.get('goals', ['general_wellness'])],
        target_calories=data.get('target_calories', 2000),
        target_protein_g=data.get('target_protein_g', 150),
        target_carbs_g=data.get('target_carbs_g', 200),
        target_fat_g=data.get('target_fat_g', 65),
    )
    
    users[user_id] = user
    
    # Initialize AI modules
    target_nutrition = NutritionInfo(
        calories=user.target_calories,
        protein_g=user.target_protein_g,
        carbs_g=user.target_carbs_g,
        fat_g=user.target_fat_g
    )
    knowledge_bases[user_id] = KnowledgeBase(user)
    nutrition_analyzers[user_id] = NutritionAnalyzer(target_nutrition)
    meal_recommenders[user_id] = MealRecommendationEngine(user, [])
    
    return jsonify({"status": "success", "user": user.to_dict()}), 201


@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get user profile"""
    if user_id not in users:
        return jsonify({"error": "User not found"}), 404
    
    user = users[user_id]
    return jsonify(user.to_dict()), 200


# ============ NUTRITION ENDPOINTS ============

@app.route('/api/nutrition/log-meal', methods=['POST'])
def log_meal(user_id):
    """Log a meal"""
    data = request.json
    user = users.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Create meal
    meal = Meal(
        meal_id=f"meal_{datetime.now().timestamp()}",
        user_id=user_id,
        meal_type=MealType(data.get('meal_type', 'lunch')),
        timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat())),
        notes=data.get('notes', '')
    )
    
    return jsonify({
        "status": "success",
        "meal_id": meal.meal_id,
        "timestamp": meal.timestamp.isoformat()
    }), 201


@app.route('/api/nutrition/analysis/<user_id>', methods=['GET'])
def analyze_nutrition(user_id):
    """Get nutrition analysis and recommendations"""
    if user_id not in users:
        return jsonify({"error": "User not found"}), 404
    
    analyzer = nutrition_analyzers.get(user_id)
    if not analyzer:
        return jsonify({"error": "Nutrition analyzer not initialized"}), 400
    
    report = analyzer.get_nutrition_report()
    return jsonify(report), 200


@app.route('/api/nutrition/recommendations/<user_id>', methods=['GET'])
def get_nutrition_recommendations(user_id):
    """Get meal recommendations"""
    if user_id not in users:
        return jsonify({"error": "User not found"}), 404
    
    analyzer = nutrition_analyzers.get(user_id)
    if not analyzer:
        return jsonify({"error": "Nutrition analyzer not initialized"}), 400
    
    recommendations = analyzer.get_macro_recommendations()
    return jsonify(recommendations), 200


# ============ SCHEDULE OPTIMIZATION ENDPOINTS ============

@app.route('/api/schedule/optimize/<user_id>', methods=['POST'])
def optimize_schedule(user_id):
    """Optimize study schedule"""
    data = request.json
    user = users.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Create scheduler
    optimizer = ScheduleOptimizer(user.earliest_study_time, user.latest_study_time)
    
    # Optimize
    tasks = data.get('tasks', [])
    optimized = optimizer.optimize_schedule(tasks)
    
    return jsonify({
        "status": "success",
        "schedule": optimized,
        "num_tasks": len(optimized)
    }), 200


@app.route('/api/schedule/available-slots/<user_id>', methods=['GET'])
def get_available_slots(user_id):
    """Get available time slots for scheduling"""
    user = users.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    duration = request.args.get('duration_minutes', 60, type=int)
    
    optimizer = ScheduleOptimizer(user.earliest_study_time, user.latest_study_time)
    slots = optimizer.get_available_slots(duration)
    
    slots_data = [{
        "day": slot.day_name,
        "start_hour": slot.start_hour,
        "end_hour": slot.end_hour,
        "productivity_factor": slot.productivity_factor
    } for slot in slots]
    
    return jsonify({"slots": slots_data}), 200


# ============ PRODUCTIVITY PREDICTION ENDPOINTS ============

@app.route('/api/productivity/predict/<user_id>', methods=['POST'])
def predict_productivity(user_id):
    """Predict focus score for given conditions"""
    data = request.json
    
    features = Features(
        hour_of_day=data.get('hour_of_day', 10),
        day_of_week=data.get('day_of_week', 0),
        sleep_quality=data.get('sleep_quality', 7.0),
        sleep_hours=data.get('sleep_hours', 8.0),
        nutrition_score=data.get('nutrition_score', 75.0),
        energy_level=data.get('energy_level', 7),
        previous_session_duration=data.get('previous_session_duration', 60),
        task_difficulty=data.get('task_difficulty', 5)
    )
    
    predictor = ProductivityPredictor()
    focus_score = predictor.predict(features)
    
    duration = predictor.estimate_session_duration(
        data.get('task_difficulty', 5),
        data.get('energy_level', 7),
        focus_score
    )
    
    return jsonify({
        "predicted_focus_score": focus_score,
        "recommended_duration_minutes": duration,
        "model_info": predictor.get_model_info()
    }), 200


@app.route('/api/productivity/optimal-time/<user_id>', methods=['GET'])
def get_optimal_study_time(user_id):
    """Get optimal time for study session"""
    user = users.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    predictor = ProductivityPredictor()
    hour, day, focus = predictor.suggest_optimal_time(user.earliest_study_time, user.latest_study_time)
    
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    return jsonify({
        "optimal_hour": hour,
        "optimal_day": days[day],
        "predicted_focus_score": focus
    }), 200


# ============ KNOWLEDGE BASE & RECOMMENDATIONS ============

@app.route('/api/recommendations/<user_id>', methods=['POST'])
def get_recommendations(user_id):
    """Get AI-based recommendations using knowledge base"""
    data = request.json
    user = users.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    kb = knowledge_bases.get(user_id)
    if not kb:
        return jsonify({"error": "Knowledge base not initialized"}), 400
    
    # Add current facts
    kb.add_facts({
        "daily_calories": data.get("daily_calories", 2000),
        "daily_protein": data.get("daily_protein", 150),
        "energy_level": data.get("energy_level", 5),
        "sleep_hours": data.get("sleep_hours", 8),
        "upcoming_difficulty": data.get("upcoming_difficulty", 5),
        "recent_session_duration": data.get("recent_session_duration", 60),
        "macro_balance": data.get("macro_balance", "balanced"),
        "macro_balance_details": data.get("macro_balance_details", {}),
        "correlation_nutrition_study": data.get("correlation_nutrition_study", 0.0),
        "adherence_rate": data.get("adherence_rate", 0.5)
    })
    
    # Infer recommendations
    recommendations = kb.get_top_recommendations(n=3)
    
    # Clear facts for next cycle
    kb.clear_facts()
    
    return jsonify({
        "status": "success",
        "recommendations": recommendations,
        "count": len(recommendations)
    }), 200


# ============ HEALTH INSIGHTS ============

@app.route('/api/insights/<user_id>', methods=['GET'])
def get_health_insights(user_id):
    """Get comprehensive health insights"""
    user = users.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    insights = {
        "user_profile": {
            "name": user.name,
            "age": user.age,
            "weight_kg": user.current_weight_kg,
            "goals": [g.value for g in user.goals]
        },
        "nutritional_metrics": {
            "bmr": round(user.get_bmr(), 1),
            "tdee": user.get_tdee(),
            "target_calories": user.target_calories
        },
        "ai_modules_status": {
            "knowledge_base": user_id in knowledge_bases,
            "nutrition_analyzer": user_id in nutrition_analyzers,
            "meal_recommender": user_id in meal_recommenders
        }
    }
    
    return jsonify(insights), 200


# ============ HEALTH CHECK ============

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
