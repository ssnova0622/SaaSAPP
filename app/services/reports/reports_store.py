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
    storage = doc.get("storage") or ""
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
    storage = doc.get("storage")
    return S3Reports.get_presigned_url(storage, expires_seconds) if storage else None


def _report_date_key_in_window(date_key: str, window_start: date, window_end: date) -> bool:
    """True if stored report key (single YYYY-MM-DD or YYYY-MM-DD_to_YYYY-MM-DD) overlaps [window_start, window_end]."""
    if not date_key or not isinstance(date_key, str):
        return False
    if "_to_" in date_key:
        try:
            a, b = date_key.split("_to_", 1)
            d1 = date.fromisoformat(a.strip())
            d2 = date.fromisoformat(b.strip())
        except Exception:
            return False
        return not (d2 < window_start or d1 > window_end)
    try:
        d0 = date.fromisoformat(date_key.strip())
    except Exception:
        return False
    return window_start <= d0 <= window_end


def list_reports(tenant: str, page: int = 1, size: int = 50, from_date: Optional[date] = None,
                 to_date: Optional[date] = None) -> Dict[str, Any]:
    col = _reports_col()
    page = max(1, int(page or 1))
    size = max(1, min(200, int(size or 50)))
    skip = (page - 1) * size
    q: Dict[str, Any] = {"tenant": tenant}

    use_window = from_date is not None or to_date is not None
    if use_window:
        w_start = from_date or date(1970, 1, 1)
        w_end = to_date or date(2099, 12, 31)
        all_docs = list(col.find(q).sort("created_at", -1).limit(500))
        filtered = [d for d in all_docs if _report_date_key_in_window(str(d.get("date") or ""), w_start, w_end)]
        total = len(filtered)
        slice_docs = filtered[skip: skip + size]
        items = [_public_report(d) for d in slice_docs]
        return {"items": items, "total": total, "page": page, "size": size}

    total = col.count_documents(q)
    items = []
    for d in col.find(q).sort("created_at", -1).skip(skip).limit(size):
        items.append(_public_report(d))
    return {"items": items, "total": total, "page": page, "size": size}


def get_report_doc(tenant: str, date_str: str) -> Optional[Dict[str, Any]]:
    col = _reports_col()
    return col.find_one({"tenant": tenant, "date": date_str})


def ensure_report_downloadable(tenant: str, date_str: str) -> Optional[Dict[str, Any]]:
    """Return stored report row; if missing, generate PDF for that period and persist (on-demand download)."""
    doc = get_report_doc(tenant, date_str)
    if doc:
        return doc
    try:
        if "_to_" in date_str:
            a, b = date_str.split("_to_", 1)
            day = date.fromisoformat(a.strip())
            to_day = date.fromisoformat(b.strip())
        else:
            day = date.fromisoformat(date_str.strip())
            to_day = None
    except Exception:
        logger.warning("Invalid report date key tenant=%s key=%s", tenant, date_str)
        return None
    try:
        generate_and_store_report(tenant, day, to_day)
    except Exception as e:
        logger.exception("On-demand report generation failed tenant=%s key=%s: %s", tenant, date_str, e)
        return None
    return get_report_doc(tenant, date_str)


def resolve_report_download(doc: Dict[str, Any]):
    """
    Return a Response that either streams the PDF from local storage or proxies from S3.
    For S3, we fetch bytes server-side to avoid CORS and return a same-origin stream.
    """
    tenant = doc.get("tenant")
    date_str = doc.get("date") or ""
    storage = doc.get("storage") or ""

    # Use proper naming for range reports
    safe_tenant = str(tenant or "report").replace("/", "-")
    if "_to_" in date_str:
        filename = f"report-{safe_tenant}-{date_str.replace('_to_', '-to-')}.pdf"
    else:
        filename = f"daily-{safe_tenant}-{date_str}.pdf"

    # If using S3 and key looks like a key (not a file path), proxy bytes
    if S3Reports.enabled() and storage and not storage.startswith("/") and not storage.startswith("file://"):
        try:
            data = S3Reports.get_bytes(storage)
            if data is None:
                return None
            return StreamingResponse(
                iter([data]),
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    return None


def deliver_report_links(tenant: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deliver the daily report to the tenant owner: email with PDF attachment when possible;
    WhatsApp with PDF document when a public HTTPS URL exists (e.g. presigned S3), otherwise
    text with link/path. Uses owner_email and owner_phone; dev NO-OP when channels disabled.
    """

    tenant_doc = Storage.get_tenant(tenant) or {}
    owner_email = (tenant_doc.get("owner_email") or "").strip()
    owner_phone = (tenant_doc.get("owner_phone") or "").strip()
    business_name = (tenant_doc.get("business_name") or tenant_doc.get("_id") or tenant)
    delivery = str(tenant_doc.get("invoice_delivery") or "both").strip().lower()
    if delivery in ("email", "e-mail", "mail"):
        send_email, send_whatsapp = True, False
    elif delivery in ("whatsapp", "wa"):
        send_email, send_whatsapp = False, True
    elif delivery == "both" or not delivery:
        send_email = send_whatsapp = True
    else:
        send_email = send_whatsapp = True

    url = get_presigned_or_file_url(doc) or doc.get("storage")
    date_str = doc.get("date", "")
    sent_via: List[str] = []

    # Email with PDF attachment when possible
    if owner_email and send_email:
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

    # WhatsApp: PDF via public URL (Twilio/Meta fetch the file); else text + link
    if owner_phone and send_whatsapp:
        summary = (
            f"📊 Daily Report – {business_name} – {date_str}\n\n"
            f"Open your report (PDF): {url}"
        )
        wa_caption = f"Daily report – {business_name} – {date_str}"
        presigned = get_presigned_or_file_url(doc)
        public_pdf_url = (
            presigned if presigned and presigned.startswith(("http://", "https://")) else None
        )
        pdf_name = f"daily-report-{tenant}-{date_str}.pdf"
        try:
            if public_pdf_url:
                try:
                    Messaging.send_whatsapp_document(
                        owner_phone,
                        public_pdf_url,
                        caption=wa_caption,
                        filename=pdf_name,
                        tenant=tenant,
                    )
                except Exception as doc_err:
                    logger.warning(
                        "Report WhatsApp document send failed for %s, falling back to text: %s",
                        tenant,
                        doc_err,
                    )
                    Messaging.send_whatsapp_text(owner_phone, summary, tenant=tenant)
            else:
                logger.info(
                    "Report WhatsApp: no public PDF URL for %s (enable S3 or use presigned URL); sending link text only",
                    tenant,
                )
                Messaging.send_whatsapp_text(owner_phone, summary, tenant=tenant)
            sent_via.append("whatsapp")
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
