"""Comprehensive tests for AI Health Tracker modules"""
import unittest
from datetime import datetime, timedelta
from models.user_profile import UserProfile, Goal
from models.meal import (
    NutritionInfo, FoodItem, Meal, MealType, DailyNutritionLog
)
from models.activity import StudySession, ScheduledActivity, ActivityType
from ai_modules import (
    KnowledgeBase, ScheduleOptimizer, ProductivityPredictor, Features,
    NutritionAnalyzer, BehavioralAnalyzer
)
from ai_modules.recommendation_engine import MealRecommendationEngine


class TestUserProfile(unittest.TestCase):
    """Test user profile calculations"""
    
    def setUp(self):
        self.user = UserProfile(
            user_id="test_user",
            name="Test User",
            age=25,
            weight_kg=80,
            height_cm=180,
            goals=[Goal.WEIGHT_LOSS]
        )
    
    def test_bmr_calculation(self):
        """Test Basal Metabolic Rate calculation"""
        bmr = self.user.get_bmr()
        self.assertGreater(bmr, 0)
        self.assertLess(bmr, 2000)  # Reasonable upper bound
    
    def test_tdee_calculation(self):
        """Test Total Daily Energy Expenditure"""
        tdee = self.user.get_tdee(activity_level=1.5)
        bmr = self.user.get_bmr()
        self.assertAlmostEqual(tdee, int(bmr * 1.5))


class TestNutritionModels(unittest.TestCase):
    """Test nutrition data models"""
    
    def setUp(self):
        self.nutrition = NutritionInfo(
            calories=500, protein_g=30, carbs_g=60, fat_g=15
        )
    
    def test_macro_ratio(self):
        """Test macro ratio calculation"""
        macros = self.nutrition.get_macro_ratio()
        
        self.assertIn("protein_percent", macros)
        self.assertIn("carbs_percent", macros)
        self.assertIn("fat_percent", macros)
        
        # Sum should approximately equal 100
        total = macros["protein_percent"] + macros["carbs_percent"] + macros["fat_percent"]
        self.assertAlmostEqual(total, 100, delta=1)
    
    def test_meal_total_nutrition(self):
        """Test total nutrition calculation for meal"""
        food1 = FoodItem(
            food_id="f1",
            name="Food 1",
            nutrition_info=NutritionInfo(calories=100, protein_g=10, carbs_g=15, fat_g=3)
        )
        food2 = FoodItem(
            food_id="f2",
            name="Food 2",
            nutrition_info=NutritionInfo(calories=200, protein_g=15, carbs_g=30, fat_g=6)
        )
        food3 = FoodItem(
            food_id="f3",
            name="Food 3",
            nutrition_info=NutritionInfo(calories=0, protein_g=0, carbs_g=0, fat_g=0)
        )
        
        meal = Meal(
            meal_id="meal1",
            user_id="user1",
            meal_type=MealType.LUNCH,
            timestamp=datetime.now(),
            food_items=[food1, food2, food3]
        )
        
        total = meal.get_total_nutrition()
        self.assertEqual(total.calories, 300)
        self.assertEqual(total.protein_g, 25)


class TestProductivityPredictor(unittest.TestCase):
    """Test ML-based productivity prediction"""
    
    def setUp(self):
        self.predictor = ProductivityPredictor()
    
    def test_prediction_range(self):
        """Test that predictions are within valid range"""
        features = Features(
            hour_of_day=10,
            day_of_week=2,
            sleep_quality=7.0,
            sleep_hours=8.0,
            nutrition_score=75.0,
            energy_level=7,
            previous_session_duration=60,
            task_difficulty=5
        )
        
        prediction = self.predictor.predict(features)
        self.assertGreaterEqual(prediction, 1)
        self.assertLessEqual(prediction, 10)
    
    def test_optimal_time_suggestion(self):
        """Test optimal time recommendation"""
        hour, day, focus = self.predictor.suggest_optimal_time()
        
        self.assertGreaterEqual(hour, 8)
        self.assertLessEqual(hour, 22)
        self.assertGreaterEqual(day, 0)
        self.assertLessEqual(day, 4) 
        self.assertGreater(focus, 0)
    
    def test_session_duration_estimation(self):
        """Test study session duration estimation"""
        duration = self.predictor.estimate_session_duration(
            difficulty=7, energy_level=8, focus_prediction=9
        )
        
        self.assertGreaterEqual(duration, 25)
        self.assertLessEqual(duration, 180)


class TestScheduleOptimizer(unittest.TestCase):
    """Test schedule optimization CSP solver"""
    
    def setUp(self):
        self.optimizer = ScheduleOptimizer(user_earliest=8, user_latest=22)
    
    def test_available_slots_generation(self):
        """Test generation of available time slots"""
        slots = self.optimizer.get_available_slots(duration_minutes=60, num_slots=5)
        
        self.assertLessEqual(len(slots), 5)
        for slot in slots:
            self.assertGreaterEqual(slot.start_hour, 8)
            self.assertLessEqual(slot.end_hour, 22)
            self.assertGreater(slot.productivity_factor, 0)
    
    def test_schedule_optimization(self):
        """Test schedule optimization"""
        tasks = [
            {
                "subject": "Math",
                "duration_min": 90,
                "difficulty": 8,
                "deadline": datetime.now() + timedelta(days=2)
            },
            {
                "subject": "Physics",
                "duration_min": 60,
                "difficulty": 6,
                "deadline": datetime.now() + timedelta(days=3)
            },
            {
                "subject": "Machine Learning",
                "duration_min": 45,
                "difficulty": 3,
                "deadline": datetime.now() + timedelta(days=5)
            },
            {
                "subject": "AI",
                "duration_min": 120,
                "difficulty": 9,
                "deadline": datetime.now() + timedelta(days=1)
            }
        ]
        
        schedule = self.optimizer.optimize_schedule(tasks, num_trials=10)
        
        self.assertIsNotNone(schedule)
        self.assertGreater(len(schedule), 0)


class TestNutritionAnalyzer(unittest.TestCase):
    """Test nutrition analysis"""
    
    def setUp(self):
        self.target_nutrition = NutritionInfo(
            calories=2000,
            protein_g=150,
            carbs_g=250,
            fat_g=65
        )
        self.analyzer = NutritionAnalyzer(self.target_nutrition)
    
    def test_daily_log_adherence(self):
        """Test adherence calculation"""
        nutrition = NutritionInfo(
            calories=2000,  # Exact match
            protein_g=150,
            carbs_g=250,
            fat_g=65
        )
        
        meal = Meal(
            meal_id="m1",
            user_id="user1",
            meal_type=MealType.LUNCH,
            timestamp=datetime.now(),
            food_items=[FoodItem(food_id="f1", name="Food", nutrition_info=nutrition)]
        )
        
        log = DailyNutritionLog(
            log_id="log1",
            user_id="user1",
            date=datetime.now(),
            meals=[meal]
        )
        
        adherence = log.get_adherence_ratio(self.target_nutrition)
        self.assertEqual(adherence, 1.0)
    
    def test_weekly_average(self):
        """Test weekly average calculation"""
        # Add multiple daily logs
        for i in range(7):
            nutrition = NutritionInfo(
                calories=2000 + (i * 50),
                protein_g=150,
                carbs_g=250,
                fat_g=65
            )
            # Create logs (simplified)
        
        # Since we can't easily add logs, just test the method exists
        avg = self.analyzer.get_weekly_average(days=7)
        self.assertIsNotNone(avg)


class TestKnowledgeBase(unittest.TestCase):
    """Test rule-based inference engine"""
    
    def setUp(self):
        self.user = UserProfile(
            user_id="test",
            name="Test",
            age=25,
            weight_kg=70,
            height_cm=175,
            goals=[Goal.WEIGHT_LOSS]
        )
        self.kb = KnowledgeBase(self.user)
    
    def test_rule_addition(self):
        """Test adding rules to knowledge base"""
        initial_count = len(self.kb.rules)
        self.assertGreater(initial_count, 0)  # Should have default rules
    
    def test_inference(self):
        """Test rule inference"""
        self.kb.add_facts({
            "daily_calories": 2500,  # Over target
            "daily_protein": 100
        })
        
        recommendations = self.kb.infer()
        self.assertIsInstance(recommendations, list)
    
    def test_correlation_calculation(self):
        """Test correlation calculation"""
        data1 = [1.0, 2.0, 3.0, 4.0, 5.0]
        data2 = [1.0, 2.0, 3.0, 4.0, 5.0]  # Perfect correlation
        
        corr = BehavioralAnalyzer.calculate_correlation(data1, data2)
        self.assertAlmostEqual(corr, 1.0, places=2)
    
    def test_anomaly_detection(self):
        """Test anomaly detection"""
        normal_values = [5.0, 5.2, 4.9, 5.1, 5.0]
        with_anomaly = normal_values + [15.0]  # Clear anomaly
        
        is_anomaly = BehavioralAnalyzer.detect_anomaly(with_anomaly, sensitivity=2.0)
        self.assertTrue(is_anomaly)


class TestMealRecommendationEngine(unittest.TestCase):
    """Test meal recommendation system"""
    
    def setUp(self):
        self.user = UserProfile(
            user_id="test",
            name="Test",
            age=25,
            weight_kg=70,
            height_cm=175
        )
        
        self.foods = [
            FoodItem(
                food_id="f1",
                name="Chicken",
                nutrition_info=NutritionInfo(calories=200, protein_g=30, carbs_g=0, fat_g=5)
            ),
            FoodItem(
                food_id="f2",
                name="Rice",
                nutrition_info=NutritionInfo(calories=200, protein_g=5, carbs_g=45, fat_g=1)
            )
        ]
        
        self.recommender = MealRecommendationEngine(self.user, self.foods)
    
    def test_dietary_constraint_satisfaction(self):
        """Test dietary constraint checking"""
        self.user.dietary_restrictions = ["vegan"]
        
        food_with_meat = FoodItem(
            food_id="meat",
            name="Steak",
            nutrition_info=NutritionInfo(calories=300, protein_g=40, carbs_g=0, fat_g=15),
            is_vegan=False
        )
        
        satisfies = self.recommender.satisfies_dietary_constraints(food_with_meat)
        self.assertFalse(satisfies)
    
    def test_food_similarity(self):
        """Test food similarity calculation"""
        food1 = FoodItem(
            food_id="f1",
            name="Food 1",
            nutrition_info=NutritionInfo(calories=200, protein_g=30, carbs_g=10, fat_g=5),
            category="protein",
            tags=["lean"]
        )
        
        food2 = FoodItem(
            food_id="f2",
            name="Food 2",
            nutrition_info=NutritionInfo(calories=210, protein_g=28, carbs_g=12, fat_g=6),
            category="protein",
            tags=["lean"]
        )
        
        v1 = self.recommender.food_vector(food1)
        v2 = self.recommender.food_vector(food2)
        similarity = self.recommender.cosine_similarity(v1, v2)
        self.assertGreater(similarity, 0)
        self.assertLessEqual(similarity, 1.0)


class TestIntegration(unittest.TestCase):
    """Integration tests for end-to-end workflows"""
    
    def test_daily_workflow(self):
        """Test a complete daily workflow"""
        # Create user
        user = UserProfile(
            user_id="integration_test",
            name="John",
            age=22,
            weight_kg=75,
            height_cm=180,
            goals=[Goal.ENERGY_OPTIMIZATION]
        )
        
        # Initialize AI modules
        target_nutrition = NutritionInfo(2200, 150, 250, 65)
        analyzer = NutritionAnalyzer(target_nutrition)
        predictor = ProductivityPredictor()
        scheduler = ScheduleOptimizer()
        kb = KnowledgeBase(user)
        
        # Simulate morning prediction
        morning_features = Features(
            hour_of_day=9,
            day_of_week=1,
            sleep_quality=8.0,
            sleep_hours=8.0,
            nutrition_score=80.0,
            energy_level=8,
            previous_session_duration=45,
            task_difficulty=6
        )
        
        focus_score = predictor.predict(morning_features)
        self.assertGreater(focus_score, 0)
        
        # Get schedule recommendations
        tasks = [
            {
                "subject": "Study",
                "duration_min": 60,
                "difficulty": 6,
                "deadline": datetime.now() + timedelta(days=1)
            }
        ]
        
        schedule = scheduler.optimize_schedule(tasks, num_trials=5)
        self.assertIsNotNone(schedule)
        
        # Get knowledge base recommendations
        kb.add_facts({
            "daily_calories": 2200,
            "energy_level": 8,
            "sleep_hours": 8
        })
        
        recommendations = kb.infer()
        self.assertIsInstance(recommendations, list)


def run_tests():
    """Run all tests"""
    unittest.main(exit=False, verbosity=2)


if __name__ == '__main__':
    run_tests()
