# app/services/store/reports_service.py
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

from app.helpers.date_utils import utcnow
from app.services.db import get_db
from app.services.store.helpers.constants import ORDER_STATUS_CANCELED


class ReportsService:
    @staticmethod
    def _orders():
        return get_db().get_collection("orders")

    # ---------------- Reports ----------------

    @classmethod
    def top_sellers(cls, tenant: str, days: int = 30, top: int = 20) -> List[Dict[str, Any]]:
        col = cls._orders()
        window_start = utcnow() - dt.timedelta(days=days)

        pipeline = [
            {"$match": {"tenant": tenant, "status": {"$ne": ORDER_STATUS_CANCELED}, "created_at": {"$gte": window_start}}},
            {"$unwind": "$items"},
            {
                "$group": {
                    "_id": "$items.sku",
                    "total_qty": {"$sum": "$items.qty"},
                    "total_revenue": {"$sum": {"$multiply": ["$items.qty", "$items.price_snapshot"]}},
                    "name": {"$first": "$items.name"},
                }
            },
            {"$sort": {"total_qty": -1}},
            {"$limit": top},
        ]

        cursor = col.aggregate(pipeline)
        return [
            {
                "sku": d["_id"],
                "name": d.get("name") or d["_id"],
                "total_qty": d["total_qty"],
                "total_revenue": round(d["total_revenue"], 2),
            }
            for d in cursor
        ]
