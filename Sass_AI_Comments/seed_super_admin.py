#!/usr/bin/env python3
"""
Seed a dummy Super Admin user into the MongoDB `users` collection.

Usage examples:
  python3 scripts/seed_super_admin.py \
    --email super@example.com \
    --password Super#12345 \
    --display-name "Super Admin"

This script does not import the app package (avoids FastAPI dependency); it connects
directly to MongoDB using MONGO_URI from settings.py and mirrors the hashing/indexing
logic used by Storage._users_col() and Storage._hash_password().
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import os
import sys

try:
    import bcrypt  # type: ignore
except Exception:  # pragma: no cover
    bcrypt = None

from pymongo import MongoClient, ASCENDING


def load_mongo_uri() -> str:
    # Reuse settings.py if available to honor your local env, otherwise env var
    try:
        # settings.py defines MONGO_URI (string)
        settings_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if settings_dir not in sys.path:
            sys.path.insert(0, settings_dir)
        from settings import MONGO_URI  # type: ignore

        if isinstance(MONGO_URI, str) and MONGO_URI:
            return MONGO_URI
    except Exception:
        pass
    uri = os.environ.get("MONGO_URI")
    if not uri:
        raise SystemExit("MONGO_URI not set and settings.MONGO_URI not found. Export MONGO_URI or configure settings.py.")
    return uri


def get_db():
    uri = load_mongo_uri()
    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    # touch the server to validate connection
    client.admin.command("ping")
    try:
        db = client.get_default_database()
    except Exception:
        db = client.get_database("ai_appo")
    return db


def ensure_user_indexes(col) -> None:
    col.create_index([("email", ASCENDING)], unique=True)
    col.create_index([("tenant", ASCENDING), ("role", ASCENDING)])


def hash_password(password: str) -> str:
    pw = (password or "").encode("utf-8")
    if bcrypt is not None:
        return bcrypt.hashpw(pw, bcrypt.gensalt(12)).decode("utf-8")
    # Fallback: salted sha256 (dev only)
    salt = os.urandom(16)
    digest = hashlib.sha256(salt + pw).hexdigest()
    return f"sha256${salt.hex()}${digest}"


def user_exists(col, email_norm: str) -> bool:
    return bool(col.find_one({"email": email_norm}))


def main():
    ap = argparse.ArgumentParser(description="Seed a Super Admin user into MongoDB")
    ap.add_argument("--email", required=False, default=os.environ.get("SEED_EMAIL", "super@example.com"))
    ap.add_argument("--password", required=False, default=os.environ.get("SEED_PASSWORD", "Super#12345"))
    ap.add_argument("--display-name", required=False, default=os.environ.get("SEED_DISPLAY_NAME", "Super Admin"))
    args = ap.parse_args()

    email = (args.email or "").strip().lower()
    if not email:
        raise SystemExit("--email is required")
    password = args.password or ""
    if len(password) < 8:
        raise SystemExit("--password must be at least 8 characters")

    db = get_db()
    users = db.get_collection("users")
    ensure_user_indexes(users)

    if user_exists(users, email):
        print(f"User already exists: {email}")
        return

    now = dt.datetime.utcnow()
    doc = {
        "email": email,
        "password_hash": hash_password(password),
        "role": "super_admin",
        "tenant": None,
        "display_name": args.display_name or "",
        "caps": [],
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    users.insert_one(doc)
    print(f"CREATED super_admin: {email}")


if __name__ == "__main__":
    main()
