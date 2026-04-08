# app/services/core/retention_service.py
from __future__ import annotations

# ============================================================
# Imports
# ============================================================

from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional, Tuple
from pymongo import ASCENDING
from app.services.core.tenant_service import TenantService
from app.helpers.date_utils import format_date_for_tenant, utcnow
from app.helpers.phone_util import PhoneUtil

# ============================================================
# DB Helpers
# ============================================================

from app.repositories.retention_repository import RetentionRepository
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.customer_repository import CustomerRepository

retention_repo = RetentionRepository()
appt_repo = AppointmentRepository()
cust_repo = CustomerRepository()


def _retention_col():
    col = retention_repo.get_collection()
    col.create_index([("tenant", ASCENDING), ("date", ASCENDING)], unique=True)
    return col


def _appointments_col():
    return appt_repo.get_collection()


def _customers_col():
    return cust_repo.get_collection()


# ============================================================
# Tenant Config Helpers
# ============================================================

DEFAULT_ACTIVE_DAYS = 30
DEFAULT_AT_RISK_DAYS = 60


def _get_retention_thresholds(tenant: str) -> Tuple[int, int]:
    """
    Returns (active_days, at_risk_days) from tenant settings.
    Falls back to defaults if not configured.
    """
    settings = TenantService.get_tenant_settings(tenant) or {}
    cfg = settings.get("retention_config") or {}

    active_days = int(cfg.get("active_days", DEFAULT_ACTIVE_DAYS))
    at_risk_days = int(cfg.get("at_risk_days", DEFAULT_AT_RISK_DAYS))

    # Ensure logical ordering
    if at_risk_days < active_days:
        at_risk_days = active_days + 1

    return active_days, at_risk_days


# ============================================================
# Utility Helpers
# ============================================================

def _normalize_dt(dt_val: datetime) -> datetime:
    """Ensure datetime is timezone-aware (UTC)."""
    if dt_val.tzinfo is None:
        return dt_val.replace(tzinfo=timezone.utc)
    return dt_val


def _segment_for_days(days: int, active_days: int, at_risk_days: int) -> str:
    if days <= active_days:
        return "active"
    if active_days < days <= at_risk_days:
        return "at_risk"
    return "churned"


# ============================================================
# Core Computation
# ============================================================

def compute_segments_for_tenant(
        tenant: str,
        as_of: Optional[datetime] = None
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Compute retention segments using last booking time per customer.
    Segments are tenant-configurable:
      - active: days <= active_days
      - at_risk: active_days < days <= at_risk_days
      - churned: days > at_risk_days
    """
    now = _normalize_dt(as_of or utcnow())
    active_days, at_risk_days = _get_retention_thresholds(tenant)

    pipeline = [
        {"$match": {"tenant": tenant, "status": "booked"}},
        {
            "$addFields": {
                "customer_e164": {
                    "$cond": {
                        "if": {
                            "$and": [
                                {"$ne": [{"$ifNull": ["$customer_phone_number", None]}, None]},
                                {"$ne": [{"$ifNull": ["$customer_phone_number.code", ""]}, ""]},
                                {"$ne": [{"$ifNull": ["$customer_phone_number.number", ""]}, ""]},
                            ]
                        },
                        "then": {
                            "$concat": [
                                "+",
                                {
                                    "$replaceAll": {
                                        "input": "$customer_phone_number.code",
                                        "find": "+",
                                        "replacement": "",
                                    }
                                },
                                "$customer_phone_number.number",
                            ]
                        },
                        "else": {"$ifNull": ["$customer_phone", ""]},
                    }
                }
            }
        },
        {
            "$group": {
                "_id": "$customer_e164",
                "last_visit_at": {"$max": "$created_at"},
                "name": {"$last": "$customer_name"},
            }
        },
    ]

    rows: List[Dict[str, Any]] = []
    for g in appt_repo.aggregate(pipeline):
        phone = g.get("_id")
        last_visit = g.get("last_visit_at")

        if not phone or not isinstance(last_visit, datetime):
            continue

        last_visit = _normalize_dt(last_visit)
        days = (now - last_visit).days

        rows.append({
            "phone": phone,
            "name": g.get("name"),
            "last_visit_at": last_visit,
            "days": days,
            "segment": _segment_for_days(days, active_days, at_risk_days),
        })

    summary = {"tenant": tenant, "active": 0, "at_risk": 0, "churned": 0}
    for r in rows:
        summary[r["segment"]] += 1

    return summary, rows


# ============================================================
# Nightly Aggregation
# ============================================================

def aggregate_and_store_for_all_tenants(as_of_date: Optional[date] = None) -> None:
    """
    Nightly job: compute and store retention metrics for all tenants.
    """
    tenants = TenantService.list_tenants()
    the_date = as_of_date or utcnow().date()

    for t in tenants:
        tenant = t.get("tenant") or t.get("_id")
        if not tenant:
            continue

        summary, _ = compute_segments_for_tenant(tenant)

        doc = {
            "tenant": tenant,
            "date": the_date.isoformat(),
            "active": int(summary["active"]),
            "at_risk": int(summary["at_risk"]),
            "churned": int(summary["churned"]),
            "created_at": utcnow(),
        }

        retention_repo.update_one_raw(
            {"tenant": tenant, "date": the_date.isoformat()},
            {"$set": doc},
            upsert=True
        )


# ============================================================
# Public Summary API
# ============================================================

def get_summary(tenant: str, use_cached: bool = True) -> Dict[str, Any]:
    col = _retention_col()

    if use_cached:
        d = col.find_one({"tenant": tenant}, sort=[("date", -1)])
        if d:
            return {
                "tenant": tenant,
                "date": d.get("date"),
                "active": int(d.get("active", 0)),
                "at_risk": int(d.get("at_risk", 0)),
                "churned": int(d.get("churned", 0)),
            }

    summary, _ = compute_segments_for_tenant(tenant)
    summary["date"] = utcnow().date().isoformat()
    return summary


# ============================================================
# Segment Listing API
# ============================================================

def list_by_segment(
        tenant: str,
        segment: str,
        days: Optional[int] = None,
        page: int = 1,
        size: int = 50
) -> Dict[str, Any]:
    """
    Return customers belonging to a segment.
    Segment boundaries are tenant-configurable.
    If `days` is provided for churned/at_risk, it overrides the upper bound.
    """
    summary, rows = compute_segments_for_tenant(tenant)

    active_days, at_risk_days = _get_retention_thresholds(tenant)

    # Override logic for custom days
    if segment == "at_risk" and days:
        at_risk_days = int(days)
    if segment == "churned" and days:
        at_risk_days = int(days)

    def _match(r: Dict[str, Any]) -> bool:
        d = r["days"]
        if segment == "active":
            return d <= active_days
        if segment == "at_risk":
            return active_days < d <= at_risk_days
        if segment == "churned":
            return d > at_risk_days
        return False

    filtered = [r for r in rows if _match(r)]
    total = len(filtered)

    page = max(1, int(page or 1))
    size = max(1, min(200, int(size or 50)))
    start = (page - 1) * size
    items = filtered[start:start + size]

    # Enrich with email
    if items:
        cust = _customers_col()
        dial = TenantService._get_tenant_country_code(tenant) or PhoneUtil.DEFAULT_DIAL_DIGITS
        email_map: Dict[str, Any] = {}
        for it in items:
            ph = it.get("phone")
            if not ph:
                continue
            doc = cust.find_one(PhoneUtil.customer_match_query(tenant, str(ph), dial), {"email": 1})
            if doc:
                email_map[str(ph)] = doc.get("email")
        for it in items:
            ph = it.get("phone")
            it["email"] = email_map.get(str(ph)) if ph else None

    # Format last_visit_at for tenant timezone
    settings = TenantService.get_tenant_settings(tenant) or {}
    for it in items:
        lv = it.get("last_visit_at")
        if isinstance(lv, datetime):
            it["last_visit_at"] = format_date_for_tenant(lv.date(), settings)

    return {"items": items, "total": total, "page": page, "size": size}
