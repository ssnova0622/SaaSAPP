# app/services/salon/appointments/no_show_block_service.py
"""No-show blocking: track no_show_count per customer (phone), block booking when count >= threshold, list blocked, reset."""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from pymongo import ReturnDocument

from app.helpers.date_utils import utcnow
from app.services.core.tenant_service import TenantService
from app.services.db import customers_collection
from app.helpers.phone_utils import normalize_phone
from app.services.ai.config_schema import get_effective_ai_config


def _normalized_phone(tenant: str, phone: str) -> str:
    if not phone:
        return ""
    cc = TenantService._get_tenant_country_code(tenant)
    return normalize_phone(phone, country_code=cc)


def _get_block_threshold(tenant: str) -> int:
    """Return no_show_block_threshold from tenant ai_config. 0 = disabled."""
    settings = TenantService.get_tenant_settings(tenant) or {}
    config = get_effective_ai_config(settings)
    return int(config.get("no_show_block_threshold") or 0)


def get_no_show_count(tenant: str, phone: str) -> int:
    """Return current no_show_count for this tenant+phone. 0 if no customer record."""
    col = customers_collection()
    norm = _normalized_phone(tenant, phone)
    if not norm:
        return 0
    doc = col.find_one({"tenant": tenant, "phone": norm}, {"no_show_count": 1})
    return int(doc.get("no_show_count", 0)) if doc else 0


def increment_no_show_count(tenant: str, phone: str, customer_name: Optional[str] = None) -> int:
    """Increment no_show_count for tenant+phone (upsert customer if needed). Returns new count."""
    col = customers_collection()
    norm = _normalized_phone(tenant, phone)
    if not norm:
        return 0
    now = utcnow()
    result = col.find_one_and_update(
        {"tenant": tenant, "phone": norm},
        {
            "$inc": {"no_show_count": 1},
            "$set": {"updated_at": now},
            "$setOnInsert": {"tenant": tenant, "phone": norm, "name": customer_name or "", "created_at": now},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(result.get("no_show_count", 0))


def is_blocked(tenant: str, phone: str) -> bool:
    """True if this phone is blocked from booking (no_show_count >= threshold)."""
    threshold = _get_block_threshold(tenant)
    if threshold <= 0:
        return False
    return get_no_show_count(tenant, phone) >= threshold


def list_blocked(tenant: str, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """List customers (phone, name, no_show_count) where no_show_count >= threshold. Optional search filters by phone or name (case-insensitive)."""
    threshold = _get_block_threshold(tenant)
    if threshold <= 0:
        return []
    col = customers_collection()
    query: Dict[str, Any] = {"tenant": tenant, "no_show_count": {"$gte": threshold}}
    if search and str(search).strip():
        import re
        term = re.escape(str(search).strip())
        pattern = f".*{term}.*"
        query["$or"] = [
            {"phone": {"$regex": pattern, "$options": "i"}},
            {"name": {"$regex": pattern, "$options": "i"}},
        ]
    cursor = col.find(
        query,
        {"phone": 1, "name": 1, "no_show_count": 1, "updated_at": 1},
    ).sort("no_show_count", -1)
    return [
        {
            "phone": d.get("phone", ""),
            "name": d.get("name", ""),
            "no_show_count": int(d.get("no_show_count", 0)),
            "updated_at": d.get("updated_at"),
        }
        for d in cursor
    ]


def reset_no_show(tenant: str, phone: str) -> Dict[str, Any]:
    """Set no_show_count to 0 for this customer. Returns updated customer snippet or error."""
    col = customers_collection()
    norm = _normalized_phone(tenant, phone)
    if not norm:
        return {"ok": False, "detail": "Invalid phone"}
    result = col.find_one_and_update(
        {"tenant": tenant, "phone": norm},
        {"$set": {"no_show_count": 0, "updated_at": utcnow()}},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        return {"ok": False, "detail": "Customer not found"}
    return {
        "ok": True,
        "phone": result.get("phone", norm),
        "name": result.get("name", ""),
        "no_show_count": 0,
    }
