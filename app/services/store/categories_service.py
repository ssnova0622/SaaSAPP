# app/services/store/categories_service.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.helpers.date_utils import utcnow
from app.services.db import get_db
from app.services.store.helpers.validation_helper import StoreValidationHelper


class CategoryService:
    @staticmethod
    def _col():
        return get_db().get_collection("categories")

    @classmethod
    def list_categories(cls, tenant: str) -> List[Dict[str, Any]]:
        col = cls._col()
        items: List[Dict[str, Any]] = []
        for d in col.find({"tenant": tenant}).sort("name", 1):
            row = {
                "name": d.get("name"),
                "active": bool(d.get("active", True)),
                "created_by": d.get("created_by"),
                "updated_by": d.get("updated_by"),
            }
            items.append(row)
        return items

    @classmethod
    def upsert_category(
        cls,
        tenant: str,
        name: str,
        active: bool = True,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        col = cls._col()
        name = StoreValidationHelper.require_non_empty_str(name, "Category name")

        now = utcnow()
        payload = {
            "tenant": tenant,
            "name": name,
            "active": bool(active),
            "updated_at": now,
            "updated_by": user_id,
        }

        existing = col.find_one({"tenant": tenant, "name": name})
        if not existing:
            payload["created_at"] = now
            payload["created_by"] = user_id

        col.update_one({"tenant": tenant, "name": name}, {"$set": payload}, upsert=True)
        return {"name": name, "active": bool(active), "created_by": user_id, "updated_by": user_id}

    @classmethod
    def delete_category(
        cls,
        tenant: str,
        name: str,
        user_id: Optional[str] = None,
    ) -> bool:
        col = cls._col()
        res = col.delete_one({"tenant": tenant, "name": name})
        return res.deleted_count > 0
