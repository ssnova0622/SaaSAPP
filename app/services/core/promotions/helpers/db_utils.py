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
    # Allow multiple deliveries per recipient (resend) via send_batch_id on each log row.
    for ix in list(col.list_indexes()):
        key = ix.get("key") or {}
        if ix.get("unique") and set(key.keys()) == {"promotion_id", "channel", "to"} and len(key) == 3:
            try:
                col.drop_index(ix["name"])
            except Exception:
                pass
            break
    try:
        col.create_index(
            [
                ("promotion_id", ASCENDING),
                ("channel", ASCENDING),
                ("to", ASCENDING),
                ("send_batch_id", ASCENDING),
            ],
            unique=True,
        )
    except Exception:
        pass
    return col
