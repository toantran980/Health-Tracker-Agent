"""MongoDB persistence helpers for the Health Tracker app."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

load_dotenv()

logger = logging.getLogger(__name__)

UTC = timezone.utc


class MongoStore:
    """Small persistence wrapper for users and daily meal logs."""

    def __init__(self, uri: str, db_name: str):
        self.uri = uri
        self.db_name = db_name
        self.enabled = False
        self._db = None

        max_retries = int(os.getenv("MONGO_CONNECT_RETRIES", "5"))
        retry_delay = float(os.getenv("MONGO_CONNECT_RETRY_DELAY", "2"))
        last_error: PyMongoError | None = None

        for attempt in range(1, max_retries + 1):
            try:
                client = MongoClient(uri, serverSelectionTimeoutMS=3000)
                db = client[db_name]
                db.command("ping")
                self._db = db
                self.enabled = True
                self._ensure_indexes()
                logger.info("[MongoDB] Connected on attempt %d", attempt)
                break
            except PyMongoError as exc:
                last_error = exc
                if attempt < max_retries:
                    logger.warning(
                        "[MongoDB] Attempt %d/%d failed: %s. Retrying in %.1fs",
                        attempt, max_retries, exc, retry_delay,
                    )
                    time.sleep(retry_delay)

        if not self.enabled:
            logger.warning(
                "[MongoDB] Disabled after %d attempts: %s",
                max_retries, last_error,
            )

    def _ensure_indexes(self) -> None:
        self._db["users"].create_index("user_id", unique=True)
        self._db["daily_logs"].create_index(
            [("user_id", ASCENDING), ("date", ASCENDING)], unique=True
        )
        self._db["activities"].create_index("activity_id", unique=True)
        self._db["recommendations"].create_index("user_id")
        self._db["meals"].create_index("meal_id", unique=True)

    
    #  Activities                                                        #
    def save_activity(self, activity_doc: dict[str, Any]) -> bool:
        """Upsert an activity document. Returns True on success, False otherwise."""
        if not self.enabled or self._db is None:
            return False
        try:
            doc = dict(activity_doc)
            doc.pop("created_at", None)  # Remove created_at if present to avoid conflict
            self._db["activities"].update_one(
                {"activity_id": doc["activity_id"]},
                {"$set": doc, "$setOnInsert": {"created_at": datetime.now(UTC)}},
                upsert=True,
            )
            return True
        except PyMongoError:
            logger.exception("[MongoDB] save_activity failed for activity_id=%s", activity_doc.get("activity_id"))
            return False

    def get_activities(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        if not self.enabled or self._db is None:
            return []
        try:
            cursor = (
                self._db["activities"]
                .find({"user_id": user_id}, {"_id": 0})
                .sort("created_at", ASCENDING)
                .limit(limit)
            )
            return list(cursor)
        except PyMongoError:
            logger.exception("[MongoDB] get_activities failed for user_id=%s", user_id)
            return []

    #  Recommendations                                                    
    def save_recommendation(self, rec_doc: dict[str, Any]) -> bool:
        """Insert a recommendation document. Returns True on success, False otherwise."""
        if not self.enabled or self._db is None:
            return False
        try:
            self._db["recommendations"].insert_one({**rec_doc, "created_at": datetime.now(UTC)})
            return True
        except PyMongoError:
            logger.exception("[MongoDB] save_recommendation failed for user_id=%s", rec_doc.get("user_id"))
            return False

    def get_recommendations(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        if not self.enabled or self._db is None:
            return []
        try:
            cursor = (
                self._db["recommendations"]
                .find({"user_id": user_id}, {"_id": 0})
                .sort("created_at", DESCENDING)
                .limit(limit)
            )
            return list(cursor)
        except PyMongoError:
            logger.exception("[MongoDB] get_recommendations failed for user_id=%s", user_id)
            return []

    #  Meals                                                              #
    def save_meal(self, meal_doc: dict[str, Any]) -> bool:
        """Upsert a meal document. Returns True on success, False otherwise."""
        if not self.enabled or self._db is None:
            return False
        try:
            self._db["meals"].update_one(
                {"meal_id": meal_doc["meal_id"]},
                {"$set": meal_doc, "$setOnInsert": {"created_at": datetime.now(UTC)}},
                upsert=True,
            )
            return True
        except PyMongoError:
            logger.exception("[MongoDB] save_meal failed for meal_id=%s", meal_doc.get("meal_id"))
            return False

    def get_meals(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        if not self.enabled or self._db is None:
            return []
        try:
            cursor = (
                self._db["meals"]
                .find({"user_id": user_id}, {"_id": 0})
                .sort("timestamp", DESCENDING)
                .limit(limit)
            )
            return list(cursor)
        except PyMongoError:
            logger.exception("[MongoDB] get_meals failed for user_id=%s", user_id)
            return []

    @classmethod
    def from_env(cls) -> "MongoStore":
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGO_DB_NAME", "health_tracker")
        return cls(uri, db_name)

    #  Users                                                               #
    def save_user(self, user_doc: dict[str, Any]) -> bool:
        """Upsert a user document. Returns True on success, False otherwise."""
        if not self.enabled or self._db is None:
            return False
        now = datetime.now(UTC)
        doc = {**user_doc, "updated_at": now}
        try:
            self._db["users"].update_one(
                {"user_id": doc["user_id"]},
                {"$set": doc, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
            return True
        except PyMongoError:
            logger.exception("[MongoDB] save_user failed for user_id=%s", user_doc.get("user_id"))
            return False

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        if not self.enabled or self._db is None:
            return None
        try:
            return self._db["users"].find_one({"user_id": user_id}, {"_id": 0})
        except PyMongoError:
            logger.exception("[MongoDB] get_user failed for user_id=%s", user_id)
            return None

    def count_users(self) -> int:
        if not self.enabled or self._db is None:
            return 0
        try:
            return int(self._db["users"].count_documents({}))
        except PyMongoError:
            logger.exception("[MongoDB] count_users failed")
            return 0

    
    #  Daily logs                                                          #
    def save_daily_log(
        self, user_id: str, date_str: str, log_doc: dict[str, Any]
    ) -> bool:
        """Upsert a daily log entry. Returns True on success, False otherwise."""
        if not self.enabled or self._db is None:
            return False
        now = datetime.now(UTC)
        doc = {**log_doc, "user_id": user_id, "date": date_str, "updated_at": now}
        try:
            self._db["daily_logs"].update_one(
                {"user_id": user_id, "date": date_str},
                {"$set": doc, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
            return True
        except PyMongoError:
            logger.exception(
                "[MongoDB] save_daily_log failed for user_id=%s date=%s", user_id, date_str
            )
            return False

    def get_daily_logs(
        self, user_id: str, limit: int = 90
    ) -> list[dict[str, Any]]:
        """Return daily logs sorted ascending by date, capped at `limit` entries."""
        if not self.enabled or self._db is None:
            return []
        try:
            cursor = (
                self._db["daily_logs"]
                .find({"user_id": user_id}, {"_id": 0})
                .sort("date", ASCENDING)
                .limit(limit)
            )
            return list(cursor)
        except PyMongoError:
            logger.exception("[MongoDB] get_daily_logs failed for user_id=%s", user_id)
            return []