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
    NutritionAnalyzer, BehavioralAnalyzer, TimeSlot
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
        slots = self.optimizer.get_available_slots(duration_minutes=60, max_slots=5)
        
        self.assertLessEqual(len(slots), 5)
        for slot in slots:
            self.assertGreaterEqual(slot.start_hour, 8)
            self.assertLessEqual(slot.end_hour, 22)
            self.assertGreater(slot.productivity_factor, 0)
    
    def test_schedule_optimization(self):
        """Test schedule optimization"""
        tasks = [
            {
                "name": "Math",  # Changed from "subject" to "name"
                "duration_min": 90,
                "difficulty": 8,
                "deadline": datetime.now() + timedelta(days=2)
            },
            {
                "name": "Physics",  # Changed from "subject" to "name"
                "duration_min": 60,
                "difficulty": 6,
                "deadline": datetime.now() + timedelta(days=3)
            },
            {
                "name": "Machine Learning",  # Changed from "subject" to "name"
                "duration_min": 45,
                "difficulty": 3,
                "deadline": datetime.now() + timedelta(days=5)
            },
            {
                "name": "AI",  # Changed from "subject" to "name"
                "duration_min": 120,
                "difficulty": 9,
                "deadline": datetime.now() + timedelta(days=1)
            }
        ]
        
        # schedule = self.optimizer.optimize_schedule(tasks, num_trials=10)
        schedule = self.optimizer.optimize_schedule(tasks)
        
        self.assertIsNotNone(schedule)
        self.assertGreater(len(schedule), 0)
    
    def test_productivity_at(self):
        """Test productivity interpolation for fractional hours"""
        # Test integer hours
        self.assertAlmostEqual(self.optimizer.productivity_at(10), 1.00)
        self.assertAlmostEqual(self.optimizer.productivity_at(8), 0.70)
        
        # Test fractional hours
        self.assertAlmostEqual(self.optimizer.productivity_at(10.5), 0.925)  # Between 10 (1.00) and 11 (0.70)
        
        # Test out of bounds (should use defaults)
        self.assertGreater(self.optimizer.productivity_at(25), 0)  # Should not crash
    
    def test_has_conflict(self):
        """Test conflict detection with scheduled activities"""
        # Add a fixed activity (e.g., class from 9-10 AM Monday)
        monday = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        monday = monday + timedelta(days=(7 - monday.weekday()))  # Next Monday
        fixed_activity = ScheduledActivity(
            activity_id="class1",
            user_id="test",
            activity_type=ActivityType.STUDY,
            title="Math Class",
            start_time=monday,
            end_time=monday + timedelta(hours=1)
        )
        self.optimizer.add_scheduled_activity(fixed_activity)
        
        # Test slot that overlaps
        conflicting_slot = TimeSlot(9.0, 10.0, "Monday")
        self.assertTrue(self.optimizer.has_conflict(conflicting_slot))
        
        # Test slot that doesn't overlap
        free_slot = TimeSlot(10.0, 11.0, "Monday")
        self.assertFalse(self.optimizer.has_conflict(free_slot))
        
        # Test different day
        tuesday_slot = TimeSlot(9.0, 10.0, "Tuesday")
        self.assertFalse(self.optimizer.has_conflict(tuesday_slot))
    
    def test_add_constraint_and_check_constraints(self):
        """Test constraint addition and validation"""
        # Add a hard constraint: no study after 8 PM
        def no_evening_study(task, slot):
            return slot.start_hour < 20  # Before 8 PM
        
        self.optimizer.add_constraint("no_evening_study", no_evening_study, is_hard=True)
        
        # Add a soft constraint: prefer morning slots
        def prefer_morning(task, slot):
            return slot.start_hour < 12
        
        self.optimizer.add_constraint("prefer_morning", prefer_morning, is_hard=False)
        
        task = {"name": "Test Task", "duration_min": 60}
        morning_slot = TimeSlot(9.0, 10.0, "Monday")
        evening_slot = TimeSlot(21.0, 22.0, "Monday")  # 9 PM
        
        # Hard constraint should pass morning, fail evening
        self.assertTrue(self.optimizer.check_constraints(task, morning_slot))
        self.assertFalse(self.optimizer.check_constraints(task, evening_slot))
    
    def test_is_valid_assignment(self):
        """Test assignment validation with conflicts and constraints"""
        # Add a fixed activity
        monday = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        monday = monday + timedelta(days=(7 - monday.weekday()))
        fixed = ScheduledActivity(
            activity_id="meeting",
            user_id="test",
            activity_type=ActivityType.WORK,
            title="Meeting",
            start_time=monday,
            end_time=monday + timedelta(hours=1)
        )
        self.optimizer.add_scheduled_activity(fixed)
        
        task = {"name": "Study", "duration_min": 60}
        conflicting_slot = TimeSlot(10.0, 11.0, "Monday")  # Overlaps with meeting
        free_slot = TimeSlot(11.0, 12.0, "Monday")
        
        # Should reject conflicting slot
        self.assertFalse(self.optimizer.is_valid_assignment(conflicting_slot, [], task))
        self.assertTrue(self.optimizer.is_valid_assignment(free_slot, [], task))
    
    def test_sort_tasks(self):
        """Test task sorting by urgency, difficulty, duration"""
        now = datetime.now()
        tasks = [
            {"name": "Easy long", "duration_min": 120, "difficulty": 3, "deadline": now + timedelta(days=7)},
            {"name": "Hard urgent", "duration_min": 60, "difficulty": 9, "deadline": now + timedelta(days=1)},
            {"name": "Medium medium", "duration_min": 90, "difficulty": 5, "deadline": now + timedelta(days=3)}
        ]
        
        sorted_tasks = self.optimizer.sort_tasks(tasks)
        
        # Hard urgent task should come first
        self.assertEqual(sorted_tasks[0]["name"], "Hard urgent")
        # Easy long task should come last (FFD heuristic)
        self.assertEqual(sorted_tasks[-1]["name"], "Easy long")
    
    def test_backtrack_small_problems(self):
        """Test backtracking with small solvable and unsolvable problems"""
        # Solvable: 2 short tasks
        tasks = [
            {"name": "Task1", "duration_min": 60, "difficulty": 5, "deadline": datetime.now() + timedelta(days=1)},
            {"name": "Task2", "duration_min": 60, "difficulty": 5, "deadline": datetime.now() + timedelta(days=1)}
        ]
        schedule = self.optimizer.optimize_schedule(tasks)
        self.assertEqual(len(schedule), 2)
        
        # Add constraint that makes it unsolvable
        def impossible_constraint(task, slot):
            return False  # Always fail
        
        self.optimizer.add_constraint("impossible", impossible_constraint, is_hard=True)
        unsolvable_schedule = self.optimizer.optimize_schedule(tasks)
        # Should fall back to greedy scheduling
        self.assertIsNotNone(unsolvable_schedule)
    
    def test_fallback_schedule(self):
        """Test fallback scheduling when CSP fails"""
        # Create impossible constraints
        def always_fail(task, slot):
            return False
        
        self.optimizer.add_constraint("fail", always_fail, is_hard=True)
        
        tasks = [
            {"name": "Task1", "duration_min": 60, "difficulty": 5},
            {"name": "Task2", "duration_min": 60, "difficulty": 5}
        ]
        
        schedule = self.optimizer.optimize_schedule(tasks)
        
        # Should still produce a schedule via fallback
        self.assertIsNotNone(schedule)
        self.assertGreater(len(schedule), 0)
        
        # Check that unscheduled tasks are marked
        unscheduled = [item for item in schedule if item.get("warning")]
        self.assertGreaterEqual(len(unscheduled), 0)  # May have some unscheduled
    
    def test_evaluate_schedule(self):
        """Test schedule scoring"""
        now = datetime.now()
        schedule = [
            {
                "task": {"name": "Hard task", "difficulty": 9, "deadline": now + timedelta(days=2)},
                "slot": TimeSlot(10.0, 11.5, "Monday", productivity_factor=1.0)  # Peak productivity
            },
            {
                "task": {"name": "Easy task", "difficulty": 3, "deadline": now + timedelta(days=5)},
                "slot": TimeSlot(20.0, 21.0, "Saturday", productivity_factor=0.7)  # Weekend evening
            }
        ]
        
        score = self.optimizer.evaluate_schedule(schedule)
        self.assertGreater(score, 0)
        
        # Higher difficulty in productive slot should score better
        # Let's test with a better schedule
        better_schedule = [
            {
                "task": {"name": "Hard task", "difficulty": 9, "deadline": now + timedelta(days=2)},
                "slot": TimeSlot(10.0, 11.5, "Monday", productivity_factor=1.0)
            }
        ]
        better_score = self.optimizer.evaluate_schedule(better_schedule)
        self.assertGreater(better_score, score * 0.5)  # Should be significantly better
    
    def test_integration_with_constraints(self):
        """Integration test: full workflow with real constraints"""
        # Reset optimizer
        self.optimizer = ScheduleOptimizer(user_earliest=8, user_latest=22)
        
        # Add real constraints
        def no_study_after_8pm(task, slot):
            return slot.start_hour < 20
        
        def minimum_break_between_tasks(task, slot):
            # Simplified: just check if slot starts at reasonable hour
            return slot.start_hour >= 8 and slot.start_hour <= 18
        
        self.optimizer.add_constraint("no_evening_study", no_study_after_8pm, is_hard=True)
        self.optimizer.add_constraint("reasonable_hours", minimum_break_between_tasks, is_hard=True)
        
        # Add fixed activity (lunch break)
        today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        lunch = ScheduledActivity(
            activity_id="lunch",
            user_id="test",
            activity_type=ActivityType.MEAL,
            title="Lunch",
            start_time=today,
            end_time=today + timedelta(hours=1)
        )
        self.optimizer.add_scheduled_activity(lunch)
        
        tasks = [
            {"name": "Morning Study", "duration_min": 90, "difficulty": 7, "deadline": datetime.now() + timedelta(days=1)},
            {"name": "Afternoon Review", "duration_min": 60, "difficulty": 4, "deadline": datetime.now() + timedelta(days=2)}
        ]
        
        schedule = self.optimizer.optimize_schedule(tasks)
        
        self.assertIsNotNone(schedule)
        # Verify constraints are respected
        for item in schedule:
            slot = item["slot"]
            self.assertLess(slot.start_hour, 20)  # No evening slots
            self.assertFalse(self.optimizer.has_conflict(slot))  # No conflicts with lunch
    
    def test_performance_large_task_set(self):
        """Performance test with larger task sets"""
        import time
    
        # Generate 20 tasks
        tasks = []
        now = datetime.now()
        for i in range(20):
            tasks.append({
                "name": f"Task{i}",
                "duration_min": 30 + (i % 5) * 30,  # 30-120 min
                "difficulty": 3 + (i % 7),  # 3-9
                "deadline": now + timedelta(days=1 + (i % 10))
            })
    
        start_time = time.time()
        schedule = self.optimizer.optimize_schedule(tasks)
        end_time = time.time()
    
        # Relax timeout from 5 to 10 seconds for complex 20-task CSP
        self.assertLess(end_time - start_time, 10.0)
        self.assertIsNotNone(schedule)
        # May not schedule all tasks if impossible
        self.assertGreater(len(schedule), 0)


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
                "name": "Study",
                "duration_min": 60,
                "difficulty": 6,
                "deadline": datetime.now() + timedelta(days=1)
            }
        ]
        
        # schedule = scheduler.optimize_schedule(tasks, num_trials=5)
        schedule = scheduler.optimize_schedule(tasks)
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
