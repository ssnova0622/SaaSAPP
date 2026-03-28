# app/services/store/offers_service.py
"""Tenant-created offers (today's offers, time-bound) for Store module. Customers can view active offers."""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from pymongo import ReturnDocument

from app.helpers.date_utils import utcnow
from app.services.db import get_db


class OffersService:
    @staticmethod
    def _col():
        return get_db().get_collection("store_offers")

    @classmethod
    def list_offers(
        cls,
        tenant: str,
        active_only: bool = False,
        page: int = 1,
        size: int = 50,
    ) -> Dict[str, Any]:
        """List offers for tenant. If active_only, return only those valid now (valid_from <= now <= valid_until)."""
        col = cls._col()
        q: Dict[str, Any] = {"tenant": tenant}
        now = utcnow()
        if active_only:
            q["valid_from"] = {"$lte": now}
            q["valid_until"] = {"$gte": now}
            q["active"] = True

        page = max(1, int(page or 1))
        size = max(1, min(100, int(size or 50)))
        skip = (page - 1) * size
        total = col.count_documents(q)
        items: List[Dict[str, Any]] = []
        for d in col.find(q).sort("valid_from", -1).skip(skip).limit(size):
            row = dict(d)
            row.pop("_id", None)
            items.append(row)
        return {"items": items, "total": total, "page": page, "size": size}

    @classmethod
    def list_active_offers(cls, tenant: str) -> List[Dict[str, Any]]:
        """Return list of offers currently valid (for display to customers)."""
        result = cls.list_offers(tenant=tenant, active_only=True, page=1, size=50)
        return result.get("items") or []

    @classmethod
    def get_offer(cls, tenant: str, offer_id: str) -> Optional[Dict[str, Any]]:
        col = cls._col()
        doc = col.find_one({"tenant": tenant, "id": offer_id})
        if not doc:
            return None
        out = dict(doc)
        out.pop("_id", None)
        return out

    @classmethod
    def create_offer(
        cls,
        tenant: str,
        title: str,
        description: str = "",
        valid_from: Optional[dt.datetime] = None,
        valid_until: Optional[dt.datetime] = None,
        product_skus: Optional[List[str]] = None,
        discount_info: Optional[Dict[str, Any]] = None,
        active: bool = True,
        user_id: Optional[str] = None,
        brochure_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        col = cls._col()
        now = utcnow()
        offer_id = f"OFF-{int(now.timestamp())}"
        v_from = valid_from if valid_from is not None else now
        v_until = valid_until if valid_until is not None else now
        doc = {
            "tenant": tenant,
            "id": offer_id,
            "title": str(title or "Offer").strip(),
            "description": str(description or "").strip(),
            "valid_from": v_from,
            "valid_until": v_until,
            "product_skus": list(product_skus or []),
            "discount_info": dict(discount_info or {}),
            "active": bool(active),
            "created_at": now,
            "updated_at": now,
            "created_by": user_id,
            "updated_by": user_id,
        }
        if brochure_url and str(brochure_url).strip():
            doc["brochure_url"] = str(brochure_url).strip()
        col.insert_one(doc)
        doc.pop("_id", None)
        return doc

    @classmethod
    def update_offer(
        cls,
        tenant: str,
        offer_id: str,
        updates: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        col = cls._col()
        allowed = {"title", "description", "valid_from", "valid_until", "product_skus", "discount_info", "active", "brochure_url"}
        payload = {k: v for k, v in updates.items() if k in allowed}
        if not payload:
            return cls.get_offer(tenant, offer_id)
        payload["updated_at"] = utcnow()
        payload["updated_by"] = user_id
        doc = col.find_one_and_update(
            {"tenant": tenant, "id": offer_id},
            {"$set": payload},
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            return None
        out = dict(doc)
        out.pop("_id", None)
        return out

    @classmethod
    def delete_offer(cls, tenant: str, offer_id: str) -> bool:
        col = cls._col()
        res = col.delete_one({"tenant": tenant, "id": offer_id})
        return res.deleted_count > 0
