"""Tests for newly implemented high-priority AI modules and API endpoints."""

import os
import tempfile
import unittest
from datetime import datetime, timezone

from ai_modules.goal_tracker import GoalTracker
from ai_modules.health_risk_assessor import HealthRiskAssessor
from ai_modules.recovery_predictor import RecoveryFeatures, RecoveryPredictor
from ai_modules.sleep_quality_predictor import SleepFeatures, SleepQualityPredictor
from ai_modules.weekly_digest import WeeklyDigestGenerator
from api.blueprints import state
from api.routes import app
from models.user_profile import BiologicalSex, Goal, UserProfile


class TestHealthRiskAssessor(unittest.TestCase):
    def setUp(self):
        self.profile = UserProfile(
            user_id="risk_test_user",
            name="Risk Tester",
            age=30,
            weight_kg=70.0,
            height_cm=175.0,
            biological_sex=BiologicalSex.MALE,
            goals=[Goal.GENERAL_WELLNESS],
            target_calories=2000,
            water_target_ml=2500,
        )

    def test_bmi_normal(self):
        assessor = HealthRiskAssessor(self.profile, [], [])
        report = assessor.assess()
        bmi_warnings = [w for w in report["warnings"] if w["field"] == "bmi"]
        self.assertEqual(len(bmi_warnings), 0)
        self.assertEqual(report["overall_risk"], "none")

    def test_bmi_underweight(self):
        self.profile.current_weight_kg = 50.0  # BMI ~ 16.3
        assessor = HealthRiskAssessor(self.profile, [], [])
        report = assessor.assess()
        bmi_warnings = [w for w in report["warnings"] if w["field"] == "bmi"]
        self.assertEqual(len(bmi_warnings), 1)
        self.assertEqual(bmi_warnings[0]["severity"], "medium")

    def test_bmi_obese(self):
        self.profile.current_weight_kg = 100.0  # BMI ~ 32.7
        assessor = HealthRiskAssessor(self.profile, [], [])
        report = assessor.assess()
        bmi_warnings = [w for w in report["warnings"] if w["field"] == "bmi"]
        self.assertEqual(len(bmi_warnings), 1)
        self.assertEqual(bmi_warnings[0]["severity"], "high")

    def test_calorie_surplus_sustained(self):
        # 3 consecutive days with 3200 kcal (> 35% above 2000)
        heavy_log = {
            "meals": [
                {"food_items": [{"nutrition_info": {"calories": 3200.0, "protein_g": 90.0}}]}
            ]
        }
        assessor = HealthRiskAssessor(self.profile, [heavy_log, heavy_log, heavy_log], [])
        report = assessor.assess()
        cal_warnings = [w for w in report["warnings"] if "calorie" in w["field"]]
        self.assertTrue(len(cal_warnings) >= 1)
        self.assertEqual(cal_warnings[0]["severity"], "high")

    def test_sleep_deficit(self):
        sleep_logs = [
            {"duration_hours": 5.0},
            {"duration_hours": 5.5},
            {"duration_hours": 4.8},
        ]
        assessor = HealthRiskAssessor(self.profile, [], [], sleep_logs=sleep_logs)
        report = assessor.assess()
        sleep_warns = [w for w in report["warnings"] if w["field"] == "sleep"]
        self.assertEqual(len(sleep_warns), 1)
        self.assertEqual(sleep_warns[0]["severity"], "high")


class TestSleepQualityPredictor(unittest.TestCase):
    def setUp(self):
        self.predictor = SleepQualityPredictor()

    def test_predict_range(self):
        feat = SleepFeatures(
            bedtime_hour=23.0,
            sleep_duration_h=8.0,
            caffeine_servings=1,
            exercise_minutes=45,
            screen_time_bedtime_min=10,
            stress_level=2,
        )
        score = self.predictor.predict(feat)
        self.assertGreaterEqual(score, 1)
        self.assertLessEqual(score, 10)

    def test_hygiene_comparison(self):
        good_feat = SleepFeatures(22.5, 8.0, 0, 45, 0, 2)
        bad_feat = SleepFeatures(3.0, 4.0, 5, 0, 60, 9)
        score_good = self.predictor.predict(good_feat)
        score_bad = self.predictor.predict(bad_feat)
        self.assertGreater(score_good, score_bad)

    def test_recommendations(self):
        bad_feat = SleepFeatures(2.0, 5.0, 4, 0, 45, 8)
        recs = self.predictor.get_sleep_hygiene_recommendations(bad_feat)
        self.assertTrue(len(recs) >= 3)

    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tf:
            temp_path = tf.name
        try:
            self.predictor.save_model(temp_path)
            loaded = SleepQualityPredictor.load_model(temp_path)
            self.assertTrue(loaded.is_trained)
            feat = SleepFeatures(23.0, 7.5, 1, 30, 15, 3)
            self.assertEqual(self.predictor.predict(feat), loaded.predict(feat))
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestRecoveryPredictor(unittest.TestCase):
    def setUp(self):
        self.predictor = RecoveryPredictor()

    def test_predict_and_assessment(self):
        feat = RecoveryFeatures(
            sleep_quality=8.5,
            sleep_hours=8.0,
            workout_load_3d_minutes=60,
            stress_level=2,
            current_energy=9,
            days_since_rest=1,
        )
        report = self.predictor.assess_readiness(feat)
        self.assertIn("readiness_score", report)
        self.assertGreaterEqual(report["readiness_score"], 7)
        self.assertIn(report["status"], ["optimal", "good", "reduced", "exhausted"])
        self.assertIn("recommendation", report)

    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tf:
            temp_path = tf.name
        try:
            self.predictor.save_model(temp_path)
            loaded = RecoveryPredictor.load_model(temp_path)
            self.assertTrue(loaded.is_trained)
            feat = RecoveryFeatures(7.0, 7.0, 90, 4, 7, 2)
            self.assertEqual(self.predictor.predict(feat), loaded.predict(feat))
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestGoalTracker(unittest.TestCase):
    def setUp(self):
        self.profile = UserProfile(
            user_id="goal_user",
            name="Goal Tester",
            age=26,
            weight_kg=80.0,
            height_cm=180.0,
            biological_sex=BiologicalSex.MALE,
            goals=[Goal.WEIGHT_LOSS],
            target_calories=2000,
            target_weight_kg=72.0,
            weekly_exercise_target_minutes=150,
        )
        self.profile.current_weight_kg = 76.0

    def test_milestones_summary(self):
        tracker = GoalTracker(self.profile, [], [])
        res = tracker.get_milestone_summary()
        self.assertEqual(res["user_id"], "goal_user")
        milestones = {m["type"]: m for m in res["milestones"]}

        self.assertIn("weight", milestones)
        weight_m = milestones["weight"]
        # Progress: started 80kg, now 76kg, target 72kg => (4 / 8) * 100 = 50.0%
        self.assertEqual(weight_m["progress_pct"], 50.0)
        self.assertEqual(weight_m["status"], "in_progress")
        self.assertIsNotNone(weight_m["projected_completion_date"])

        self.assertIn("exercise", milestones)
        self.assertIn("nutrition", milestones)


class TestWeeklyDigestGenerator(unittest.TestCase):
    def test_generate_digest(self):
        user = UserProfile(
            user_id="digest_user",
            name="Digest User",
            age=28,
            weight_kg=75.0,
            height_cm=178.0,
            target_calories=2100,
        )
        daily_logs = [{
            "meals": [
                {"food_items": [{"nutrition_info": {"calories": 2050.0, "protein_g": 120.0, "carbs_g": 210.0, "fat_g": 60.0}}]}
            ]
        }]
        activity_logs = [
            {
                "activity_type": "exercise",
                "duration_minutes": 45,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "energy_after": 8,
            }
        ]
        sleep_logs = [
            {"duration_hours": 7.5, "quality_score": 8}
        ]

        generator = WeeklyDigestGenerator(user, daily_logs, activity_logs, sleep_logs)
        digest = generator.generate()

        self.assertEqual(digest["user_id"], "digest_user")
        self.assertIn("period", digest)
        self.assertIn("highlights", digest)
        self.assertEqual(digest["nutrition"]["avg_calories"], 2050.0)
        self.assertEqual(digest["activity"]["workout_minutes"], 45)
        self.assertEqual(digest["sleep"]["avg_duration_hours"], 7.5)
        self.assertIn("goals", digest)
        self.assertIn("health_risks", digest)


class TestNewEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.user_id = "test_endpoint_user"
        user = UserProfile(
            user_id=self.user_id,
            name="Endpoint User",
            age=25,
            weight_kg=70.0,
            height_cm=175.0,
            biological_sex=BiologicalSex.MALE,
            goals=[Goal.WEIGHT_LOSS],
            target_calories=2000,
            password_hash="fake_hash",
        )
        state.users[self.user_id] = user

    def test_health_risks_endpoint(self):
        resp = self.client.get(f"/api/health-risks/{self.user_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("warnings", data)
        self.assertIn("overall_risk", data)

    def test_recovery_endpoint(self):
        resp = self.client.get(f"/api/recovery/{self.user_id}?sleep_quality=8&energy_level=7")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("readiness_score", data)
        self.assertIn("recommendation", data)

    def test_goals_endpoint(self):
        resp = self.client.get(f"/api/goals/{self.user_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("milestones", data)

    def test_digest_endpoint(self):
        resp = self.client.get(f"/api/digest/{self.user_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("highlights", data)
        self.assertIn("nutrition", data)
        self.assertIn("activity", data)

    def test_sleep_predict_endpoint(self):
        resp = self.client.get(f"/api/sleep/predict/{self.user_id}?duration_hours=7.5&stress_level=3")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("predicted_sleep_quality", data)
        self.assertIn("recommendations", data)

    def test_sleep_log_requires_auth(self):
        resp = self.client.post("/api/sleep/log", json={
            "user_id": self.user_id,
            "duration_hours": 8.0,
        })
        self.assertEqual(resp.status_code, 401)

    def test_sleep_log_with_auth(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user_id
            sess["csrf_token"] = "test_csrf_token_val"

        resp = self.client.post(
            "/api/sleep/log",
            headers={"X-CSRF-Token": "test_csrf_token_val"},
            json={
                "user_id": self.user_id,
                "duration_hours": 7.5,
                "quality_score": 8,
                "stress_level": 3,
                "notes": "Fell asleep quickly",
            },
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["sleep_log"]["duration_hours"], 7.5)

        # Check logs retrieval
        logs_resp = self.client.get(f"/api/sleep/logs/{self.user_id}")
        self.assertEqual(logs_resp.status_code, 200)
        logs_data = logs_resp.get_json()
        self.assertGreaterEqual(logs_data["count"], 1)


if __name__ == "__main__":
    unittest.main()
