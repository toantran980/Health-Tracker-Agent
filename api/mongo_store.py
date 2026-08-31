"""MongoDB persistence helpers for the Health Tracker app."""

from __future__ import annotations

import logging
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
        self.db = None

        import config
        max_retries = config.MONGO_CONNECT_RETRIES
        retry_delay = config.MONGO_CONNECT_RETRY_DELAY
        last_error: PyMongoError | None = None

        for attempt in range(1, max_retries + 1):
            try:
                client = MongoClient(uri, serverSelectionTimeoutMS=3000)
                db = client[db_name]
                db.command("ping")
                self.db = db
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
        import config
        meals_ttl = config.MONGO_MEALS_TTL_DAYS
        daily_logs_ttl = config.MONGO_DAILY_LOGS_TTL_DAYS

        self.db["users"].create_index("user_id", unique=True)
        self.db["daily_logs"].create_index(
            [("user_id", ASCENDING), ("date", ASCENDING)], unique=True
        )

        # TTL indexes bound collection growth on meal logs and daily records.
        # daily_logs["updated_at"] is refreshed on every upsert, so docs are
        # dropped only after MONGO_DAILY_LOGS_TTL_DAYS of inactivity.
        if 0 < daily_logs_ttl:
            self.db["daily_logs"].create_index(
                "updated_at", expireAfterSeconds=daily_logs_ttl * 86400
            )
        if 0 < meals_ttl:
            self.db["meals"].create_index(
                "timestamp", expireAfterSeconds=meals_ttl * 86400
            )

        self.db["activities"].create_index("activity_id", unique=True)
        self.db["activity_logs"].create_index(
            [("user_id", ASCENDING), ("timestamp", DESCENDING)]
        )
        self.db["recommendations"].create_index("user_id")
        self.db["meals"].create_index("meal_id", unique=True)
        self.db["schedules"].create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)]
        )
        self.db["productivity_sessions"].create_index(
            [("user_id", ASCENDING), ("timestamp", DESCENDING)]
        )
        self.db["chat_history"].create_index("user_id", unique=True)

    
    #  Activities                                                        #
    def save_activity(self, activity_doc: dict[str, Any]) -> bool:
        """Upsert an activity document. Returns True on success, False otherwise."""
        if not self.enabled or self.db is None:
            return False
        try:
            doc = dict(activity_doc)
            doc.pop("created_at", None)  # Remove created_at if present to avoid conflict
            self.db["activities"].update_one(
                {"activity_id": doc["activity_id"]},
                {"$set": doc, "$setOnInsert": {"created_at": datetime.now(UTC)}},
                upsert=True,
            )
            return True
        except PyMongoError:
            logger.exception("[MongoDB] save_activity failed for activity_id=%s", activity_doc.get("activity_id"))
            return False

    def get_activities(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        if not self.enabled or self.db is None:
            return []
        try:
            cursor = (
                self.db["activities"]
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
        if not self.enabled or self.db is None:
            return False
        try:
            self.db["recommendations"].insert_one({**rec_doc, "created_at": datetime.now(UTC)})
            return True
        except PyMongoError:
            logger.exception("[MongoDB] save_recommendation failed for user_id=%s", rec_doc.get("user_id"))
            return False

    def get_recommendations(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        if not self.enabled or self.db is None:
            return []
        try:
            cursor = (
                self.db["recommendations"]
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
        if not self.enabled or self.db is None:
            return False
        try:
            doc = dict(meal_doc)
            # TTL indexes require timezone-aware UTC datetimes.
            ts = doc.get("timestamp")
            if isinstance(ts, datetime):
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
                doc["timestamp"] = ts.astimezone(UTC)
            self.db["meals"].update_one(
                {"meal_id": doc["meal_id"]},
                {"$set": doc, "$setOnInsert": {"created_at": datetime.now(UTC)}},
                upsert=True,
            )
            return True
        except PyMongoError:
            logger.exception("[MongoDB] save_meal failed for meal_id=%s", meal_doc.get("meal_id"))
            return False

    def get_meals(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        if not self.enabled or self.db is None:
            return []
        try:
            cursor = (
                self.db["meals"]
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
        import config
        uri = config.MONGO_URI
        db_name = config.MONGO_DB_NAME
        return cls(uri, db_name)

    #  Users                                                               #
    def save_user(self, user_doc: dict[str, Any]) -> bool:
        """Upsert a user document. Returns True on success, False otherwise."""
        if not self.enabled or self.db is None:
            return False
        now = datetime.now(UTC)
        doc = {**user_doc, "updated_at": now}
        try:
            self.db["users"].update_one(
                {"user_id": doc["user_id"]},
                {"$set": doc, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
            return True
        except PyMongoError:
            logger.exception("[MongoDB] save_user failed for user_id=%s", user_doc.get("user_id"))
            return False

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        if not self.enabled or self.db is None:
            return None
        try:
            return self.db["users"].find_one({"user_id": user_id}, {"_id": 0})
        except PyMongoError:
            logger.exception("[MongoDB] get_user failed for user_id=%s", user_id)
            return None

    def count_users(self) -> int:
        if not self.enabled or self.db is None:
            return 0
        try:
            return int(self.db["users"].count_documents({}))
        except PyMongoError:
            logger.exception("[MongoDB] count_users failed")
            return 0

    
    #  Daily logs                                                          #
    def save_daily_log(
        self, user_id: str, date_str: str, log_doc: dict[str, Any]
    ) -> bool:
        """Upsert a daily log entry. Returns True on success, False otherwise."""
        if not self.enabled or self.db is None:
            return False
        now = datetime.now(UTC)
        doc = {**log_doc, "user_id": user_id, "date": date_str, "updated_at": now}
        try:
            self.db["daily_logs"].update_one(
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
        if not self.enabled or self.db is None:
            return []
        try:
            cursor = (
                self.db["daily_logs"]
                .find({"user_id": user_id}, {"_id": 0})
                .sort("date", ASCENDING)
                .limit(limit)
            )
            return list(cursor)
        except PyMongoError:
            logger.exception("[MongoDB] get_daily_logs failed for user_id=%s", user_id)
            return []

    #  Scheduled tasks + productivity sessions                    #
    def save_schedule(self, user_id: str, schedule_doc: dict[str, Any]) -> bool:
        """Insert a schedule optimization result."""
        if not self.enabled or self.db is None:
            return False
        try:
            doc = {"user_id": user_id, **schedule_doc}
            doc.setdefault("created_at", datetime.now(UTC))
            self.db["schedules"].insert_one(doc)
            return True
        except PyMongoError:
            logger.exception("[MongoDB] save_schedule failed for user_id=%s", user_id)
            return False

    def get_schedules(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        if not self.enabled or self.db is None:
            return []
        try:
            cursor = (
                self.db["schedules"]
                .find({"user_id": user_id}, {"_id": 0})
                .sort("created_at", DESCENDING)
                .limit(limit)
            )
            return list(cursor)
        except PyMongoError:
            logger.exception("[MongoDB] get_schedules failed for user_id=%s", user_id)
            return []

    def save_productivity_session(self, user_id: str, session_doc: dict[str, Any]) -> bool:
        """Insert a productivity prediction session."""
        if not self.enabled or self.db is None:
            return False
        try:
            doc = {"user_id": user_id, **session_doc}
            doc.setdefault("timestamp", datetime.now(UTC))
            self.db["productivity_sessions"].insert_one(doc)
            return True
        except PyMongoError:
            logger.exception(
                "[MongoDB] save_productivity_session failed for user_id=%s", user_id
            )
            return False

    def get_productivity_sessions(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        if not self.enabled or self.db is None:
            return []
        try:
            cursor = (
                self.db["productivity_sessions"]
                .find({"user_id": user_id}, {"_id": 0})
                .sort("timestamp", DESCENDING)
                .limit(limit)
            )
            return list(cursor)
        except PyMongoError:
            logger.exception(
                "[MongoDB] get_productivity_sessions failed for user_id=%s", user_id
            )
            return []

    #  Activity logs                                                #
    def save_activity_log(self, log_doc: dict[str, Any]) -> bool:
        """Insert an ActivityLog document. Returns True on success, False otherwise."""
        if not self.enabled or self.db is None:
            return False
        try:
            self.db["activity_logs"].insert_one({**log_doc, "created_at": datetime.now(UTC)})
            return True
        except PyMongoError:
            logger.exception(
                "[MongoDB] save_activity_log failed for user_id=%s", log_doc.get("user_id")
            )
            return False

    def get_activity_logs(self, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        if not self.enabled or self.db is None:
            return []
        try:
            cursor = (
                self.db["activity_logs"]
                .find({"user_id": user_id}, {"_id": 0})
                .sort("timestamp", DESCENDING)
                .limit(limit)
            )
            return list(cursor)
        except PyMongoError:
            logger.exception("[MongoDB] get_activity_logs failed for user_id=%s", user_id)
            return []

    #  Chat history                                                       #
    def save_chat_history(self, user_id: str, messages: list[dict[str, Any]]) -> bool:
        """Upsert the most recent conversation turns for a user.

        Stored so a server restart can restore the session context. Keep only
        role/content so no snapshot or secret data is persisted.
        """
        if not self.enabled or self.db is None:
            return False
        try:
            clean = [
                {"role": m.get("role"), "content": m.get("content")}
                for m in messages
                if m.get("role") in ("user", "assistant") and m.get("content")
            ]
            self.db["chat_history"].update_one(
                {"user_id": user_id},
                {"$set": {"messages": clean, "updated_at": datetime.now(UTC)}},
                upsert=True,
            )
            return True
        except PyMongoError:
            logger.exception("[MongoDB] save_chat_history failed for user_id=%s", user_id)
            return False

    def get_chat_history(self, user_id: str) -> list[dict[str, Any]]:
        if not self.enabled or self.db is None:
            return []
        try:
            doc = self.db["chat_history"].find_one({"user_id": user_id}, {"_id": 0})
            return (doc or {}).get("messages", [])
        except PyMongoError:
            logger.exception("[MongoDB] get_chat_history failed for user_id=%s", user_id)
            return []

    def delete_chat_history(self, user_id: str) -> bool:
        if not self.enabled or self.db is None:
            return False
        try:
            self.db["chat_history"].delete_many({"user_id": user_id})
            return True
        except PyMongoError:
            logger.exception("[MongoDB] delete_chat_history failed for user_id=%s", user_id)
            return False