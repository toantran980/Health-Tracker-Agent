"""
tests/test_production_readiness.py

Unit and integration tests for Production Readiness:
1. Production Deployment Baseline (readiness probes, secret validation)
2. Privacy & Account Controls (deletion cascade, export, privacy policy, duplicate user check)
3. Data-Quality Contract (strict ISO timestamp, future timestamp rejection, duplicate submission detection, water units)
4. Observability (X-Request-ID tracing, dependency metrics)
5. Release Process (backup/restore and migration check verification)
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from api.blueprints import state
from api.routes import app
from scripts import backup_restore, migration_check


class TestPhase1Foundation(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        state.users.clear()
        state.daily_logs.clear()
        state.activity_logs.clear()
        state.sleep_logs.clear()
        state.schedule_history.clear()
        state.productivity_sessions.clear()
        state.recent_submissions.clear()
        if state.mongo_store.enabled:
            for uid in (
                "test_unique_user",
                "test_export_delete_user",
                "test_timestamp_user",
                "test_dupe_user",
                "test_water_units_user",
            ):
                state.mongo_store.delete_user_data(uid)

    # -------------------------------------------------------------------------
    # 1. Production Deployment Baseline
    # -------------------------------------------------------------------------
    def test_health_live_and_ready_probes(self):
        """Verify liveness and readiness endpoints return standard structures."""
        live_res = self.client.get('/api/health/live')
        self.assertEqual(live_res.status_code, 200)
        live_data = live_res.get_json()
        self.assertEqual(live_data["status"], "live")

        ready_res = self.client.get('/api/health/ready')
        self.assertEqual(ready_res.status_code, 200)
        ready_data = ready_res.get_json()
        self.assertIn("checks", ready_data)
        self.assertIn("secret_key", ready_data["checks"])
        self.assertIn("database", ready_data)

    # -------------------------------------------------------------------------
    # 2. Privacy & Account Controls
    # -------------------------------------------------------------------------
    def test_privacy_policy_endpoint(self):
        """Test /api/privacy returns documented health categories and user rights."""
        res = self.client.get('/api/privacy')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("data_collected", data)
        self.assertIn("data_protection_rights", data)
        self.assertIn("erasure", data["data_protection_rights"])
        self.assertIn("portability", data["data_protection_rights"])

    def test_user_creation_duplicate_prevention(self):
        """Attempting to create a user with an existing user_id should return 409."""
        user_data = {
            "user_id": "test_unique_user",
            "name": "Unique User",
            "age": 28,
            "weight_kg": 75.0,
            "height_cm": 180.0,
            "password": "strongpassword123",
        }
        res1 = self.client.post('/api/user/create', json=user_data)
        self.assertEqual(res1.status_code, 201)

        # Second creation with identical user_id must fail
        res2 = self.client.post('/api/user/create', json=user_data)
        self.assertEqual(res2.status_code, 409)
        self.assertEqual(res2.get_json()["code"], "USER_ALREADY_EXISTS")

    def test_user_data_export_and_account_deletion(self):
        """Test full cycle: user registration, logging, data export, and cascade account deletion."""
        user_id = "test_export_delete_user"
        pw = "supersecret123"
        create_res = self.client.post('/api/user/create', json={
            "user_id": user_id,
            "name": "Export User",
            "password": pw,
        })
        self.assertEqual(create_res.status_code, 201)

        login_res = self.client.post('/api/auth/login', json={"user_id": user_id, "password": pw})
        self.assertEqual(login_res.status_code, 200)
        csrf_token = login_res.get_json().get("csrf_token")
        headers = {"X-CSRF-Token": csrf_token}

        act_res = self.client.post('/api/activity/log', json={
            "user_id": user_id,
            "activity_type": "exercise",
            "duration_minutes": 45,
            "notes": "Morning run",
        }, headers=headers)
        self.assertEqual(act_res.status_code, 201)

        water_res = self.client.post('/api/water/log', json={
            "user_id": user_id,
            "amount": 500,
            "unit": "ml",
        }, headers=headers)
        self.assertEqual(water_res.status_code, 201)

        export_res = self.client.get(f'/api/user/{user_id}/export', headers=headers)
        self.assertEqual(export_res.status_code, 200)
        export_data = export_res.get_json()
        self.assertIn("export_metadata", export_data)
        self.assertEqual(export_data["export_metadata"]["user_id"], user_id)
        self.assertNotIn("password_hash", export_data.get("user_profile", {}))
        # Password hash must NEVER be present in export

        del_res = self.client.delete(f'/api/user/{user_id}', headers=headers)
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.get_json()["status"], "deleted")

        get_res = self.client.get(f'/api/user/{user_id}')
        self.assertEqual(get_res.status_code, 404)
        self.assertNotIn(user_id, state.users)
        self.assertNotIn(user_id, state.activity_logs)

    # -------------------------------------------------------------------------
    # 3. Data-Quality Contract
    # -------------------------------------------------------------------------
    def test_invalid_and_future_timestamps_rejected(self):
        """Verify strict ISO-8601 parsing and rejection of future/invalid timestamps."""
        user_id = "test_timestamp_user"
        pw = "timestamp_pass_123"
        self.client.post('/api/user/create', json={"user_id": user_id, "password": pw})
        login_res = self.client.post('/api/auth/login', json={"user_id": user_id, "password": pw})
        csrf_token = login_res.get_json().get("csrf_token")
        headers = {"X-CSRF-Token": csrf_token}

        # 1. Invalid non-ISO string
        bad_ts_res = self.client.post('/api/activity/log', json={
            "user_id": user_id,
            "activity_type": "study",
            "duration_minutes": 30,
            "timestamp": "not-a-valid-date",
        }, headers=headers)
        self.assertEqual(bad_ts_res.status_code, 400)
        self.assertEqual(bad_ts_res.get_json()["code"], "INVALID_TIMESTAMP")

        # 2. Future timestamp (> 24 hours)
        future_dt = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        future_res = self.client.post('/api/activity/log', json={
            "user_id": user_id,
            "activity_type": "study",
            "duration_minutes": 30,
            "timestamp": future_dt,
        }, headers=headers)
        self.assertEqual(future_res.status_code, 400)
        self.assertEqual(future_res.get_json()["code"], "TIMESTAMP_IN_FUTURE")

    def test_duplicate_submission_detection(self):
        """Rapid identical submissions should return 409 DUPLICATE_SUBMISSION."""
        user_id = "test_dupe_user"
        pw = "dupe_pass_123"
        self.client.post('/api/user/create', json={"user_id": user_id, "password": pw})
        login_res = self.client.post('/api/auth/login', json={"user_id": user_id, "password": pw})
        csrf_token = login_res.get_json().get("csrf_token")
        headers = {"X-CSRF-Token": csrf_token}

        fixed_ts = datetime.now(timezone.utc).isoformat()
        req_body = {
            "user_id": user_id,
            "activity_type": "exercise",
            "duration_minutes": 25,
            "timestamp": fixed_ts,
            "log_id": "act_dedupe_123",
        }

        res1 = self.client.post('/api/activity/log', json=req_body, headers=headers)
        self.assertEqual(res1.status_code, 201)

        # Immediate second attempt with same key must trigger duplicate detection
        res2 = self.client.post('/api/activity/log', json=req_body, headers=headers)
        self.assertEqual(res2.status_code, 409)
        self.assertEqual(res2.get_json()["code"], "DUPLICATE_SUBMISSION")

    def test_water_logging_units(self):
        """Water endpoint should parse ml, oz, and l units correctly and validate bounds."""
        user_id = "test_water_units_user"
        pw = "water_pass_123"
        self.client.post('/api/user/create', json={"user_id": user_id, "password": pw})
        login_res = self.client.post('/api/auth/login', json={"user_id": user_id, "password": pw})
        headers = {"X-CSRF-Token": login_res.get_json().get("csrf_token")}

        res_oz = self.client.post('/api/water/log', json={
            "user_id": user_id,
            "amount": 8,
            "unit": "oz",
        }, headers=headers)
        self.assertEqual(res_oz.status_code, 201)
        self.assertEqual(res_oz.get_json()["logged_ml"], 237)

        res_bad = self.client.post('/api/water/log', json={
            "user_id": user_id,
            "amount": 10,
            "unit": "gallons",
        }, headers=headers)
        self.assertEqual(res_bad.status_code, 400)
        self.assertEqual(res_bad.get_json()["code"], "INVALID_UNIT")

    # -------------------------------------------------------------------------
    # 4. Observability
    # -------------------------------------------------------------------------
    def test_request_id_tracing_and_dependency_metrics(self):
        """Every response must return X-Request-ID, and /api/metrics/dependencies returns live metrics."""
        res = self.client.get('/api/health/live')
        self.assertIn("X-Request-ID", res.headers)
        self.assertTrue(len(res.headers["X-Request-ID"]) >= 8)

        # Pass custom X-Request-ID and verify it is preserved
        custom_id = "test-custom-req-id-1234"
        custom_res = self.client.get('/api/health/live', headers={"X-Request-ID": custom_id})
        self.assertEqual(custom_res.headers.get("X-Request-ID"), custom_id)

        metrics_res = self.client.get('/api/metrics/dependencies')
        self.assertEqual(metrics_res.status_code, 200)
        metrics_data = metrics_res.get_json()
        self.assertIn("uptime_seconds", metrics_data)
        self.assertIn("database", metrics_data)
        self.assertIn("external_apis", metrics_data)

    # -------------------------------------------------------------------------
    # 5. Release Process
    # -------------------------------------------------------------------------
    def test_backup_restore_and_migration_scripts(self):
        """Test backup, verify, and migration check scripts programmatically."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = tf.name

        try:
            backup_ok = backup_restore.backup(temp_path)
            self.assertTrue(backup_ok)

            verify_ok = backup_restore.verify(temp_path)
            self.assertTrue(verify_ok)

            config_errs = migration_check.check_configuration()
            self.assertEqual(len(config_errs), 0)

            import_errs = migration_check.check_code_imports()
            self.assertEqual(len(import_errs), 0)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
