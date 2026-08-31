"""API blueprint integration tests (auth flow, protected endpoints, persistence)."""

import os
import unittest
from unittest import mock

# Fail fast when MongoDB is unreachable so the in-memory fallback is used.
os.environ.setdefault("MONGO_CONNECT_RETRIES", "1")
os.environ.setdefault("MONGO_URI", "mongodb://127.0.0.1:1")

from api.routes import app  # noqa: E402  (registers all blueprints)
from api.rate_limiter import RateLimiter, build_limiter  # noqa: E402
from api.blueprints import state  # noqa: E402
import api.blueprints.external as external_module  # noqa: E402
import config  # noqa: E402


def make_client():
    app.config["TESTING"] = True
    return app.test_client()


def reset_state():
    state.users.clear()
    state.daily_logs.clear()
    state.schedule_history.clear()
    state.productivity_sessions.clear()
    state.activity_logs.clear()


class TestRateLimiter(unittest.TestCase):
    """Unit tests for the sliding-window rate limiter."""

    def test_allows_up_to_limit(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        self.assertTrue(limiter.allow("client-1"))
        self.assertTrue(limiter.allow("client-1"))
        self.assertTrue(limiter.allow("client-1"))

    def test_denies_beyond_limit(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        self.assertTrue(limiter.allow("a"))
        self.assertTrue(limiter.allow("a"))
        self.assertFalse(limiter.allow("a"))

    def test_clients_isolated(self):
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        self.assertTrue(limiter.allow("x"))
        self.assertFalse(limiter.allow("x"))
        self.assertTrue(limiter.allow("y"))

    def test_window_expires(self):
        limiter = RateLimiter(max_requests=1, window_seconds=0.2)
        self.assertTrue(limiter.allow("a"))
        self.assertFalse(limiter.allow("a"))
        import time
        time.sleep(0.3)
        self.assertTrue(limiter.allow("a"))

    def test_status_reports_remaining_and_reset(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        s0 = limiter.status("c")
        self.assertEqual(s0["limit"], 3)
        self.assertEqual(s0["remaining"], 3)
        self.assertGreater(s0["reset"], 0)

        limiter.allow("c")
        limiter.allow("c")
        s = limiter.status("c")
        self.assertEqual(s["remaining"], 1)
        self.assertGreater(s["reset"], 0)
        self.assertLessEqual(s["reset"], 60)

    def test_build_limiter_from_config_memory(self):
        """build_limiter honours the config-driven defaults for memory backend."""
        limiter = build_limiter(
            max_requests=config.EXTERNAL_API_RATE_LIMIT,
            window_seconds=config.EXTERNAL_API_RATE_WINDOW_SECONDS,
            backend="memory",
            redis_url=config.REDIS_URL,
        )
        self.assertIsInstance(limiter, RateLimiter)
        self.assertEqual(limiter.max_requests, config.EXTERNAL_API_RATE_LIMIT)
        self.assertEqual(limiter.window_seconds, config.EXTERNAL_API_RATE_WINDOW_SECONDS)

    def test_build_limiter_unknown_backend(self):
        with self.assertRaises(ValueError):
            build_limiter(5, 60, backend="cassandra", redis_url="")


class TestAuthFlow(unittest.TestCase):
    USER = {
        "name": "Test User",
        "age": 25,
        "weight_kg": 70,
        "height_cm": 175,
        "biological_sex": "male",
        "goals": ["general_wellness"],
        "target_calories": 2200,
        "target_protein_g": 120,
        "target_carbs_g": 220,
        "target_fat_g": 70,
        "password": "secret123",
    }

    def setUp(self):
        reset_state()
        self.client = make_client()
        self.user_id = None
        resp = self.client.post("/api/user/create", json=self.USER)
        self.assertEqual(resp.status_code, 201)
        self.user_id = resp.get_json()["user_id"]

    def test_me_before_login(self):
        data = self.client.get("/api/auth/me").get_json()
        self.assertFalse(data["authenticated"])

    def test_water_target_customization(self):
        resp = make_client().post("/api/user/create", json=dict(self.USER, water_target_ml=3000))
        self.assertEqual(resp.status_code, 201)
        body = resp.get_json()
        self.assertEqual(body["user"]["water_target_ml"], 3000)

        fetched = make_client().get(f"/api/user/{body['user_id']}").get_json()
        self.assertEqual(fetched["water_target_ml"], 3000)

    def test_water_target_defaults_to_2500(self):
        resp = make_client().post("/api/user/create", json=dict(self.USER))
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["user"]["water_target_ml"], 2500)

    def test_create_requires_password_length(self):
        data = dict(self.USER, password="123")
        resp = make_client().post("/api/user/create", json=data)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["code"], "PASSWORD_TOO_SHORT")

    def test_wrong_password_denied(self):
        resp = self.client.post("/api/auth/login", json={
            "user_id": self.user_id, "password": "wrongpass",
        })
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["code"], "INVALID_CREDENTIALS")

    def test_login_logout_flow(self):
        resp = self.client.post("/api/auth/login", json={
            "user_id": self.user_id, "password": self.USER["password"],
        })
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertEqual(body["status"], "authenticated")
        self.assertEqual(body["user_id"], self.user_id)
        self.assertIn("csrf_token", body)

        me = self.client.get("/api/auth/me").get_json()
        self.assertTrue(me["authenticated"])
        self.assertEqual(me["user_id"], self.user_id)
        self.assertIn("csrf_token", me)

        logout = self.client.post("/api/auth/logout", headers={"X-CSRF-Token": body["csrf_token"]})
        self.assertEqual(logout.status_code, 200)
        me = self.client.get("/api/auth/me").get_json()
        self.assertFalse(me["authenticated"])

    def test_user_response_never_leaks_password_hash(self):
        resp = self.client.get(f"/api/user/{self.user_id}")
        self.assertEqual(resp.status_code, 200)
        raw = (resp.get_data(as_text=True) + "").lower()
        self.assertNotIn("password_hash", raw)

    def test_set_password_then_login(self):
        resp = self.client.post(f"/api/user/{self.user_id}/password", json={"password": "newpass99"})
        self.assertEqual(resp.status_code, 200)
        login = self.client.post("/api/auth/login", json={
            "user_id": self.user_id, "password": "newpass99",
        })
        self.assertEqual(login.status_code, 200)
        login = self.client.post("/api/auth/login", json={
            "user_id": self.user_id, "password": "old" + self.USER["password"],
        })
        self.assertEqual(login.status_code, 401)


class TestProtectedEndpoints(unittest.TestCase):
    USER = {
        "name": "Runner", "age": 30, "weight_kg": 80, "height_cm": 180,
        "target_calories": 2500, "target_protein_g": 130,
        "target_carbs_g": 280, "target_fat_g": 80,
        "password": "hunter22",
    }

    def setUp(self):
        reset_state()
        self.client = make_client()
        resp = self.client.post("/api/user/create", json=self.USER)
        self.assertEqual(resp.status_code, 201)
        self.user_id = resp.get_json()["user_id"]

    def test_meal_log_requires_auth(self):
        resp = self.client.post("/api/meals/log", json={
            "user_id": self.user_id,
            "meal_type": "lunch",
            "food_items": [{"name": "Chicken", "calories": 400, "protein_g": 35, "carbs_g": 0, "fat_g": 10}],
        })
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()["code"], "AUTH_REQUIRED")

    def test_chat_requires_auth(self):
        resp = self.client.post(f"/api/chat/{self.user_id}", json={"message": "Hi"})
        self.assertEqual(resp.status_code, 401)

    def test_activity_log_requires_auth(self):
        resp = self.client.post("/api/activity/log", json={
            "user_id": self.user_id, "activity_type": "study", "duration_minutes": 45,
        })
        self.assertEqual(resp.status_code, 401)

    def test_authenticated_chat_returns_reply_and_provider(self):
        login = self.client.post("/api/auth/login", json={
            "user_id": self.user_id, "password": self.USER["password"],
        })
        self.assertEqual(login.status_code, 200)
        headers = {"X-CSRF-Token": login.get_json()["csrf_token"]}
        resp = self.client.post(f"/api/chat/{self.user_id}", headers=headers, json={"message": "hello"})
        self.assertEqual(resp.status_code, 200)
        body = resp.get_json()
        self.assertIn("reply", body)
        self.assertIn("provider", body)
        self.assertIn(body["provider"], ("groq", "local"))
        self.assertTrue(body["reply"].strip())

    def test_other_user_cannot_authenticate_for_me(self):
        other = make_client()
        resp = other.post("/api/user/create", json=dict(self.USER, name="Other", user_id="other_one"))
        self.assertEqual(resp.status_code, 201)

        login = other.post("/api/auth/login", json={"user_id": "other_one", "password": "hunter22"})
        self.assertEqual(login.status_code, 200)
        headers = {"X-CSRF-Token": login.get_json()["csrf_token"]}
        resp = other.post("/api/meals/log", headers=headers, json={
            "user_id": self.user_id,
            "meal_type": "lunch",
            "food_items": [{"name": "Rice", "calories": 200, "protein_g": 4, "carbs_g": 45, "fat_g": 1}],
        })
        self.assertEqual(resp.status_code, 401)


class TestCsrf(unittest.TestCase):
    USER = {
        "name": "Csrf User", "age": 28, "weight_kg": 75, "height_cm": 178,
        "target_calories": 2400, "target_protein_g": 130,
        "target_carbs_g": 260, "target_fat_g": 75,
        "password": "secret99",
    }

    def setUp(self):
        reset_state()
        self.client = make_client()
        create = self.client.post("/api/user/create", json=self.USER)
        self.assertEqual(create.status_code, 201)
        self.user_id = create.get_json()["user_id"]
        login = self.client.post("/api/auth/login", json={
            "user_id": self.user_id, "password": self.USER["password"],
        })
        self.assertEqual(login.status_code, 200)
        self.token = login.get_json()["csrf_token"]

    def postLog(self, headers):
        return self.client.post("/api/activity/log", headers=headers, json={
            "user_id": self.user_id, "activity_type": "study", "duration_minutes": 30,
        })

    def test_authenticated_post_without_token(self):
        resp = self.postLog({})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["code"], "CSRF_FAILED")

    def test_authenticated_post_with_wrong_token(self):
        resp = self.postLog({"X-CSRF-Token": "nope"})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()["code"], "CSRF_FAILED")

    def test_authenticated_post_with_valid_token(self):
        resp = self.postLog({"X-CSRF-Token": self.token})
        self.assertEqual(resp.status_code, 201)

    def test_get_requests_never_blocked(self):
        resp = self.client.get(f"/api/user/{self.user_id}")
        self.assertEqual(resp.status_code, 200)

    def test_login_and_create_are_exempt(self):
        # Even a stale token on these pre-auth endpoints is tolerated.
        resp = self.client.post("/api/auth/logout", headers={"X-CSRF-Token": self.token})
        self.assertEqual(resp.status_code, 200)
        other = make_client()
        resp = other.post("/api/user/create", json=dict(self.USER, name="Two", user_id="user_two"))
        self.assertEqual(resp.status_code, 201)


class TestPersistenceEndpoints(unittest.TestCase):
    USER = {
        "name": "Planner", "age": 24, "weight_kg": 68, "height_cm": 172,
        "target_calories": 2300, "target_protein_g": 140,
        "target_carbs_g": 240, "target_fat_g": 75,
        "password": "plan99x",
    }

    def setUp(self):
        reset_state()
        self.client = make_client()
        resp = self.client.post("/api/user/create", json=self.USER)
        self.assertEqual(resp.status_code, 201)
        self.user_id = resp.get_json()["user_id"]
        login = self.client.post("/api/auth/login", json={
            "user_id": self.user_id, "password": "plan99x",
        })
        self.assertEqual(login.status_code, 200)
        self.headers = {"X-CSRF-Token": login.get_json()["csrf_token"]}

    def test_schedule_optimize_and_history(self):
        tasks = [
            {"name": "Study", "duration_min": 60, "difficulty": 6, "deadline_days": 2},
            {"name": "Review", "duration_min": 45, "difficulty": 4, "deadline_days": 4},
        ]
        resp = self.client.post(f"/api/schedule/optimize/{self.user_id}", headers=self.headers, json={"tasks": tasks})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["status"], "success")

        history = self.client.get(f"/api/schedule/history/{self.user_id}").get_json()
        self.assertGreaterEqual(history["count"], 1)
        self.assertEqual(history["schedules"][0]["num_tasks"], resp.get_json()["num_tasks"])

    def test_productivity_predict_and_sessions(self):
        resp = self.client.post(f"/api/productivity/predict/{self.user_id}", headers=self.headers, json={
            "hour_of_day": 10, "day_of_week": 0,
            "sleep_quality": 8.0, "sleep_hours": 8.0, "nutrition_score": 80.0,
            "energy_level": 7, "previous_session_duration": 60, "task_difficulty": 5,
        })
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertIn("predicted_focus_score", payload)

        sessions = self.client.get(f"/api/productivity/sessions/{self.user_id}").get_json()
        self.assertGreaterEqual(sessions["count"], 1)
        self.assertEqual(sessions["sessions"][0]["recommended_duration_minutes"],
                         payload["recommended_duration_minutes"])

    def test_activity_log_logs_trends(self):
        resp = self.client.post("/api/activity/log", headers=self.headers, json={
            "user_id": self.user_id, "activity_type": "study",
            "duration_minutes": 50, "energy_after": 7, "notes": "focused",
        })
        self.assertEqual(resp.status_code, 201)

        logs = self.client.get(f"/api/activity/logs/{self.user_id}").get_json()
        self.assertEqual(logs["count"], 1)
        self.assertEqual(logs["activity_logs"][0]["activity_type"], "study")

        trends = self.client.get(f"/api/activity/trends/{self.user_id}?days=7").get_json()
        self.assertEqual(trends["total_activities"], 1)
        self.assertEqual(trends["total_duration_minutes"], 50)
        self.assertEqual(trends["by_type"]["study"]["avg_energy_after"], 7.0)

    def test_activity_energy_after_out_of_range_rejected(self):
        resp = self.client.post("/api/activity/log", headers=self.headers, json={
            "user_id": self.user_id, "activity_type": "study",
            "duration_minutes": 30, "energy_after": 99,
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["code"], "VALUE_OUT_OF_RANGE")

    def test_rate_limit_returns_429(self):
        with mock.patch.object(external_module, "default_limiter",
                               RateLimiter(max_requests=2, window_seconds=60)):
            r1 = self.client.get("/api/food/search?q=chicken")
            self.assertNotEqual(r1.status_code, 429)
            r2 = self.client.get("/api/food/search?q=chicken")
            self.assertNotEqual(r2.status_code, 429)
            r3 = self.client.get("/api/food/search?q=chicken")
            self.assertEqual(r3.status_code, 429)
            self.assertEqual(r3.get_json()["code"], "RATE_LIMITED")

    def test_rate_limit_headers_present_on_success_and_429(self):
        with mock.patch.object(external_module, "default_limiter",
                               RateLimiter(max_requests=2, window_seconds=60)):
            ok = self.client.get("/api/food/search?q=chicken")
            self.assertEqual(ok.status_code, 200)
            self.assertIn("X-RateLimit-Limit", ok.headers)
            self.assertIn("X-RateLimit-Remaining", ok.headers)
            self.assertIn("X-RateLimit-Reset", ok.headers)
            self.assertEqual(ok.headers["X-RateLimit-Limit"], "2")
            self.assertEqual(ok.headers["X-RateLimit-Remaining"], "1")

            self.client.get("/api/food/search?q=chicken")  # exhausts the window
            limited = self.client.get("/api/food/search?q=chicken")
            self.assertEqual(limited.status_code, 429)
            self.assertEqual(limited.headers["X-RateLimit-Remaining"], "0")
            self.assertTrue(limited.headers["X-RateLimit-Reset"].isdigit())


class TestSessionExpiry(unittest.TestCase):
    """Auth sessions become permanent (with a TTL) only when configured."""

    USER = {
        "name": "Expiry User",
        "age": 30,
        "weight_kg": 75,
        "height_cm": 180,
        "biological_sex": "male",
        "password": "secret123",
    }

    def setUp(self):
        reset_state()
        self.old_lifetime = config.SESSION_LIFETIME_MINUTES
        self.old_permanent = app.config.get("PERMANENT_SESSION_LIFETIME")
        resp = make_client().post("/api/user/create", json=self.USER)
        self.assertEqual(resp.status_code, 201)
        self.user_id = resp.get_json()["user_id"]

    def tearDown(self):
        from datetime import timedelta
        config.SESSION_LIFETIME_MINUTES = self.old_lifetime
        app.config["PERMANENT_SESSION_LIFETIME"] = self.old_permanent or timedelta(days=31)

    def test_session_gets_ttl_when_configured(self):
        from datetime import timedelta
        config.SESSION_LIFETIME_MINUTES = 5
        app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=5)

        client = make_client()
        login = client.post("/api/auth/login", json={
            "user_id": self.user_id, "password": self.USER["password"],
        })
        self.assertEqual(login.status_code, 200)
        # The first authenticated request promotes the session to permanent.
        me = client.get("/api/auth/me")
        self.assertTrue(me.get_json()["authenticated"])
        set_cookie = me.headers.get("Set-Cookie", "")
        self.assertIn("Expires=", set_cookie, "permanent TTL cookie should carry Expires")

    def test_permanent_session_only_when_configured(self):
        from datetime import timedelta
        config.SESSION_LIFETIME_MINUTES = 0
        app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=31)
        client = make_client()
        login = client.post("/api/auth/login", json={
            "user_id": self.user_id, "password": self.USER["password"],
        })
        self.assertEqual(login.status_code, 200)
        me = client.get("/api/auth/me")
        self.assertTrue(me.get_json()["authenticated"])
        set_cookie = me.headers.get("Set-Cookie", "")
        self.assertNotIn("Expires=", set_cookie, "session stays transient when no TTL is configured")


if __name__ == "__main__":
    unittest.main()