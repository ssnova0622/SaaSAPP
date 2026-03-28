# app/services/core/promotions/helpers/db_utils.py
from __future__ import annotations
from pymongo import ASCENDING
from pymongo.collection import Collection
from app.services.db import get_db


def promotions_col() -> Collection:
    db = get_db()
    col = db.get_collection("promotions")
    col.create_index([("tenant", ASCENDING)])
    col.create_index([("tenant", ASCENDING), ("status", ASCENDING)])
    col.create_index([("tenant", ASCENDING), ("schedule_at", ASCENDING)])
    return col


def promotion_logs_col() -> Collection:
    db = get_db()
    col = db.get_collection("promotion_logs")
    col.create_index([("tenant", ASCENDING)])
    col.create_index([("promotion_id", ASCENDING)])
    col.create_index([("tenant", ASCENDING), ("sent_at", ASCENDING)])
    col.create_index([("tenant", ASCENDING), ("status", ASCENDING)])
    col.create_index([("tenant", ASCENDING), ("channel", ASCENDING)])
    try:
        col.create_index(
            [("promotion_id", ASCENDING), ("channel", ASCENDING), ("to", ASCENDING)],
            unique=True,
        )
    except Exception:
        pass
    return col
