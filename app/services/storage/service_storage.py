"""Salon/tenant services CRUD (e.g. Hair Cut, Eye Doctor)."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from pymongo import ReturnDocument

from app.services.db import services_collection
from app.helpers.audit_utils import audit_fields_for_create, audit_fields_for_update

logger = logging.getLogger(__name__)


class ServiceStorage:
    @classmethod
    def create_service(
        cls,
        tenant: str,
        name: str,
        description: Optional[str] = None,
        price: float = 0.0,
        duration: int = 30,
        active: bool = True,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        col = services_collection()
        if col.find_one({"tenant": tenant, "name": name.strip()}):
            raise ValueError(f"Service '{name}' already exists for this tenant")
        audit = audit_fields_for_create(user_id)
        doc = {
            "tenant": tenant,
            "name": name.strip(),
            "description": (description or "").strip(),
            "price": float(price or 0.0),
            "duration": int(duration or 30),
            "active": bool(active),
            "created_at": audit["created_at"],
            "updated_at": audit["updated_at"],
            "created_by": audit["created_by"],
            "updated_by": audit["updated_by"],
        }
        try:
            col.insert_one(doc)
        except Exception as e:
            if "E11000" in str(e):
                raise ValueError(f"Service '{name}' already exists for this tenant")
            logger.exception("create_service failed for tenant=%s name=%s", tenant, name)
            raise
        out = dict(doc)
        out.pop("_id", None)
        return out

    @classmethod
    def list_services(cls, tenant: str, active: Optional[bool] = None) -> List[Dict[str, Any]]:
        col = services_collection()
        q: Dict[str, Any] = {"tenant": tenant}
        if active is not None:
            q["active"] = bool(active)
        items = []
        for d in col.find(q).sort("name", 1):
            row = dict(d)
            row.pop("_id", None)
            items.append(row)
        return items

    @classmethod
    def update_service(
        cls,
        tenant: str,
        name: str,
        updates: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        col = services_collection()
        updates.update(audit_fields_for_update(user_id))
        res = col.find_one_and_update(
            {"tenant": tenant, "name": name},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        return dict(res) if res else None

    @classmethod
    def delete_service(cls, tenant: str, name: str) -> bool:
        col = services_collection()
        res = col.delete_one({"tenant": tenant, "name": name})
        return res.deleted_count > 0
