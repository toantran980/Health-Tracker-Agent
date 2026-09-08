"""
tests/test_comparative_analytics.py

Unit and integration tests for Comparative Analytics (Phase 2):
- Week-over-week trend calculations
- Multi-domain analytics (activity, sleep, nutrition, productivity)
- Confidence scoring based on data availability
- Human-readable explanations for trend changes
"""

import unittest
import uuid
from datetime import datetime, timedelta, timezone

from api.blueprints import state
from api.routes import app
from models.activity import ActivityLog, ActivityType


class TestComparativeAnalytics(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        state.users.clear()
        state.activity_logs.clear()
        state.sleep_logs.clear()
        state.daily_logs.clear()
        state.productivity_sessions.clear()
        
        # Create test user with unique ID to avoid conflicts
        self.user_id = f"test_comparative_user_{uuid.uuid4().hex[:8]}"
        self.password = "test_password_123"
        create_res = self.client.post('/api/user/create', json={
            "user_id": self.user_id,
            "name": "Test User",
            "password": self.password,
        })
        self.assertEqual(create_res.status_code, 201)
        
        login_res = self.client.post('/api/auth/login', json={
            "user_id": self.user_id,
            "password": self.password
        })
        self.assertEqual(login_res.status_code, 200)
        self.csrf_token = login_res.get_json().get("csrf_token")
        self.headers = {"X-CSRF-Token": self.csrf_token}
    
    def tearDown(self):
        if self.user_id in state.users:
            del state.users[self.user_id]
        if self.user_id in state.activity_logs:
            del state.activity_logs[self.user_id]
        if self.user_id in state.sleep_logs:
            del state.sleep_logs[self.user_id]
        if self.user_id in state.daily_logs:
            del state.daily_logs[self.user_id]
        if self.user_id in state.productivity_sessions:
            del state.productivity_sessions[self.user_id]
        
        if state.mongo_store.enabled:
            state.mongo_store.delete_user_data(self.user_id)
        
        with self.client.session_transaction() as sess:
            sess.clear()
    
    def test_comparative_analytics_endpoint_exists(self):
        """Verify the comparative analytics endpoint is accessible."""
        res = self.client.get(f'/api/comparative-analytics/{self.user_id}', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("user_id", data)
        self.assertEqual(data["user_id"], self.user_id)
        self.assertIn("analysis_period", data)
        self.assertIn("domains", data)
    
    def test_comparative_analytics_with_no_data(self):
        """Test analytics endpoint returns appropriate structure with no data."""
        res = self.client.get(f'/api/comparative-analytics/{self.user_id}', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        # Should return empty weekly data for each domain
        for domain in ["activity", "sleep", "nutrition", "productivity"]:
            self.assertIn(domain, data["domains"])
            self.assertEqual(data["domains"][domain]["weekly_data"], [])
            self.assertEqual(data["domains"][domain]["week_over_week_trends"], [])
    
    def test_activity_weekly_stats_calculation(self):
        """Test that activity data is correctly aggregated by week."""
        now = datetime.now(timezone.utc)
        
        for i in range(5):
            ts = now - timedelta(days=14 + i)  # 2 weeks ago
            log = ActivityLog(
                log_id=f"act_week1_{i}",
                user_id=self.user_id,
                activity_type=ActivityType.EXERCISE,
                timestamp=ts,
                duration_minutes=30 + i * 5,
                energy_after=7 + i,
            )
            state.activity_logs.setdefault(self.user_id, []).append(log.to_dict())
        
        for i in range(5):
            ts = now - timedelta(days=7 + i)  # 1 week ago
            log = ActivityLog(
                log_id=f"act_week2_{i}",
                user_id=self.user_id,
                activity_type=ActivityType.EXERCISE,
                timestamp=ts,
                duration_minutes=40 + i * 5,
                energy_after=8 + i,
            )
            state.activity_logs.setdefault(self.user_id, []).append(log.to_dict())
        
        res = self.client.get(f'/api/comparative-analytics/{self.user_id}?weeks=3', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        activity_data = data["domains"]["activity"]
        self.assertGreater(len(activity_data["weekly_data"]), 0)
        
        for week in activity_data["weekly_data"]:
            self.assertIn("week", week)
            self.assertIn("week_start", week)
            self.assertIn("week_end", week)
            self.assertIn("count", week)
            self.assertIn("duration_minutes_avg", week)
            self.assertIn("energy_after_avg", week)
    
    def test_week_over_week_trend_calculation(self):
        """Test that week-over-week changes are calculated correctly."""
        now = datetime.now(timezone.utc)
        
        # Create data with clear trend - increasing duration
        for i in range(3):
            ts = now - timedelta(days=14 + i)
            log = ActivityLog(
                log_id=f"act_early_{i}",
                user_id=self.user_id,
                activity_type=ActivityType.EXERCISE,
                timestamp=ts,
                duration_minutes=20,
                energy_after=5,
            )
            state.activity_logs.setdefault(self.user_id, []).append(log.to_dict())
        
        for i in range(3):
            ts = now - timedelta(days=7 + i)
            log = ActivityLog(
                log_id=f"act_recent_{i}",
                user_id=self.user_id,
                activity_type=ActivityType.EXERCISE,
                timestamp=ts,
                duration_minutes=40,
                energy_after=8,
            )
            state.activity_logs.setdefault(self.user_id, []).append(log.to_dict())
        
        res = self.client.get(f'/api/comparative-analytics/{self.user_id}?weeks=3', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        activity_trends = data["domains"]["activity"]["week_over_week_trends"]
        self.assertGreater(len(activity_trends), 0)
        
        latest_trend = activity_trends[-1]
        self.assertIn("week", latest_trend)
        self.assertIn("metrics", latest_trend)
        self.assertIn("duration_minutes", latest_trend["metrics"])
        
        duration_metric = latest_trend["metrics"]["duration_minutes"]
        self.assertIn("current_avg", duration_metric)
        self.assertIn("previous_avg", duration_metric)
        self.assertIn("change_pct", duration_metric)
        self.assertIn("direction", duration_metric)
        self.assertIn("explanation", duration_metric)
    
    def test_confidence_scoring_low_data(self):
        """Test confidence scoring with limited data."""
        now = datetime.now(timezone.utc)
        log = ActivityLog(
            log_id="single_log",
            user_id=self.user_id,
            activity_type=ActivityType.EXERCISE,
            timestamp=now - timedelta(days=1),
            duration_minutes=30,
            energy_after=7,
        )
        state.activity_logs.setdefault(self.user_id, []).append(log.to_dict())
        
        res = self.client.get(f'/api/comparative-analytics/{self.user_id}?weeks=4', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        confidence = data["domains"]["activity"]["confidence"]
        self.assertIn("level", confidence)
        self.assertIn("reason", confidence)
        self.assertIn("data_points", confidence)
        self.assertIn("weeks_with_data", confidence)
        
        self.assertEqual(confidence["data_points"], 1)
    
    def test_confidence_scoring_high_data(self):
        """Test confidence scoring with substantial data."""
        # Add substantial data across multiple weeks
        now = datetime.now(timezone.utc)
        
        for week in range(4):
            for day in range(7):
                ts = now - timedelta(weeks=week, days=day)
                log = ActivityLog(
                    log_id=f"act_{week}_{day}",
                    user_id=self.user_id,
                    activity_type=ActivityType.EXERCISE,
                    timestamp=ts,
                    duration_minutes=30 + week * 5,
                    energy_after=7,
                )
                state.activity_logs.setdefault(self.user_id, []).append(log.to_dict())
        
        res = self.client.get(f'/api/comparative-analytics/{self.user_id}?weeks=4', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        confidence = data["domains"]["activity"]["confidence"]
        self.assertGreater(confidence["data_points"], 20)
        self.assertIn(confidence["level"], ["medium", "high"])
    
    def test_domain_filtering(self):
        """Test that domains parameter correctly filters which domains are analyzed."""
        res = self.client.get(
            f'/api/comparative-analytics/{self.user_id}?domains=activity,sleep',
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        self.assertIn("activity", data["domains"])
        self.assertIn("sleep", data["domains"])
        self.assertNotIn("nutrition", data["domains"])
        self.assertNotIn("productivity", data["domains"])
    
    def test_weeks_parameter_validation(self):
        """Test that weeks parameter is properly validated."""
        # Test minimum weeks (should return 400 for invalid input)
        res = self.client.get(
            f'/api/comparative-analytics/{self.user_id}?weeks=1',
            headers=self.headers
        )
        self.assertEqual(res.status_code, 400)
        
        res = self.client.get(
            f'/api/comparative-analytics/{self.user_id}?weeks=2',
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["analysis_period"]["weeks_analyzed"], 2)
        
        # Test maximum weeks (should return 400 for invalid input)
        res = self.client.get(
            f'/api/comparative-analytics/{self.user_id}?weeks=20',
            headers=self.headers
        )
        self.assertEqual(res.status_code, 400)
        
        res = self.client.get(
            f'/api/comparative-analytics/{self.user_id}?weeks=12',
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["analysis_period"]["weeks_analyzed"], 12)
    
    def test_human_readable_explanations(self):
        """Test that trend changes generate human-readable explanations."""
        now = datetime.now(timezone.utc)
        
        # Create data that should generate "increased" explanation
        for i in range(3):
            ts = now - timedelta(days=14 + i)
            log = ActivityLog(
                log_id=f"act_old_{i}",
                user_id=self.user_id,
                activity_type=ActivityType.EXERCISE,
                timestamp=ts,
                duration_minutes=20,
                energy_after=5,
            )
            state.activity_logs.setdefault(self.user_id, []).append(log.to_dict())
        
        for i in range(3):
            ts = now - timedelta(days=7 + i)
            log = ActivityLog(
                log_id=f"act_new_{i}",
                user_id=self.user_id,
                activity_type=ActivityType.EXERCISE,
                timestamp=ts,
                duration_minutes=50,
                energy_after=8,
            )
            state.activity_logs.setdefault(self.user_id, []).append(log.to_dict())
        
        res = self.client.get(f'/api/comparative-analytics/{self.user_id}?weeks=3', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        activity_trends = data["domains"]["activity"]["week_over_week_trends"]
        if activity_trends:
            latest_trend = activity_trends[-1]
            explanation = latest_trend["metrics"]["duration_minutes"]["explanation"]
            self.assertIsInstance(explanation, str)
            self.assertGreater(len(explanation), 0)
    
    def test_authentication_required(self):
        """Test that comparative analytics requires authentication."""
        # Create another user but don't login
        other_user_id = f"other_test_user_{uuid.uuid4().hex[:8]}"
        self.client.post('/api/user/create', json={
            "user_id": other_user_id,
            "name": "Other User",
            "password": "password123",
        })
        
        res = self.client.get(f'/api/comparative-analytics/{other_user_id}')
        self.assertEqual(res.status_code, 401)
    
    def test_sleep_domain_analytics(self):
        """Test that sleep domain analytics work correctly."""
        now = datetime.now(timezone.utc)
        
        # Add sleep logs using the dict structure expected by the API
        for i in range(5):
            ts = now - timedelta(days=i)
            sleep_log = {
                "log_id": f"sleep_{i}",
                "user_id": self.user_id,
                "timestamp": ts.isoformat(),
                "duration_hours": 7.0 + i * 0.5,
                "quality_score": 7 + i,
                "bedtime_hour": 23.0,
                "caffeine_servings": 0,
                "exercise_minutes": 30,
                "screen_time_bedtime_min": 60,
                "stress_level": 5,
                "notes": ""
            }
            state.sleep_logs.setdefault(self.user_id, []).append(sleep_log)
        
        res = self.client.get(
            f'/api/comparative-analytics/{self.user_id}?domains=sleep',
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        sleep_data = data["domains"]["sleep"]
        self.assertIn("weekly_data", sleep_data)
        self.assertIn("week_over_week_trends", sleep_data)
        self.assertIn("confidence", sleep_data)
    
    def test_nutrition_domain_analytics(self):
        """Test that nutrition domain analytics work correctly."""
        from models.meal import DailyNutritionLog, Meal, MealType
        
        now = datetime.now(timezone.utc)
        
        for i in range(10):
            date_str = (now - timedelta(days=i)).date().isoformat()
            date_obj = datetime.fromisoformat(date_str)
            
            meal = Meal(
                meal_id=f"meal_{i}",
                user_id=self.user_id,
                meal_type=MealType.LUNCH,
                timestamp=date_obj,
                food_items=[],
                notes=""
            )
            
            daily_log = DailyNutritionLog(
                log_id=f"daily_{i}",
                user_id=self.user_id,
                date=date_obj,
                meals=[meal],
                water_intake_ml=2000 + i * 100
            )
            
            state.daily_logs.setdefault(self.user_id, {})[date_str] = daily_log
        
        res = self.client.get(
            f'/api/comparative-analytics/{self.user_id}?domains=nutrition',
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        
        nutrition_data = data["domains"]["nutrition"]
        self.assertIn("weekly_data", nutrition_data)
        self.assertIn("week_over_week_trends", nutrition_data)
        self.assertIn("confidence", nutrition_data)


if __name__ == "__main__":
    unittest.main()