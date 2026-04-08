from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
import copy
import logging
import time

from pymongo import ASCENDING
from pymongo.collection import Collection

from app.services.db import get_db, customers_collection
from app.services.messaging.messaging import Messaging
from app.helpers.phone_util import PhoneUtil
from app.services.core.tenant_service import TenantService

from .whatsapp_delivery import append_cta_urls_to_message_text, append_offer_code_line, send_promotion_whatsapp
from app.core.realtime import get_notifier
from settings import env

logger = logging.getLogger(__name__)


def _broadcast_safe(event: Dict[str, Any]) -> None:
    """Send a WebSocket broadcast without requiring an async context.
    Swallows exceptions in non‑WS contexts (e.g., during tests or CLI calls).
    """
    try:
        import anyio

        async def _send():
            await get_notifier().broadcast(event)

        anyio.run(_send)
    except Exception:
        # Log at debug to avoid noise in development when no WS hub is attached
        logger.debug("WS broadcast skipped: %s", event.get("type"))


def _promotions_col() -> Collection:
    db = get_db()
    col = db.get_collection("promotions")
    # Ensure indexes (idempotent)
    col.create_index([("tenant", ASCENDING)])
    col.create_index([("tenant", ASCENDING), ("status", ASCENDING)])
    col.create_index([("tenant", ASCENDING), ("schedule_at", ASCENDING)])
    return col


def _promotion_logs_col() -> Collection:
    from app.services.core.promotions.helpers.db_utils import promotion_logs_col

    return promotion_logs_col()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def create_promotion(
    tenant: str,
    name: str,
    channel: str,
    message: str,
    html_message: Optional[str],
    media_url: Optional[str],
    audience: Dict[str, Any],
    schedule_at: Optional[datetime] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    interactive_type: Optional[str] = None,
    buttons: Optional[List[Dict[str, Any]]] = None,
    list_sections: Optional[List[Dict[str, Any]]] = None,
    cta_url: Optional[str] = None,
    cta_display_text: Optional[str] = None,
    cta_footer: Optional[str] = None,
    cta_entries: Optional[List[Dict[str, Any]]] = None,
    cta_append_urls_to_body: Optional[bool] = None,
    offer_code: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    col = _promotions_col()
    entries = list(cta_entries) if cta_entries else []
    if entries:
        fe = entries[0]
        if (fe.get("url") or "").strip():
            cta_url = fe["url"].strip()
            cta_display_text = (fe.get("display_text") or cta_display_text or "Open").strip()
    entries_out: Optional[List[Dict[str, Any]]] = entries if entries else None
    doc = {
        "tenant": tenant,
        "name": name,
        "channel": channel or "both",
        "message": message or "",
        "html_message": html_message,
        "media_url": media_url,
        "attachments": attachments,
        "interactive_type": interactive_type,
        "buttons": buttons,
        "list_sections": list_sections,
        "cta_url": cta_url,
        "cta_display_text": cta_display_text,
        "cta_footer": cta_footer,
        "cta_entries": entries_out,
        "cta_append_urls_to_body": True if cta_append_urls_to_body is None else bool(cta_append_urls_to_body),
        "offer_code": offer_code,
        "audience": audience or {"type": "all"},
        "schedule_at": schedule_at,
        "created_at": _now_utc(),
        "created_by": user_id,
        "updated_at": _now_utc(),
        "updated_by": user_id,
        "status": "draft" if schedule_at is None else "scheduled",
    }
    res = col.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _public_promotion(doc)


def list_promotions(tenant: str) -> List[Dict[str, Any]]:
    col = _promotions_col()
    out: List[Dict[str, Any]] = []
    for d in col.find({"tenant": tenant}).sort("created_at", -1):
        out.append(_public_promotion(d))
    return out


def get_promotion(tenant: str, prom_id: str) -> Optional[Dict[str, Any]]:
    from bson import ObjectId
    col = _promotions_col()
    try:
        _id = ObjectId(prom_id)
    except Exception:
        return None
    d = col.find_one({"_id": _id, "tenant": tenant})
    return _public_promotion(d) if d else None


def update_promotion(tenant: str, prom_id: str, updates: Dict[str, Any], user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    from bson import ObjectId
    col = _promotions_col()
    try:
        _id = ObjectId(prom_id)
    except Exception:
        return None
    doc = col.find_one({"_id": _id, "tenant": tenant})
    if not doc:
        return None
    if doc.get("status") in ("running", "completed"):
        raise ValueError("Cannot update a promotion that has started")
    allowed = {
        "name", "channel", "message", "html_message", "media_url", "attachments", "audience",
        "schedule_at", "status", "interactive_type", "buttons", "list_sections",
        "cta_url", "cta_display_text", "cta_footer", "offer_code",
        "cta_entries", "cta_append_urls_to_body",
    }
    payload = {k: v for k, v in (updates or {}).items() if k in allowed}
    payload["updated_at"] = _now_utc()
    payload["updated_by"] = user_id
    if payload.get("cta_entries"):
        fe = payload["cta_entries"][0]
        if isinstance(fe, dict) and (fe.get("url") or "").strip():
            payload["cta_url"] = fe["url"].strip()
            payload["cta_display_text"] = (fe.get("display_text") or payload.get("cta_display_text") or "Open").strip()
    col.update_one({"_id": _id}, {"$set": payload})
    d = col.find_one({"_id": _id})
    return _public_promotion(d) if d else None


def delete_promotion(tenant: str, prom_id: str) -> bool:
    from bson import ObjectId
    col = _promotions_col()
    try:
        _id = ObjectId(prom_id)
    except Exception:
        return False
    res = col.delete_one({"_id": _id, "tenant": tenant})
    return res.deleted_count > 0


def resend_promotion_as_new(
    tenant: str,
    source_prom_id: str,
    *,
    audience_override: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Clone a completed promotion into a new row and send the clone. The source document is not modified."""
    from bson import ObjectId

    col = _promotions_col()
    try:
        sid = ObjectId(source_prom_id)
    except Exception:
        raise ValueError("Invalid promotion id")

    src = col.find_one({"_id": sid, "tenant": tenant})
    if not src:
        raise ValueError("Promotion not found")
    if src.get("status") != "completed":
        raise ValueError("Resend creates a new promotion only when the original has completed")

    now = _now_utc()
    base_name = (src.get("name") or "Promotion").strip()
    name_out = f"{base_name} (resend)" if base_name else "Promotion (resend)"

    eff_audience: Dict[str, Any]
    if audience_override is not None:
        eff_audience = copy.deepcopy(audience_override)
    else:
        eff_audience = copy.deepcopy(src.get("audience") or {"type": "all"})

    new_doc: Dict[str, Any] = {
        "tenant": tenant,
        "name": name_out,
        "channel": src.get("channel") or "both",
        "message": src.get("message") or "",
        "html_message": src.get("html_message"),
        "media_url": src.get("media_url"),
        "attachments": copy.deepcopy(src.get("attachments")),
        "interactive_type": src.get("interactive_type"),
        "buttons": copy.deepcopy(src.get("buttons")),
        "list_sections": copy.deepcopy(src.get("list_sections")),
        "cta_url": src.get("cta_url"),
        "cta_display_text": src.get("cta_display_text"),
        "cta_footer": src.get("cta_footer"),
        "cta_entries": copy.deepcopy(src.get("cta_entries")),
        "cta_append_urls_to_body": True if src.get("cta_append_urls_to_body") is None else bool(src.get("cta_append_urls_to_body")),
        "offer_code": src.get("offer_code"),
        "audience": eff_audience,
        "created_at": now,
        "created_by": user_id,
        "updated_at": now,
        "updated_by": user_id,
        "status": "draft",
        "resend_of": sid,
    }

    ins = col.insert_one(new_doc)
    new_id_str = str(ins.inserted_id)

    out = send_promotion_now(tenant, new_id_str)
    out["source_promotion_id"] = source_prom_id
    return out


def send_promotion_now(
    tenant: str,
    prom_id: str,
    *,
    audience_override: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Resolve audience and send via configured channels. Logs per-recipient outcome per send batch.

    Promotions in ``completed`` status are left unchanged (returns current stats). Use
    :func:`resend_promotion_as_new` to send again. Optional ``audience_override`` applies to this
    send only without updating the stored document.
    """
    from bson import ObjectId
    from pymongo.errors import DuplicateKeyError

    promos = _promotions_col()
    logs = _promotion_logs_col()

    try:
        _id = ObjectId(prom_id)
    except Exception:
        raise ValueError("Invalid promotion id")

    promo = promos.find_one({"_id": _id, "tenant": tenant})
    if not promo:
        raise ValueError("Promotion not found")

    st = promo.get("status")
    if st == "running":
        stats = promo.get("stats") or {"total": 0, "sent": 0, "failed": 0}
        return {
            "id": str(_id),
            "tenant": tenant,
            "status": st,
            "total": stats.get("total", 0),
            "sent": stats.get("sent", 0),
            "failed": stats.get("failed", 0),
        }
    if st == "completed":
        stats = promo.get("stats") or {"total": 0, "sent": 0, "failed": 0}
        return {
            "id": str(_id),
            "tenant": tenant,
            "status": st,
            "total": stats.get("total", 0),
            "sent": stats.get("sent", 0),
            "failed": stats.get("failed", 0),
        }

    effective_audience = audience_override if audience_override is not None else (promo.get("audience") or {})
    recipients = _resolve_audience(tenant, effective_audience)
    total = len(recipients)
    send_batch_id = ObjectId()

    # Mark running & store total upfront
    promos.update_one(
        {"_id": _id},
        {"$set": {"status": "running", "started_at": _now_utc(), "stats": {"total": total, "sent": 0, "failed": 0}}},
    )

    # WS: started
    _broadcast_safe({
        "type": "promotion.started",
        "tenant": tenant,
        "promotion_id": str(_id),
        "total": total,
    })

    batch_size = env.int("PROMO_BATCH_SIZE", 50)
    rps = max(1, env.int("PROMO_RPS", 20))
    delay = 1.0 / float(rps)

    sent = 0
    failed = 0
    processed = 0

    def _progress():
        _broadcast_safe({
            "type": "promotion.progress",
            "tenant": tenant,
            "promotion_id": str(_id),
            "total": total,
            "sent": sent,
            "failed": failed,
            "processed": processed,
        })

    channel = (promo.get("channel") or "both").lower()
    message = promo.get("message", "")
    html_message = promo.get("html_message")
    interactive_type = promo.get("interactive_type")
    buttons = promo.get("buttons") or []
    list_sections = promo.get("list_sections") or []
    attachments = promo.get("attachments")

    # If interactive buttons/lists have URLs, we should append them to the message for non-interactive fallback
    # or even for interactive providers if they don't support CTA URL buttons.
    message_with_links = message
    it = (interactive_type or "").lower()
    if it == "button" and any(b.get("url") for b in buttons):
        links = [f"{b['title']}: {b['url']}" for b in buttons if b.get("url")]
        message_with_links += "\n\n" + "\n".join(links)
    elif it == "list" and any(r.get("url") for s in list_sections for r in s.get("rows", [])):
        links = [f"{r['title']}: {r['url']}" for s in list_sections for r in s.get("rows", []) if r.get("url")]
        message_with_links += "\n\n" + "\n".join(links)

    message_for_whatsapp = append_cta_urls_to_message_text(message_with_links, promo)
    email_body = append_offer_code_line(
        append_cta_urls_to_message_text(message_with_links, promo, force=True),
        promo,
    )

    # Preload customer active map for phones in recipients to minimize per-send lookups
    phones = [(PhoneUtil.promo_normalize(r.get("phone")) if r.get("phone") else None) for r in recipients]
    phones = [p for p in phones if p]
    active_map: Dict[str, bool] = {}
    if phones:
        col_cust = customers_collection()
        dial = TenantService._get_tenant_country_code(tenant) or PhoneUtil.DEFAULT_DIAL_DIGITS
        seen_ph: set[str] = set()
        for ph in phones:
            if not ph or ph in seen_ph:
                continue
            seen_ph.add(ph)
            doc = col_cust.find_one(PhoneUtil.customer_match_query(tenant, ph, dial), {"active": 1})
            if doc:
                active_map[ph] = bool(doc.get("active", True))

    for idx, r in enumerate(recipients, start=1):
        phone = r.get("phone")
        email = r.get("email")
        # WhatsApp
        if channel in ("whatsapp", "both") and phone:
            to_val = PhoneUtil.promo_normalize(phone)
            # Enforce: only active customers receive WhatsApp
            if active_map.get(to_val, True) is False:
                try:
                    logs.insert_one({
                        "promotion_id": _id,
                        "tenant": tenant,
                        "to": to_val,
                        "channel": "whatsapp",
                        "status": "skipped",
                        "reason": "inactive_customer",
                        "sent_at": _now_utc(),
                        "send_batch_id": send_batch_id,
                    })
                except DuplicateKeyError:
                    pass
                processed += 1
                # Throttle and progress handling below
                if (idx % batch_size) == 0 or idx == total:
                    _progress()
                time.sleep(delay)
                continue
            try:
                promo_wa = {
                    "interactive_type": interactive_type,
                    "attachments": attachments or [],
                    "buttons": buttons,
                    "list_sections": list_sections,
                    "cta_url": promo.get("cta_url"),
                    "cta_display_text": promo.get("cta_display_text"),
                    "cta_footer": promo.get("cta_footer"),
                    "cta_entries": promo.get("cta_entries"),
                    "cta_append_urls_to_body": promo.get("cta_append_urls_to_body"),
                    "offer_code": promo.get("offer_code"),
                }
                send_promotion_whatsapp(tenant, to_val, promo_wa, message_for_whatsapp)
                try:
                    logs.insert_one({
                        "promotion_id": _id,
                        "tenant": tenant,
                        "to": to_val,
                        "channel": "whatsapp",
                        "status": "sent",
                        "sent_at": _now_utc(),
                        "send_batch_id": send_batch_id,
                    })
                    sent += 1
                except DuplicateKeyError:
                    pass
            except Exception as e:  # pragma: no cover
                failed += 1
                try:
                    logs.insert_one({
                        "promotion_id": _id,
                        "tenant": tenant,
                        "to": to_val,
                        "channel": "whatsapp",
                        "status": "failed",
                        "error": str(e),
                        "sent_at": _now_utc(),
                        "send_batch_id": send_batch_id,
                    })
                except Exception:
                    pass
        # Email
        if channel in ("email", "both") and email:
            to_email = email
            try:
                Messaging.send_email(to_email, promo.get("name", "Promotion"), email_body, html_message, tenant=tenant)
                try:
                    logs.insert_one({
                        "promotion_id": _id,
                        "tenant": tenant,
                        "to": to_email,
                        "channel": "email",
                        "status": "sent",
                        "sent_at": _now_utc(),
                        "send_batch_id": send_batch_id,
                    })
                    sent += 1
                except DuplicateKeyError:
                    pass
            except Exception as e:  # pragma: no cover
                failed += 1
                try:
                    logs.insert_one({
                        "promotion_id": _id,
                        "tenant": tenant,
                        "to": to_email,
                        "channel": "email",
                        "status": "failed",
                        "error": str(e),
                        "sent_at": _now_utc(),
                        "send_batch_id": send_batch_id,
                    })
                except Exception:
                    pass

        processed += 1
        # Throttle per RPS
        time.sleep(delay)
        # Emit progress every batch_size or at end
        if (idx % batch_size) == 0 or idx == total:
            _progress()

    status = "completed"
    promos.update_one({"_id": _id}, {"$set": {"status": status, "completed_at": _now_utc(), "stats": {"total": total, "sent": sent, "failed": failed}}})

    # WS: completed
    _broadcast_safe({
        "type": "promotion.completed",
        "tenant": tenant,
        "promotion_id": str(_id),
        "total": total,
        "sent": sent,
        "failed": failed,
    })

    return {
        "id": str(_id),
        "tenant": tenant,
        "status": status,
        "total": total,
        "sent": sent,
        "failed": failed,
    }


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
    from bson import ObjectId
    logs = _promotion_logs_col()
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
    total = logs.count_documents(q)
    page = max(1, int(page or 1))
    size = max(1, min(200, int(size or 50)))
    skip = (page - 1) * size
    items: List[Dict[str, Any]] = []
    for d in logs.find(q).sort("sent_at", -1).skip(skip).limit(size):
        d["id"] = str(d.pop("_id"))
        d["promotion_id"] = str(d.get("promotion_id"))
        sb = d.get("send_batch_id")
        if sb is not None:
            d["send_batch_id"] = str(sb)
        items.append(d)
    return {"items": items, "total": total, "page": page, "size": size}


def process_pending_promotions() -> None:
    """Called by scheduler to dispatch scheduled promotions whose time has arrived."""
    col = _promotions_col()
    now = _now_utc()
    for p in col.find({"status": "scheduled", "schedule_at": {"$lte": now}}).sort("schedule_at", 1):
        prom_id = str(p["_id"])  # type: ignore[index]
        try:
            logger.info("Dispatching scheduled promotion %s for tenant %s", prom_id, p.get("tenant"))
            send_promotion_now(p.get("tenant"), prom_id)
        except Exception as e:  # pragma: no cover
            logger.error("Failed to dispatch promotion %s: %s", prom_id, e)


def _public_promotion(d: Dict[str, Any]) -> Dict[str, Any]:
    if not d:
        return {}
    out = dict(d)
    out["id"] = str(out.pop("_id"))
    ro = out.get("resend_of")
    if ro is not None:
        out["resend_of"] = str(ro)
    return out


def _resolve_audience(tenant: str, audience: Dict[str, Any]) -> List[Dict[str, Any]]:
    from app.services.core import retention_service as retention_svc
    col = customers_collection()
    typ = (audience.get("type") or "all").lower()
    recipients: List[Dict[str, Any]] = []
    dial = TenantService._get_tenant_country_code(tenant) or PhoneUtil.DEFAULT_DIAL_DIGITS
    if typ == "all":
        # Only active customers receive messages
        for c in col.find({"tenant": tenant, "active": True}, {"_id": 0}).sort("name", 1):
            recipients.append(
                {
                    "phone": PhoneUtil.export_e164(c, dial) or c.get("phone"),
                    "email": c.get("email"),
                    "name": c.get("name"),
                }
            )
    elif typ == "tags":
        tags = [t.strip() for t in (audience.get("tags") or []) if isinstance(t, str) and t.strip()]
        if tags:
            q = {"tenant": tenant, "tags": {"$in": tags}, "active": True}
            for c in col.find(q, {"_id": 0}).sort("name", 1):
                recipients.append(
                    {
                        "phone": PhoneUtil.export_e164(c, dial) or c.get("phone"),
                        "email": c.get("email"),
                        "name": c.get("name"),
                    }
                )
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
            recipients.append({"phone": PhoneUtil.promo_normalize(p), "email": None, "name": None})
        for e in emails:
            recipients.append({"phone": None, "email": e, "name": None})
    # Dedupe by phone+email tuple
    seen: set[Tuple[Optional[str], Optional[str]]] = set()
    uniq: List[Dict[str, Any]] = []
    for r in recipients:
        key = (r.get("phone"), r.get("email"))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    return uniq
