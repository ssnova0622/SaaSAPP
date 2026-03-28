#!/usr/bin/env python3
"""
Create or update the Super Admin user. Uses app's DB and Storage password hashing so login works.
Run from project root: python scripts/create_super_admin.py
"""
import datetime

from app.services.db import get_db, users_collection
from app.services.storage_mongo import Storage
from settings import MOCK_SUPER_ADMIN_EMAIL, MOCK_SUPER_ADMIN_PASSWORD, MOCK_SUPER_ADMIN_DISPLAY_NAME


def main():
    get_db()  # ensure connection and indexes
    col = users_collection()
    email = (MOCK_SUPER_ADMIN_EMAIL or "").strip().lower()
    existing = col.find_one({"email": email})
    password_hash = Storage._hash_password(MOCK_SUPER_ADMIN_PASSWORD)
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    doc = {
        "id": "user_super_admin",
        "email": email,
        "password_hash": password_hash,
        "role": "super_admin",
        "tenant": None,
        "display_name": (MOCK_SUPER_ADMIN_DISPLAY_NAME or "Super Admin").strip(),
        "caps": [],
        "status": "active",
        "created_at": existing.get("created_at") if existing else now,
        "updated_at": now,
    }

    col.update_one(
        {"email": doc["email"]},
        {"$set": doc},
        upsert=True,
    )
    print("Super Admin user created/updated.")
    print(f"  Email: {MOCK_SUPER_ADMIN_EMAIL}")
    print(f"  Password: {MOCK_SUPER_ADMIN_PASSWORD}")


if __name__ == "__main__":
    main()
