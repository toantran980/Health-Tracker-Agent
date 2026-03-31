"""
Example usage of the AI Health & Wellness Tracker
"""
from datetime import datetime, timedelta
from models.user_profile import UserProfile, Goal
from models.meal import (
    NutritionInfo, FoodItem, Meal, MealType, DailyNutritionLog
)
from models.activity import StudySession, ScheduledActivity, ActivityType
from ai_modules import (
    KnowledgeBase, ScheduleOptimizer, ProductivityPredictor, Features,
    NutritionAnalyzer, MealRecommendationEngine, ActivityRecommendationEngine
)


def example_1_user_creation():
    """Example 1: Create user profile"""
    print("Example 1: User Profile Creation")
    user = UserProfile(
        user_id="user_001",
        name="Alex Chen",
        age=22,
        weight_kg=72,
        height_cm=178,
        goals=[Goal.ENERGY_OPTIMIZATION, Goal.MUSCLE_GAIN],
        dietary_restrictions=["vegan"],
        allergies=["peanuts"],
        target_calories=2400,
        target_protein_g=180,
        target_carbs_g=280,
        target_fat_g=80
    )
    
    print(f"\nUser: {user.name}")
    print(f"BMR: {user.get_bmr():.1f} kcal")
    print(f"TDEE (1.5 activity): {user.get_tdee(1.5)} kcal")
    print(f"Goals: {[g.value for g in user.goals]}")
    print(f"Dietary Restrictions: {user.dietary_restrictions}")
    
    return user


def example_2_productivity_prediction(user: UserProfile):
    """Example 2: Predict productivity for study session"""
    print("Example 2: Productivity Prediction")
    
    predictor = ProductivityPredictor(model_type="nonlinear")
    
    # Scenario 1: Morning study with good sleep
    morning_features = Features(
        hour_of_day=10,
        day_of_week=1,  # Tuesday
        sleep_quality=9.0,
        sleep_hours=8.5,
        nutrition_score=85.0,
        energy_level=8,
        previous_session_duration=60,
        task_difficulty=7
    )
    
    focus_score = predictor.predict(morning_features)
    duration = predictor.estimate_session_duration(7, 8, focus_score)
    
    print(f"\nMorning Study Session (Tuesday 10:00)")
    print(f"  Predicted Focus Score: {focus_score}/10")
    print(f"  Recommended Duration: {duration} minutes")
    
    # Scenario 2: Evening study with poor sleep
    evening_features = Features(
        hour_of_day=20,
        day_of_week=4,  # Friday
        sleep_quality=5.0,
        sleep_hours=6.0,
        nutrition_score=60.0,
        energy_level=4,
        previous_session_duration=30,
        task_difficulty=5
    )
    
    evening_focus = predictor.predict(evening_features)
    evening_duration = predictor.estimate_session_duration(5, 4, evening_focus)
    
    print(f"\nEvening Study Session (Friday 20:00)")
    print(f"  Predicted Focus Score: {evening_focus}/10")
    print(f"  Recommended Duration: {evening_duration} minutes")
    
    # Find optimal time
    optimal_hour, optimal_day, optimal_focus = predictor.suggest_optimal_time(8, 22)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    print(f"\nOptimal Study Time This Week: {days[optimal_day]} {optimal_hour}:00")
    print(f"  Expected Focus Score: {optimal_focus:.1f}/10")


def example_3_schedule_optimization(user: UserProfile):
    """Example 3: Optimize weekly study schedule"""
    print("Example 3: Schedule Optimization")
    
    scheduler = ScheduleOptimizer(user.earliest_study_time, user.latest_study_time)
    
    # Define tasks
    tasks = [
        {
            "subject": "Data Structures",
            "duration_min": 120,
            "difficulty": 8,
            "deadline": datetime.now() + timedelta(days=2)
        },
        {
            "subject": "Linear Algebra",
            "duration_min": 90,
            "difficulty": 7,
            "deadline": datetime.now() + timedelta(days=3)
        },
        {
            "subject": "Programming Project",
            "duration_min": 150,
            "difficulty": 9,
            "deadline": datetime.now() + timedelta(days=4)
        },
        {
            "subject": "Reading Assignment",
            "duration_min": 60,
            "difficulty": 4,
            "deadline": datetime.now() + timedelta(days=5)
        }
    ]
    
    print(f"\nOptimizing schedule for {len(tasks)} tasks...")
    optimized_schedule = scheduler.optimize_schedule(tasks, num_trials=50)
    
    if optimized_schedule:
        print(f"\nOptimized Study Schedule:\n")
        for i, item in enumerate(optimized_schedule, 1):
            task = item["task"]
            time_slot = item["time_slot"]
            print(f"  {i}. {task['subject']} ({task['duration_min']}min)")
            print(f"     {time_slot}")
            print(f"     Difficulty: {task['difficulty']}/10")


def example_4_nutrition_analysis():
    """Example 4: Nutrition tracking and analysis"""
    print("Example 4: Nutrition Analysis")
    
    # Target nutrition
    target = NutritionInfo(
        calories=2400,
        protein_g=180,
        carbs_g=280,
        fat_g=80
    )
    
    # Sample food database
    foods = [
        FoodItem(
            food_id="tofu",
            name="Tofu (200g)",
            nutrition_info=NutritionInfo(calories=180, protein_g=22, carbs_g=2, fat_g=11),
            tags=["vegan", "protein"],
            is_vegan=True
        ),
        FoodItem(
            food_id="quinoa",
            name="Quinoa (1 cup)",
            nutrition_info=NutritionInfo(calories=220, protein_g=8, carbs_g=40, fat_g=4),
            tags=["vegan", "grain"],
            is_vegan=True
        ),
        FoodItem(
            food_id="vegetables",
            name="Mixed Vegetables (3 cups)",
            nutrition_info=NutritionInfo(calories=120, protein_g=6, carbs_g=22, fat_g=1),
            tags=["vegan", "vegetables"],
            is_vegan=True
        ),
    ]
    
    # Create analyzer
    analyzer = NutritionAnalyzer(target)
    
    # Create meals
    meal1 = Meal(
        meal_id="m1",
        user_id="user_001",
        meal_type=MealType.LUNCH,
        timestamp=datetime.now(),
        food_items=[foods[0], foods[1], foods[2]]
    )
    
    daily_log = DailyNutritionLog(
        log_id="log_1",
        user_id="user_001",
        date=datetime.now(),
        meals=[meal1]
    )
    
    analyzer.add_daily_log(daily_log)
    
    print(f"\nMeal Logged: {meal1.get_macro_balance()}")
    total = meal1.get_total_nutrition()
    print(f"  Calories: {total.calories:.0f} / {target.calories}")
    print(f"  Protein: {total.protein_g:.0f}g / {target.protein_g}g")
    print(f"  Carbs: {total.carbs_g:.0f}g / {target.carbs_g}g")
    print(f"  Fat: {total.fat_g:.0f}g / {target.fat_g}g")
    
    # Macro recommendations
    recommendations = analyzer.get_macro_recommendations()
    print(f"\nRecommendations:")
    for macro, rec in recommendations.items():
        print(f"{rec}")


def example_5_meal_recommendations():
    """Example 5: Personalized meal recommendations"""
    print("Example 5: Meal Recommendations")
    
    user = UserProfile(
        user_id="user_001",
        name="Alex",
        age=22,
        weight_kg=72,
        height_cm=178,
        dietary_restrictions=["vegan"],
        allergies=["peanuts"]
    )
    
    # Sample vegan foods
    foods = [
        FoodItem(food_id="lentils", name="Lentil Pasta", 
                 nutrition_info=NutritionInfo(200, 12, 35, 2),
                 is_vegan=True, tags=["vegan", "protein"]),
        FoodItem(food_id="chickpeas", name="Chickpea Curry",
                 nutrition_info=NutritionInfo(250, 15, 30, 8),
                 is_vegan=True, tags=["vegan", "protein"]),
        FoodItem(food_id="cashew", name="Cashew Stir Fry",
                 nutrition_info=NutritionInfo(300, 8, 25, 20),
                 is_vegan=True, tags=["vegan", "nuts"]),
    ]
    
    recommender = MealRecommendationEngine(user, foods)
    
    # Get constraint-based recommendations
    recommendations = recommender.get_constraint_based_recommendations(
        target_calories=2400,
        target_protein=180,
        n=3
    )
    
    print(f"\nRecommended Vegan Meals:\n")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec['name']}")
        print(f"     Calories: {rec['calories']:.0f} | Protein: {rec['protein_g']:.0f}g")
        print(f"     Fit Score: {rec['fit_score']}")


def example_6_knowledge_base_inference():
    """Example 6: AI-powered recommendations using knowledge base"""
    print("Example 6: Knowledge Base Inference")

    
    user = UserProfile(
        user_id="user_001",
        name="Alex",
        age=22,
        weight_kg=72,
        height_cm=178,
        goals=[Goal.WEIGHT_LOSS]
    )
    
    kb = KnowledgeBase(user)
    
    # Add facts about today
    kb.add_facts({
        "daily_calories": 2800,  # Over target
        "daily_protein": 140,    # Below target
        "energy_level": 4,       # Low
        "sleep_hours": 6,        # Below 7
        "upcoming_difficulty": 8,
        "recent_session_duration": 20,
        "macro_balance": "unbalanced",
        "macro_balance_details": {"protein": 25, "carbs": 55, "fat": 20},
        "correlation_nutrition_study": 0.75,
        "adherence_rate": 0.65
    })
    
    # Get recommendations
    recommendations = kb.get_top_recommendations(n=3)
    
    print(f"\nAI Recommendations Based on Today's Data:\n")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec.get('action', 'N/A').replace('_', ' ').title()}")
        print(f"     {rec.get('suggestion', '')}")
        print(f"     Confidence: {rec.get('confidence', 0)*100:.0f}%\n")


def main():
    """Run all examples"""
    print("AI HEALTH & WELLNESS TRACKER - EXAMPLES")
    
    # Run examples
    user = example_1_user_creation()
    example_2_productivity_prediction(user)
    example_3_schedule_optimization(user)
    example_4_nutrition_analysis()
    example_5_meal_recommendations()
    example_6_knowledge_base_inference()
    
    print("\nAll examples completed!")


if __name__ == '__main__':
    main()
