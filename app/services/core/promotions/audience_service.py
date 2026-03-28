# app/services/core/promotions/audience_service.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

from app.helpers.phone_utils import normalize_promo_phone
from app.services.db import customers_collection
from app.services.core import retention_service as retention_svc


class AudienceService:
    @staticmethod
    def resolve(tenant: str, audience: Dict[str, Any]) -> List[Dict[str, Any]]:
        col = customers_collection()
        typ = (audience.get("type") or "all").lower()
        recipients: List[Dict[str, Any]] = []

        if typ == "all":
            for c in col.find({"tenant": tenant, "active": True}, {"_id": 0}).sort("name", 1):
                recipients.append({"phone": c.get("phone"), "email": c.get("email"), "name": c.get("name")})

        elif typ == "tags":
            tags = [t.strip() for t in (audience.get("tags") or []) if isinstance(t, str) and t.strip()]
            if tags:
                q = {"tenant": tenant, "tags": {"$in": tags}, "active": True}
                for c in col.find(q, {"_id": 0}).sort("name", 1):
                    recipients.append({"phone": c.get("phone"), "email": c.get("email"), "name": c.get("name")})

        elif typ == "segment":
            seg = audience.get("segment") or {}
            seg_type = seg.get("type")
            seg_days = seg.get("days")
            if seg_type:
                res = retention_svc.list_by_segment(tenant, seg_type, days=seg_days, page=1, size=100000)
                for r in res.get("items") or []:
                    recipients.append({"phone": r.get("phone"), "email": r.get("email"), "name": r.get("name")})

        elif typ == "custom":
            phones = [str(p).strip() for p in (audience.get("phones") or []) if str(p).strip()]
            emails = [str(e).strip() for e in (audience.get("emails") or []) if str(e).strip()]
            for p in phones:
                recipients.append({"phone": normalize_promo_phone(p), "email": None, "name": None})
            for e in emails:
                recipients.append({"phone": None, "email": e, "name": None})

        # dedupe
        seen: set[Tuple[Optional[str], Optional[str]]] = set()
        uniq: List[Dict[str, Any]] = []
        for r in recipients:
            key = (r.get("phone"), r.get("email"))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(r)
        return uniq
