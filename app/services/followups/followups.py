from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
import logging

from pymongo import ASCENDING
from pymongo.collection import Collection

from app.services.db import get_db, customers_collection
from app.services.messaging.messaging import Messaging
from app.core.realtime import get_notifier

logger = logging.getLogger(__name__)


# ---- Helpers ----
def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _broadcast_safe(event: Dict[str, Any]) -> None:
    try:
        import anyio

        async def _send():
            await get_notifier().broadcast(event)

        anyio.run(_send)
    except Exception:
        logger.debug("WS broadcast skipped: %s", event.get("type"))


def _col() -> Collection:
    db = get_db()
    col = db.get_collection("followups")
    # indexes
    col.create_index([("tenant", ASCENDING), ("run_at", ASCENDING), ("status", ASCENDING)])
    col.create_index([("tenant", ASCENDING), ("appointment_id", ASCENDING)])
    return col


# ---- API layer helpers ----
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
    """
    Enqueue follow-ups for a newly created appointment.
    Schedules: confirm (now), reminder24 (T-24h), reminder2 (T-2h), post (T+4h).
    Times are computed in UTC with simple offsets from current UTC time for MVP.
    """
    col = _col()
    now = _now_utc()
    items: List[Dict[str, Any]] = []

    def _mk(ftype: str, run_at: datetime) -> Dict[str, Any]:
        return {
            "tenant": tenant,
            "appointment_id": appointment_id,
            "to_phone": (customer_phone or "").strip() or None,
            "to_email": (customer_email or "").strip() or None,
            "type": ftype,
            "run_at": run_at,
            "status": "scheduled",
            "attempts": 0,
            "last_error": None,
            "created_at": now,
            "payload": {
                "customer_name": customer_name,
                "professional": professional,
                "time": time_label,
                "tenant": tenant,
            },
        }

    items.append(_mk("confirm", now))
    items.append(_mk("reminder24", now + timedelta(hours=24)))
    items.append(_mk("reminder2", now + timedelta(hours=2)))
    items.append(_mk("post", now + timedelta(hours=4)))

    if items:
        col.insert_many(items)


def cancel_for_appointment(tenant: str, appointment_id: str) -> int:
    """Cancel all pending follow-ups for the given appointment."""
    col = _col()
    res = col.update_many(
        {"tenant": tenant, "appointment_id": appointment_id, "status": "scheduled"},
        {"$set": {"status": "canceled", "canceled_at": _now_utc()}},
    )
    return int(res.modified_count or 0)


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
    col = _col()
    q: Dict[str, Any] = {"tenant": tenant}
    if status:
        q["status"] = status
    if from_ts or to_ts:
        r: Dict[str, Any] = {}
        if from_ts:
            r["$gte"] = from_ts
        if to_ts:
            r["$lte"] = to_ts
        q["run_at"] = r
    if customer_phone:
        q["to_phone"] = {"$regex": customer_phone, "$options": "i"}
    if customer_name:
        q["payload.customer_name"] = {"$regex": customer_name, "$options": "i"}
    total = col.count_documents(q)
    page = max(1, int(page or 1))
    size = max(1, min(200, int(size or 50)))
    skip = (page - 1) * size
    items: List[Dict[str, Any]] = []
    for d in col.find(q).sort("run_at", 1).skip(skip).limit(size):
        d["id"] = str(d.pop("_id"))
        items.append(d)
    return {"items": items, "total": total, "page": page, "size": size}


def cancel_followup(tenant: str, followup_id: str) -> bool:
    from bson import ObjectId

    col = _col()
    try:
        _id = ObjectId(followup_id)
    except Exception:
        return False
    res = col.update_one({"_id": _id, "tenant": tenant, "status": "scheduled"}, {"$set": {"status": "canceled", "canceled_at": _now_utc()}})
    return bool(res.modified_count)


# ---- Dispatcher ----
def _format_message(ftype: str, payload: Dict[str, Any]) -> str:
    name = payload.get("customer_name") or "Customer"
    professional = payload.get("professional") or "our team"
    time_label = payload.get("time") or "your scheduled time"
    tenant = payload.get("tenant") or "our service"

    if ftype == "confirm":
        return f"Hi {name}, your booking with {professional} at {time_label} is confirmed. - {tenant}"
    if ftype == "reminder24":
        return f"Reminder: {professional} at {time_label} tomorrow. Reply 1 to confirm, 2 to reschedule. - {tenant}"
    if ftype == "reminder2":
        return f"Reminder: you are due in 2 hours for {professional} at {time_label}. - {tenant}"
    if ftype == "post":
        return f"Thanks for visiting! Please share feedback and book again. - {tenant}"
    if ftype == "recovery":
        return f"We're sorry to miss you. Would you like to rebook? - {tenant}"
    return f"Message from {tenant}"


def process_due_followups(max_batch: int = 200) -> None:
    """Send due follow-ups. No-op external sends when feature flags disabled."""
    col = _col()
    now = _now_utc()
    cur = col.find({"status": "scheduled", "run_at": {"$lte": now}}).sort("run_at", 1).limit(max_batch)
    for d in cur:
        _id = d.get("_id")
        tenant = d.get("tenant")
        ftype = d.get("type")
        to_phone = d.get("to_phone")
        to_email = d.get("to_email")
        payload = d.get("payload") or {}
        msg = _format_message(ftype, payload)
        sent_any = False
        error_text: Optional[str] = None
        try:
            if to_phone:
                # Enforce: only active customers should receive WhatsApp follow-ups
                try:
                    cust = customers_collection().find_one({"tenant": tenant, "phone": to_phone}, {"active": 1})
                    if cust is not None and not bool(cust.get("active", True)):
                        # Skip inactive recipient
                        col.update_one({"_id": _id}, {"$set": {"status": "skipped", "reason": "inactive_customer", "skipped_at": _now_utc()}, "$inc": {"attempts": 1}})
                        _broadcast_safe({
                            "type": "followup.skipped",
                            "tenant": tenant,
                            "followup_id": str(_id),
                            "f_type": ftype,
                            "reason": "inactive_customer",
                        })
                        continue
                except Exception:
                    # On lookup failure, proceed without blocking
                    pass
                try:
                    Messaging.send_whatsapp_text(to_phone, msg, tenant=tenant)
                    sent_any = True
                except Exception as e:  # pragma: no cover
                    error_text = str(e)
            if to_email:
                try:
                    Messaging.send_email(to_email, f"{ftype.title()} - {payload.get('tenant','')}", msg, tenant=tenant)
                    sent_any = True
                except Exception as e:  # pragma: no cover
                    error_text = (error_text or "") + f"; {e}"
        except Exception as e:  # pragma: no cover
            error_text = str(e)
        # Update status
        if sent_any:
            col.update_one({"_id": _id}, {"$set": {"status": "sent", "sent_at": _now_utc()}, "$inc": {"attempts": 1}})
            _broadcast_safe({
                "type": "followup.sent",
                "tenant": tenant,
                "followup_id": str(_id),
                "f_type": ftype,
            })
        else:
            col.update_one({"_id": _id}, {"$set": {"status": "failed", "last_error": error_text, "failed_at": _now_utc()}, "$inc": {"attempts": 1}})
            _broadcast_safe({
                "type": "followup.failed",
                "tenant": tenant,
                "followup_id": str(_id),
                "f_type": ftype,
                "error": error_text,
            })
