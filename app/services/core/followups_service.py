# app/services/core/followups_service.py
from __future__ import annotations
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
import logging
from pymongo import ASCENDING
from pymongo.collection import Collection

from ..db import customers_collection
from .messaging_service import Messaging
from . import message_templates as msg_tpl
from app.core.container import get_tenant_service
from app.core.realtime import get_notifier
from ...helpers.date_utils import utcnow

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Core Helpers
# ----------------------------------------------------------------------


def _broadcast(event: Dict[str, Any]) -> None:
    """Safe websocket broadcast."""
    try:
        import anyio

        async def _send():
            await get_notifier().broadcast(event)

        anyio.run(_send)
    except Exception:
        logger.debug("WS broadcast skipped: %s", event.get("type"))


from app.repositories.followup_repository import FollowupRepository

followup_repo = FollowupRepository()


def _col() -> Collection:
    """Follow-ups collection with ensured indexes."""
    col = followup_repo.get_collection()
    col.create_index([("tenant", ASCENDING), ("run_at", ASCENDING), ("status", ASCENDING)])
    col.create_index([("tenant", ASCENDING), ("appointment_id", ASCENDING)])
    return col


# ----------------------------------------------------------------------
# Message Templates (tenant-configurable via message_templates service)
# ----------------------------------------------------------------------

# Map follow-up type to message_templates key
_FOLLOWUP_TEMPLATE_KEYS = {
    "confirm": "followup_confirm",
    "reminder24": "followup_reminder24",
    "reminder2": "followup_reminder2",
    "post": "followup_post",
    "recovery": "followup_recovery",
}


def format_message(tenant: str, ftype: str, payload: Dict[str, Any]) -> str:
    """Resolve follow-up message from tenant-configurable templates."""
    key = _FOLLOWUP_TEMPLATE_KEYS.get(ftype, "followup_default")
    return msg_tpl.get_message(
        tenant,
        key,
        name=payload.get("customer_name", "Customer"),
        pro=payload.get("professional", "our team"),
        time=payload.get("time", "your scheduled time"),
        tenant=payload.get("tenant", "our service"),
    )


# ----------------------------------------------------------------------
# Scheduling Logic
# ----------------------------------------------------------------------

SCHEDULE_OFFSETS = {
    "confirm": timedelta(hours=0),
    "reminder24": timedelta(hours=24),
    "reminder2": timedelta(hours=2),
    "post": timedelta(hours=4),
}


def _followup_prefs_for_tenant(tenant: str) -> Dict[str, bool]:
    """Which follow-up event types are enabled for this tenant. Default: all True."""
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    prefs = settings.get("followup_prefs") or {}
    if not isinstance(prefs, dict):
        return {k: True for k in SCHEDULE_OFFSETS}
    return {
        ftype: bool(prefs.get(ftype, True))
        for ftype in SCHEDULE_OFFSETS
    }


def schedule_for_appointment(
        *,
        tenant: str,
        appointment_id: str,
        customer_name: str,
        customer_phone: Optional[str],
        customer_email: Optional[str],
        professional: str,
        time_label: str,
        tenant_tz: Optional[str] = None,
) -> None:
    """Create follow-up tasks for an appointment. Only event types enabled in tenant followup_prefs are scheduled."""
    col = _col()
    now = utcnow()
    prefs = _followup_prefs_for_tenant(tenant)

    payload = {
        "customer_name": customer_name,
        "professional": professional,
        "time": time_label,
        "tenant": tenant,
    }

    docs = []
    for ftype, offset in SCHEDULE_OFFSETS.items():
        if not prefs.get(ftype, True):
            continue
        docs.append({
            "tenant": tenant,
            "appointment_id": appointment_id,
            "to_phone": (customer_phone or "").strip() or None,
            "to_email": (customer_email or "").strip() or None,
            "type": ftype,
            "run_at": now + offset,
            "status": "scheduled",
            "attempts": 0,
            "last_error": None,
            "created_at": now,
            "payload": payload,
        })

    if docs:
        col.insert_many(docs)


def cancel_for_appointment(tenant: str, appointment_id: str) -> int:
    """Cancel all pending follow-ups for an appointment."""
    res = followup_repo.get_collection().update_many(
        {"tenant": tenant, "appointment_id": appointment_id, "status": "scheduled"},
        {"$set": {"status": "canceled", "canceled_at": utcnow()}},
    )
    return int(res.modified_count or 0)


# ----------------------------------------------------------------------
# Listing
# ----------------------------------------------------------------------

def list_followups(
        tenant: str,
        status: Optional[str] = None,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        page: int = 1,
        size: int = 50,
) -> Dict[str, Any]:
    q: Dict[str, Any] = {"tenant": tenant}

    if status:
        q["status"] = status

    if from_ts or to_ts:
        q["run_at"] = {}
        if from_ts:
            q["run_at"]["$gte"] = from_ts
        if to_ts:
            q["run_at"]["$lte"] = to_ts

    if customer_phone:
        q["to_phone"] = {"$regex": customer_phone, "$options": "i"}

    if customer_name:
        q["payload.customer_name"] = {"$regex": customer_name, "$options": "i"}

    total = followup_repo.count_documents(q)

    page = max(1, int(page))
    size = max(1, min(200, int(size)))
    skip = (page - 1) * size

    items = followup_repo.find_many_raw(q, limit=size, skip=skip, sort=[("run_at", 1)])
    for d in items:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))

    return {"items": items, "total": total, "page": page, "size": size}


# ----------------------------------------------------------------------
# Cancel Single Follow-up
# ----------------------------------------------------------------------

def cancel_followup(tenant: str, followup_id: str) -> bool:
    from bson import ObjectId

    col = _col()
    try:
        oid = ObjectId(followup_id)
    except Exception:
        return False

    res = col.update_one(
        {"_id": oid, "tenant": tenant, "status": "scheduled"},
        {"$set": {"status": "canceled", "canceled_at": utcnow()}},
    )
    return bool(res.modified_count)


# ----------------------------------------------------------------------
# Dispatcher
# ----------------------------------------------------------------------

def process_due_followups(max_batch: int = 200) -> None:
    """Send due follow-ups."""
    col = _col()
    now = utcnow()

    cursor = col.find(
        {"status": "scheduled", "run_at": {"$lte": now}}
    ).sort("run_at", 1).limit(max_batch)

    for doc in cursor:
        _process_single_followup(col, doc)


def _process_single_followup(col: Collection, doc: Dict[str, Any]) -> None:
    _id = doc["_id"]
    tenant = doc["tenant"]
    ftype = doc["type"]
    to_phone = doc.get("to_phone")
    to_email = doc.get("to_email")
    payload = doc.get("payload") or {}

    msg = format_message(tenant, ftype, payload)
    sent = False
    error = None

    # Skip inactive customers
    if to_phone:
        try:
            cust = customers_collection().find_one(
                {"tenant": tenant, "phone": to_phone},
                {"active": 1}
            )
            if cust and not cust.get("active", True):
                _mark_skipped(col, _id, tenant, ftype, "inactive_customer")
                return
        except Exception:
            pass

    # Try sending
    try:
        if to_phone:
            try:
                Messaging.send_whatsapp_text(to_phone, msg, tenant=tenant)
                sent = True
            except Exception as e:
                error = str(e)

        if to_email:
            try:
                Messaging.send_email(
                    to_email,
                    f"{ftype.title()} - {payload.get('tenant', '')}",
                    msg,
                    tenant=tenant,
                )
                sent = True
            except Exception as e:
                error = (error or "") + f"; {e}"

    except Exception as e:
        error = str(e)

    # Update status
    if sent:
        _mark_sent(col, _id, tenant, ftype)
    else:
        _mark_failed(col, _id, tenant, ftype, error)


# ----------------------------------------------------------------------
# Status Update Helpers
# ----------------------------------------------------------------------

def _mark_sent(col: Collection, _id, tenant: str, ftype: str) -> None:
    col.update_one(
        {"_id": _id},
        {"$set": {"status": "sent", "sent_at": utcnow()}, "$inc": {"attempts": 1}},
    )
    _broadcast({"type": "followup.sent", "tenant": tenant, "followup_id": str(_id), "f_type": ftype})


def _mark_failed(col: Collection, _id, tenant: str, ftype: str, error: Optional[str]) -> None:
    col.update_one(
        {"_id": _id},
        {"$set": {"status": "failed", "last_error": error, "failed_at": utcnow()}, "$inc": {"attempts": 1}},
    )
    _broadcast({
        "type": "followup.failed",
        "tenant": tenant,
        "followup_id": str(_id),
        "f_type": ftype,
        "error": error,
    })


def _mark_skipped(col: Collection, _id, tenant: str, ftype: str, reason: str) -> None:
    col.update_one(
        {"_id": _id},
        {"$set": {"status": "skipped", "reason": reason, "skipped_at": utcnow()}, "$inc": {"attempts": 1}},
    )
    _broadcast({
        "type": "followup.skipped",
        "tenant": tenant,
        "followup_id": str(_id),
        "f_type": ftype,
        "reason": reason,
    })
