#!/usr/bin/env python3
"""
scripts/backup_restore.py

CLI tool for backup, restore, and integrity verification of Health Tracker data.
Handles MongoDB collections when reachable, or exports/imports structured JSON archives.

Usage:
    python scripts/backup_restore.py --backup backup_2026.json
    python scripts/backup_restore.py --restore backup_2026.json
    python scripts/backup_restore.py --verify backup_2026.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient
from pymongo.errors import PyMongoError

import config

COLLECTIONS = [
    "users",
    "daily_logs",
    "meals",
    "activity_logs",
    "activities",
    "schedules",
    "productivity_sessions",
    "chat_history",
    "sleep_logs",
    "recommendations",
]


def get_mongo_db():
    try:
        client = MongoClient(config.MONGO_URI, serverSelectionTimeoutMS=3000)
        db = client[config.MONGO_DB_NAME]
        db.command("ping")
        return db
    except PyMongoError as exc:
        print(f"[Backup/Restore] MongoDB unavailable at {config.MONGO_URI}: {exc}")
        return None


def serialize_doc(doc: dict) -> dict:
    """Make MongoDB documents JSON-serializable."""
    clean = {}
    for k, v in doc.items():
        if k == "_id":
            continue
        if isinstance(v, datetime):
            clean[k] = v.isoformat()
        else:
            clean[k] = v
    return clean


def backup(output_path: str) -> bool:
    print(f"[*] Starting backup to '{output_path}'...")
    db = get_mongo_db()
    archive = {
        "metadata": {
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_uri": config.MONGO_URI if db is not None else "memory",
            "database": config.MONGO_DB_NAME,
        },
        "collections": {},
    }

    if db is not None:
        total_records = 0
        for col_name in COLLECTIONS:
            cursor = db[col_name].find()
            docs = [serialize_doc(doc) for doc in cursor]
            archive["collections"][col_name] = docs
            total_records += len(docs)
            print(f"    - {col_name}: {len(docs)} documents")
        archive["metadata"]["total_records"] = total_records
    else:
        print("    [!] MongoDB not connected. Backing up in-memory state...")
        from api.blueprints import state
        archive["collections"]["users"] = [u.to_public_dict() for u in state.users.values()]
        archive["collections"]["activity_logs"] = [
            item for sublist in state.activity_logs.values() for item in sublist
        ]
        archive["collections"]["sleep_logs"] = [
            item for sublist in state.sleep_logs.values() for item in sublist
        ]
        total = sum(len(v) for v in archive["collections"].values())
        archive["metadata"]["total_records"] = total
        print(f"    - Backed up {total} in-memory records.")

    parent = os.path.dirname(os.path.abspath(output_path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(archive, f, indent=2, ensure_ascii=False)

    print(f"[OK] Backup completed successfully: {output_path} ({archive['metadata']['total_records']} total records)")
    return True


def verify(input_path: str) -> bool:
    print(f"[*] Verifying archive '{input_path}'...")
    if not os.path.exists(input_path):
        print(f"[!] File not found: {input_path}")
        return False

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:  # noqa: BLE001
        print(f"[!] JSON parsing failed: {exc}")
        return False

    metadata = data.get("metadata", {})
    collections = data.get("collections", {})
    if "version" not in metadata or "timestamp" not in metadata:
        print("[!] Archive missing metadata fields (version, timestamp)")
        return False

    print(f"    - Archive version: {metadata.get('version')}")
    print(f"    - Created at: {metadata.get('timestamp')}")
    total = 0
    for col, items in collections.items():
        if not isinstance(items, list):
            print(f"[!] Collection '{col}' is not a list")
            return False
        total += len(items)
        print(f"    - {col}: {len(items)} records OK")

    print(f"[OK] Archive integrity verified: {total} total records valid.")
    return True


def restore(input_path: str) -> bool:
    print(f"[*] Starting restore from '{input_path}'...")
    if not verify(input_path):
        return False

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    db = get_mongo_db()
    if db is None:
        print("[!] Cannot restore: MongoDB is not reachable.")
        return False

    collections = data.get("collections", {})
    restored_total = 0
    for col_name, docs in collections.items():
        if not docs:
            continue
        try:
            db[col_name].delete_many({})
            res = db[col_name].insert_many(docs)
            restored_total += len(res.inserted_ids)
            print(f"    - Restored {len(res.inserted_ids)} records to '{col_name}'")
        except PyMongoError as exc:
            print(f"[!] Failed restoring collection '{col_name}': {exc}")
            return False

    print(f"[OK] Restore completed: {restored_total} documents restored into '{config.MONGO_DB_NAME}'.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Health Tracker Backup & Restore CLI")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--backup", metavar="FILE", help="Save database contents to JSON archive")
    group.add_argument("--restore", metavar="FILE", help="Restore database contents from JSON archive")
    group.add_argument("--verify", metavar="FILE", help="Verify archive structure and integrity")

    args = parser.parse_args()
    if args.backup:
        success = backup(args.backup)
    elif args.restore:
        success = restore(args.restore)
    elif args.verify:
        success = verify(args.verify)
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
