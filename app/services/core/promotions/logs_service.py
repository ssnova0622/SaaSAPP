# app/services/core/promotions/logs_service.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from .helpers.db_utils import promotion_logs_col


class PromotionLogsService:
    @staticmethod
    def insert_safe(doc: Dict[str, Any]) -> None:
        col = promotion_logs_col()
        try:
            col.insert_one(doc)
        except DuplicateKeyError:
            pass

    @staticmethod
    def list_logs(
            tenant: str,
            prom_id: str,
            page: int = 1,
            size: int = 50,
            status: Optional[str] = None,
            channel: Optional[str] = None,
            from_ts: Optional[datetime] = None,
            to_ts: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        logs = promotion_logs_col()
        try:
            _id = ObjectId(prom_id)
        except Exception:
            return {"items": [], "total": 0, "page": page, "size": size}

        q: Dict[str, Any] = {"tenant": tenant, "promotion_id": _id}
        if status:
            q["status"] = status
        if channel:
            q["channel"] = channel
        if from_ts or to_ts:
            srange: Dict[str, Any] = {}
            if from_ts:
                srange["$gte"] = from_ts
            if to_ts:
                srange["$lte"] = to_ts
            q["sent_at"] = srange

        page = max(1, int(page or 1))
        size = max(1, min(200, int(size or 50)))
        skip = (page - 1) * size

        total = logs.count_documents(q)
        items: List[Dict[str, Any]] = []
        for d in logs.find(q).sort("sent_at", -1).skip(skip).limit(size):
            d["id"] = str(d.pop("_id"))
            d["promotion_id"] = str(d.get("promotion_id"))
            items.append(d)

        return {"items": items, "total": total, "page": page, "size": size}
