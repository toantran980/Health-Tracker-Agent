"""MongoDB persistence helpers for the Health Tracker app."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()


class MongoStore:
    """Small persistence wrapper for users and daily meal logs."""

    def __init__(self, uri: str, db_name: str):
        self.uri = uri
        self.db_name = db_name
        self.enabled = False
        self._db = None

        max_retries = int(os.getenv("MONGO_CONNECT_RETRIES", "5"))
        retry_delay_seconds = float(os.getenv("MONGO_CONNECT_RETRY_DELAY", "2"))
        last_error: PyMongoError | None = None

        for attempt in range(1, max_retries + 1):
            try:
                client = MongoClient(uri, serverSelectionTimeoutMS=3000)
                db = client[db_name]
                db.command("ping")
                self._db = db
                self.enabled = True

                users = self._db["users"]
                daily_logs = self._db["daily_logs"]
                users.create_index("user_id", unique=True)
                daily_logs.create_index([("user_id", 1), ("date", 1)], unique=True)
                logger.info("[MongoDB] Connected on attempt %d", attempt)
                break
            except PyMongoError as exc:
                last_error = exc
                if attempt < max_retries:
                    logger.warning(
                        "[MongoDB] Connection attempt %d/%d failed: %s. Retrying in %.1fs",
                        attempt,
                        max_retries,
                        exc,
                        retry_delay_seconds,
                    )
                    time.sleep(retry_delay_seconds)

        if not self.enabled and last_error is not None:
            logger.warning("[MongoDB] Disabled after %d retries: %s", max_retries, last_error)

    @classmethod
    def from_env(cls) -> "MongoStore":
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        db_name = os.getenv("MONGO_DB_NAME", "health_tracker")
        return cls(uri, db_name)

    def save_user(self, user_doc: dict[str, Any]) -> None:
        if not self.enabled or not self._db:
            return
        doc = dict(user_doc)
        doc["updated_at"] = datetime.utcnow()
        self._db["users"].update_one(
            {"user_id": doc["user_id"]},
            {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
            upsert=True,
        )

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        if not self.enabled or not self._db:
            return None
        return self._db["users"].find_one({"user_id": user_id}, {"_id": 0})

    def count_users(self) -> int:
        if not self.enabled or not self._db:
            return 0
        return int(self._db["users"].count_documents({}))

    def save_daily_log(self, user_id: str, date_str: str, log_doc: dict[str, Any]) -> None:
        if not self.enabled or not self._db:
            return
        doc = dict(log_doc)
        doc.update({"user_id": user_id, "date": date_str, "updated_at": datetime.utcnow()})
        self._db["daily_logs"].update_one(
            {"user_id": user_id, "date": date_str},
            {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
            upsert=True,
        )

    def get_daily_logs(self, user_id: str) -> list[dict[str, Any]]:
        if not self.enabled or not self._db:
            return []
        cursor = self._db["daily_logs"].find({"user_id": user_id}, {"_id": 0}).sort("date", 1)
        return list(cursor)
