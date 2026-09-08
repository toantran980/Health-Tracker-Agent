#!/usr/bin/env python3
"""
scripts/migration_check.py

Pre-deployment verification script for database schema, index definitions,
and production configuration readiness.

Exit Codes:
    0: All checks passed (ready for deployment)
    1: One or more critical checks failed
"""

import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient
from pymongo.errors import PyMongoError

import config

EXPECTED_INDEXES = {
    "users": ["user_id_1"],
    "daily_logs": ["user_id_1_date_1"],
    "activities": ["activity_id_1"],
    "meals": ["meal_id_1"],
    "schedules": ["user_id_1_created_at_-1"],
    "productivity_sessions": ["user_id_1_timestamp_-1"],
    "chat_history": ["user_id_1"],
    "sleep_logs": ["user_id_1_timestamp_-1"],
}


def check_configuration() -> list[str]:
    errors = []
    print("[*] Checking configuration...")
    if not config.SECRET_KEY:
        errors.append("SECRET_KEY is empty")
    elif len(config.SECRET_KEY.strip()) < 16:
        errors.append("SECRET_KEY is shorter than 16 characters")
    elif config.IS_PRODUCTION and len(config.SECRET_KEY.strip()) < 32:
        errors.append("SECRET_KEY must be >= 32 characters in production mode")

    print(f"    - Environment: {config.ENVIRONMENT}")
    print(f"    - Port: {config.PORT}")
    print(f"    - CSRF Protection: {config.CSRF_PROTECTION}")
    print(f"    - Session Secure Cookie: {config.SESSION_COOKIE_SECURE}")
    return errors


def check_database() -> list[str]:
    errors = []
    print("[*] Checking database connectivity and indexes...")
    try:
        client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=2000)
        db = client[config.MONGO_DB_NAME]
        db.command("ping")
        print(f"    - Connected to MongoDB at {config.MONGO_URI}")
    except PyMongoError as exc:
        if config.IS_PRODUCTION:
            errors.append(f"MongoDB connection failed in production: {exc}")
        else:
            print(f"    [!] MongoDB not available ({exc}). Memory fallback active for dev.")
        return errors

    existing_collections = db.list_collection_names()
    print(f"    - Found {len(existing_collections)} collections in '{config.MONGO_DB_NAME}'")

    for col_name, expected_names in EXPECTED_INDEXES.items():
        if col_name not in existing_collections:
            continue
        indexes = db[col_name].index_information()
        for idx in expected_names:
            if idx not in indexes:
                errors.append(f"Missing required index '{idx}' on collection '{col_name}'")
            else:
                print(f"    - Index '{idx}' on '{col_name}': OK")

    return errors


def check_code_imports() -> list[str]:
    errors = []
    print("[*] Verifying critical module imports...")
    modules = [
        "flask",
        "pymongo",
        "sklearn",
        "werkzeug",
        "ai_modules.goal_tracker",
        "ai_modules.health_risk_assessor",
        "ai_modules.recovery_predictor",
        "ai_modules.sleep_quality_predictor",
        "ai_modules.weekly_digest",
        "api.routes",
    ]
    for mod in modules:
        try:
            __import__(mod)
        except Exception as exc:
            errors.append(f"Import check failed for {mod}: {exc}")

    if not errors:
        print("    - All core modules imported successfully.")
    return errors


def main():
    print("=== Health Tracker Pre-Deployment Migration Check ===")
    config_errs = check_configuration()
    import_errs = check_code_imports()
    db_errs = check_database()

    all_errors = config_errs + import_errs + db_errs
    if all_errors:
        print("\n[!] Pre-deployment check FAILED with errors:")
        for err in all_errors:
            print(f"    - {err}")
        sys.exit(1)

    print("\n[OK] All pre-deployment migration checks PASSED successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()
