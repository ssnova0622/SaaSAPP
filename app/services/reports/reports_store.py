from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Dict, Any, List, Optional
import os
import logging

from pymongo import ASCENDING

from app.helpers.constants import DEFAULT_TIMEZONE

logger = logging.getLogger(__name__)

from app.services.db import get_db
from app.services.s3.storage_s3 import S3Reports
from app.services.reports.reports import build_daily_report
from app.services.storage_mongo import Storage
from app.services.messaging.messaging import Messaging
from settings import env
from fastapi.responses import StreamingResponse


def get_report_pdf_bytes(doc: Dict[str, Any]) -> Optional[bytes]:
    """Return PDF bytes for a stored report (from S3 or local file). Used for email attachment."""
    storage = doc.get("../storage") or ""
    if not storage:
        return None
    if S3Reports.enabled() and storage and not storage.startswith("/") and not storage.startswith("file://"):
        return S3Reports.get_bytes(storage)
    path = storage
    if path.startswith("file://"):
        path = path[len("file://"):]
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    return None


_DEF_TZ = env.str("DEFAULT_TZ", DEFAULT_TIMEZONE)


def _reports_col():
    db = get_db()
    col = db.get_collection("reports")
    # indexes
    col.create_index([("tenant", ASCENDING), ("date", ASCENDING)], unique=True)
    col.create_index([("tenant", ASCENDING), ("created_at", ASCENDING)])
    return col


def generate_and_store_report(tenant: str, day: date, to_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Build the daily or range report PDF, upload to S3 (or save locally) and persist metadata.
    Returns the stored report document (public shape).
    """
    # Build data snapshot from DB for the given day/range and tenant
    snapshot = Storage.get_report_snapshot(tenant, day, to_date)
    fname, pdf_bytes = build_daily_report(tenant, day, snapshot, to_date)
    
    date_str = day.isoformat()
    if to_date and to_date != day:
        date_str = f"{day.isoformat()}_to_{to_date.isoformat()}"
        
    storage_ref = S3Reports.upload_report(tenant, date_str, pdf_bytes)
    doc = {
        "tenant": tenant,
        "date": date_str,
        "storage": storage_ref,
        "url_type": "s3" if S3Reports.enabled() else "file",
        "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
        "sent_via": [],
        "status": "generated",
    }
    col = _reports_col()
    col.update_one({"tenant": tenant, "date": date_str}, {"$set": doc}, upsert=True)
    saved = col.find_one({"tenant": tenant, "date": date_str})
    return _public_report(saved)


def get_presigned_or_file_url(doc: Dict[str, Any], expires_seconds: int = 86400) -> Optional[str]:
    storage = doc.get("../storage")
    return S3Reports.get_presigned_url(storage, expires_seconds) if storage else None


def list_reports(tenant: str, page: int = 1, size: int = 50, from_date: Optional[date] = None, to_date: Optional[date] = None) -> Dict[str, Any]:
    col = _reports_col()
    page = max(1, int(page or 1))
    size = max(1, min(200, int(size or 50)))
    skip = (page - 1) * size
    q: Dict[str, Any] = {"tenant": tenant}
    if from_date and to_date:
        q["date"] = {"$gte": from_date.isoformat(), "$lte": to_date.isoformat()}
    elif from_date:
        q["date"] = {"$gte": from_date.isoformat()}
    elif to_date:
        q["date"] = {"$lte": to_date.isoformat()}
        
    total = col.count_documents(q)
    items: List[Dict[str, Any]] = []
    for d in col.find(q).sort("date", -1).skip(skip).limit(size):
        items.append(_public_report(d))
    return {"items": items, "total": total, "page": page, "size": size}


def get_report_doc(tenant: str, date_str: str) -> Optional[Dict[str, Any]]:
    col = _reports_col()
    return col.find_one({"tenant": tenant, "date": date_str})


def resolve_report_download(doc: Dict[str, Any]):
    """
    Return a Response that either streams the PDF from local storage or proxies from S3.
    For S3, we fetch bytes server-side to avoid CORS and return a same-origin stream.
    """
    tenant = doc.get("tenant")
    date_str = doc.get("date")
    storage = doc.get("../storage") or ""
    
    # Use proper naming for range reports
    if "_to_" in date_str:
        filename = f"report-{tenant}-{date_str.replace('_to_', '-to-')}.pdf"
    else:
        filename = f"daily-{tenant}-{date_str}.pdf"

    # If using S3 and key looks like a key (not a file path), proxy bytes
    if S3Reports.enabled() and storage and not storage.startswith("/") and not storage.startswith("file://"):
        try:
            data = S3Reports.get_bytes(storage)
            if data is None:
                return None
            return StreamingResponse(
                iter([data]),
                media_type="application/pdf",
                headers={"Content-Disposition": f"inline; filename={filename}"},
            )
        except Exception:
            return None

    # Local file path
    path = storage
    if storage.startswith("file://"):
        path = storage[len("file://"):]
    if path and os.path.exists(path):
        def file_iterator(pth: str, chunk_size: int = 8192):
            with open(pth, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

        return StreamingResponse(
            file_iterator(path),
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename={filename}"},
        )
    return None


def deliver_report_links(tenant: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deliver the daily report via Email (with PDF attachment) and WhatsApp (link + short summary) to the tenant.
    Uses owner_email and owner_phone from tenant; in dev (SMTP/Twilio disabled), this is a NO-OP with logs.
    """

    tenant_doc = Storage.get_tenant(tenant) or {}
    owner_email = (tenant_doc.get("owner_email") or "").strip()
    owner_phone = (tenant_doc.get("owner_phone") or "").strip()
    business_name = (tenant_doc.get("business_name") or tenant_doc.get("_id") or tenant)

    url = get_presigned_or_file_url(doc) or doc.get("../storage")
    date_str = doc.get("date", "")
    sent_via: List[str] = []

    # Email with PDF attachment when possible
    if owner_email:
        pdf_bytes = get_report_pdf_bytes(doc)
        subject = f"Daily Report – {business_name} – {date_str}"
        text_body = (
            f"Your daily report for {business_name} ({date_str}) is attached.\n\n"
            f"You can also open the report here: {url}"
        )
        attachments = None
        if pdf_bytes:
            fname = f"daily-report-{tenant}-{date_str}.pdf"
            attachments = [(fname, pdf_bytes, "application/pdf")]
        try:
            Messaging.send_email(
                owner_email,
                subject=subject,
                text_body=text_body,
                tenant=tenant,
                attachments=attachments,
            )
            sent_via.append("email")
        except Exception as e:
            logger.warning("Report email delivery failed for %s: %s", tenant, e)

    # WhatsApp: link + one-line summary so tenant can open PDF
    if owner_phone:
        summary = (
            f"📊 Daily Report – {business_name} – {date_str}\n\n"
            f"Open your report (PDF): {url}"
        )
        try:
            Messaging.send_whatsapp_text(owner_phone, summary, tenant=tenant)
            sent_via.append("../whatsapp")
        except Exception as e:
            logger.warning("Report WhatsApp delivery failed for %s: %s", tenant, e)

    col = _reports_col()
    col.update_one(
        {"tenant": tenant, "date": doc.get("date")},
        {"$set": {"sent_via": sent_via, "status": "sent", "sent_at": datetime.now(timezone.utc).replace(tzinfo=None)}},
    )
    new_doc = col.find_one({"tenant": tenant, "date": doc.get("date")})
    return _public_report(new_doc)


def _public_report(d: Dict[str, Any] | None) -> Dict[str, Any]:
    if not d:
        return {}
    out = dict(d)
    out.pop("_id", None)
    # Attach a short-lived URL for convenience when listing
    out["url"] = get_presigned_or_file_url(out) or out.get("storage")
    return out
