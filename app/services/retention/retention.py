from __future__ import annotations
from datetime import datetime, timezone, date
from typing import Dict, Any, List, Optional, Tuple
from pymongo import ASCENDING
from app.services.db import get_db
from app.core.container import get_tenant_service
from app.helpers.date_utils import format_date_for_tenant


# --- Helpers ---

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _retention_col():
    db = get_db()
    col = db.get_collection("retention_metrics")
    col.create_index([("tenant", ASCENDING), ("date", ASCENDING)], unique=True)
    return col


def _appointments_col():
    db = get_db()
    return db.get_collection("appointments")


def _customers_col():
    db = get_db()
    return db.get_collection("customers")


# --- Core computation ---

def compute_segments_for_tenant(tenant: str, as_of: Optional[datetime] = None) -> Tuple[
    Dict[str, Any], List[Dict[str, Any]]]:
    """
    Compute retention segments using last booking time per customer based on appointments.created_at (status='booked').
    Segments:
      - active: last_visit_age_days <= 30
      - at_risk: 31 <= days <= 60
      - churned: days > 60
    Returns (summary, raw list of {phone, name, last_visit_at, days}).
    """
    now = as_of or _now_utc()
    appts = _appointments_col()
    pipeline = [
        {"$match": {"tenant": tenant, "status": "booked"}},
        {"$group": {
            "_id": "$customer_phone",
            "last_visit_at": {"$max": "$created_at"},
            "name": {"$last": "$customer_name"},
        }},
    ]
    rows: List[Dict[str, Any]] = []
    for g in appts.aggregate(pipeline):
        phone = g.get("_id")
        last_visit: Optional[datetime] = g.get("last_visit_at")
        if not phone or not isinstance(last_visit, datetime):
            continue
        # Normalize tz awareness
        if last_visit.tzinfo is None:
            last_visit = last_visit.replace(tzinfo=timezone.utc)
        days = (now - last_visit).days
        rows.append({
            "phone": phone,
            "name": g.get("name"),
            "last_visit_at": last_visit,
            "days": days,
        })

    summary = {"tenant": tenant, "active": 0, "at_risk": 0, "churned": 0}
    for r in rows:
        d = r["days"]
        if d <= 30:
            summary["active"] += 1
        elif 31 <= d <= 60:
            summary["at_risk"] += 1
        else:
            summary["churned"] += 1
    return summary, rows


def aggregate_and_store_for_all_tenants(as_of_date: Optional[date] = None) -> None:
    """Nightly job: compute and store retention metrics for all tenants for the given date (UTC)."""
    db = get_db()
    tenants = db.get_collection("tenants")
    col = _retention_col()
    the_date = as_of_date or _now_utc().date()
    for t in tenants.find({}, {"_id": 1}):
        tenant = t.get("_id")
        if not tenant:
            continue
        summary, _ = compute_segments_for_tenant(tenant)
        doc = {
            "tenant": tenant,
            "date": the_date.isoformat(),
            "active": int(summary.get("active", 0)),
            "at_risk": int(summary.get("at_risk", 0)),
            "churned": int(summary.get("churned", 0)),
            "created_at": _now_utc(),
        }
        col.update_one({"tenant": tenant, "date": the_date.isoformat()}, {"$set": doc}, upsert=True)


# --- Public API used by router ---

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
    # Compute on the fly
    summary, _ = compute_segments_for_tenant(tenant)
    summary["date"] = _now_utc().date().isoformat()
    return summary


def list_by_segment(tenant: str, segment: str, days: Optional[int] = None, page: int = 1, size: int = 50) -> Dict[
    str, Any]:
    """
    Return customers belonging to a segment computed from appointments created_at.
    segment in {"active", "at_risk", "churned"}
    days parameter overrides the boundary midpoint for at_risk (default 45) when segment=='at_risk'.
    """
    _, rows = compute_segments_for_tenant(tenant)
    page = max(1, int(page or 1))
    size = max(1, min(200, int(size or 50)))

    def _predicate(r: Dict[str, Any]) -> bool:
        d = r.get("days", 10 ** 9)
        if segment == "active":
            return d <= 30
        if segment == "at_risk":
            lo = 31
            hi = (days or 60)
            return lo <= d <= hi
        if segment == "churned":
            return d > 60 if days is None else d > int(days)
        return False

    filtered = [r for r in rows if _predicate(r)]
    total = len(filtered)
    start = (page - 1) * size
    end = start + size
    items = filtered[start:end]

    # Enrich with email if present in customers collection
    if items:
        cust = _customers_col()
        phones = [it.get("phone") for it in items if it.get("phone")]
        if phones:
            mp: Dict[str, Optional[str]] = {}
            for c in cust.find({"tenant": tenant, "phone": {"$in": phones}}, {"_id": 0, "phone": 1, "email": 1}):
                mp[c.get("phone")] = c.get("email")
            for it in items:
                it["email"] = mp.get(it.get("phone"))

    # Normalize output
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    for it in items:
        lv = it.get("last_visit_at")
        if isinstance(lv, datetime):
            it["last_visit_at"] = format_date_for_tenant(lv.date(), settings)
    return {"items": items, "total": total, "page": page, "size": size}
