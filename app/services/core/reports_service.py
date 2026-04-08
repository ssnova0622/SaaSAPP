# app/services/core/reports_service.py
from __future__ import annotations

# ============================================================
# Imports
# ============================================================

from datetime import date, datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import os

from fastapi.responses import StreamingResponse

from app.helpers.constants import DEFAULT_TIMEZONE
from app.services.core.messaging_service import Messaging
from app.services.s3.storage import StorageService
from app.services.core.tenant_service import TenantService

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from io import BytesIO

from app.services.salon.appointments.appointment_service import AppointmentService
from app.helpers.date_utils import format_date_for_display
from settings import env

DEFAULT_TZ = env.str("DEFAULT_TZ", DEFAULT_TIMEZONE)

# ============================================================
# DB Helpers
# ============================================================

from app.repositories.report_repository import ReportRepository

report_repo = ReportRepository()


def _reports_col():
    col = report_repo.get_collection()
    from pymongo import ASCENDING
    col.create_index([("tenant", ASCENDING), ("date", ASCENDING)], unique=True)
    col.create_index([("tenant", ASCENDING), ("created_at", ASCENDING)])
    return col


# ============================================================
# Pagination Helpers
# ============================================================

def _paginate(page: int, size: int, max_size: int = 200) -> Tuple[int, int, int]:
    page = max(1, int(page or 1))
    size = max(1, min(int(size or 50), max_size))
    skip = (page - 1) * size
    return page, size, skip


# ============================================================
# Filename & Date Helpers
# ============================================================

def _build_date_str(day: date, to_date: Optional[date]) -> str:
    if to_date and to_date != day:
        return f"{day.isoformat()}_to_{to_date.isoformat()}"
    return day.isoformat()


def _build_filename(tenant: str, date_str: str) -> str:
    if "_to_" in date_str:
        return f"report-{tenant}-{date_str.replace('_to_', '-to-')}.pdf"
    return f"daily-{tenant}-{date_str}.pdf"


# ============================================================
# PDF Builder Helpers
# ============================================================

def _create_pdf_doc(title: str):
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
        title=title,
    )
    return doc, buf


def _table(data, col_widths=None):
    table = Table(data, repeatRows=1, colWidths=col_widths)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.aliceblue]),
            ]
        )
    )
    return table


# ============================================================
# PDF Sections
# ============================================================

def _section_header(tenant: str, date_label: str, tz: str, title_text: str):
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"<b>{title_text}</b>", styles["Title"]),
        Spacer(1, 12),
        Paragraph(
            f"Tenant: <b>{tenant}</b><br/>Date: <b>{date_label}</b><br/>Timezone: <b>{tz}</b>",
            styles["Normal"],
        ),
        Spacer(1, 18),
    ]
    return story


def _section_appointments(rows: List[Dict[str, Any]]):
    styles = getSampleStyleSheet()
    story = [
        Paragraph("<b>Appointments / Services</b>", styles["Heading3"]),
        Spacer(1, 6),
    ]

    data = [["Time", "Professional", "Customer", "Price", "Status"]]
    if rows:
        for r in rows:
            data.append([
                str(r.get("time") or ""),
                str(r.get("professional") or ""),
                str(r.get("customer") or ""),
                f"{float(r.get('price') or 0):.2f}",
                str(r.get("status") or ""),
            ])
    else:
        data.append(["—", "—", "No appointments", "0.00", "—"])

    story.append(_table(data, col_widths=[60, 100, 150, 60, 100]))
    story.append(Spacer(1, 18))
    return story


def _section_sales(rows: List[Dict[str, Any]]):
    styles = getSampleStyleSheet()
    story = [
        Paragraph("<b>Product Sales</b>", styles["Heading3"]),
        Spacer(1, 6),
    ]

    data = [["Product", "Qty", "Amount", "Profit", "Customer", "Status"]]
    if rows:
        for r in rows:
            data.append([
                str(r.get("product") or ""),
                str(r.get("qty") or "0"),
                f"{float(r.get('total') or 0):.2f}",
                f"{float(r.get('profit') or 0):.2f}",
                str(r.get("customer") or ""),
                str(r.get("status") or ""),
            ])
    else:
        data.append(["—", "0", "0.00", "0.00", "No sales", "—"])

    story.append(_table(data, col_widths=[150, 40, 70, 70, 100, 70]))
    story.append(Spacer(1, 18))
    return story


def _section_totals(totals: Dict[str, Any]):
    styles = getSampleStyleSheet()

    appts = int(totals.get("appointments") or 0)
    canc = int(totals.get("cancellations") or 0)
    revenue = float(totals.get("revenue") or 0)

    text = f"Totals — Appointments: {appts} • Cancellations: {canc} • Revenue: {revenue:.2f}"

    if totals.get("orders_count"):
        text += (
            f"<br/>Store — Orders: {totals['orders_count']} • "
            f"Units: {totals.get('units_sold', 0)} • "
            f"Revenue: {float(totals.get('store_revenue', 0)):.2f}"
        )

    if totals.get("status_counts"):
        parts = [f"{k.capitalize()}: {v}" for k, v in totals["status_counts"].items() if v > 0]
        if parts:
            text += "<br/>Status Breakdown: " + " • ".join(parts)

    story = [
        Paragraph(text, styles["Normal"]),
        Spacer(1, 6),
        Paragraph(f"Generated at: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", styles["Italic"]),
    ]
    return story


# ============================================================
# PDF Builder
# ============================================================

def build_daily_report(
        tenant: str,
        day: date,
        snapshot: Dict[str, Any],
        to_date: Optional[date] = None,
) -> Tuple[str, bytes]:
    settings = TenantService.get_tenant_settings(tenant)
    day_fmt = format_date_for_display(day, settings)
    if to_date and to_date != day:
        to_fmt = format_date_for_display(to_date, settings)
        date_label = f"{day_fmt} to {to_fmt}"
    else:
        date_label = day_fmt

    title = f"Report - {tenant} - {date_label}"
    doc, buf = _create_pdf_doc(title)

    tz = str(snapshot.get("tz") or DEFAULT_TZ)
    modules = snapshot.get("modules") or []
    is_store = "store" in modules
    is_service = ("salon" in modules) or ("clinic" in modules) or (not modules)

    story = []
    story += _section_header(tenant, date_label, tz, "Daily Report" if not to_date else "Range Report")

    if is_service:
        story += _section_appointments(snapshot.get("rows") or [])

    if is_store:
        story += _section_sales(snapshot.get("order_rows") or [])

    story += _section_totals(snapshot.get("totals") or {})

    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()

    filename = (
        f"report-{tenant}-{day.isoformat()}-to-{to_date.isoformat()}.pdf"
        if to_date and to_date != day
        else f"daily-{tenant}-{day.isoformat()}.pdf"
    )

    return filename, pdf_bytes


# ============================================================
# Report Generation & Storage
# ============================================================

def generate_and_store_report(tenant: str, day: date, to_date: Optional[date] = None) -> Dict[str, Any]:
    snapshot = AppointmentService.get_report_snapshot(tenant, day, to_date)
    filename, pdf_bytes = build_daily_report(tenant, day, snapshot, to_date)

    date_str = _build_date_str(day, to_date)
    storage_ref = StorageService.upload_report(tenant, date_str, pdf_bytes)

    doc = {
        "tenant": tenant,
        "date": date_str,
        "storage": storage_ref,
        "url_type": "s3" if StorageService.is_s3() else "file",
        "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
        "sent_via": [],
        "status": "generated",
    }

    col = _reports_col()
    col.update_one({"tenant": tenant, "date": date_str}, {"$set": doc}, upsert=True)
    saved = col.find_one({"tenant": tenant, "date": date_str})
    return _public_report(saved)


# ============================================================
# URL Helpers
# ============================================================

def get_presigned_or_file_url(doc: Dict[str, Any], expires_seconds: int = 86400) -> Optional[str]:
    storage = doc.get("storage")
    if not storage:
        return None
    return StorageService.get_report_url(storage, expires_seconds)


# ============================================================
# Listing & Retrieval
# ============================================================

def list_reports(
        tenant: str,
        page: int = 1,
        size: int = 50,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
) -> Dict[str, Any]:
    col = report_repo.get_collection()
    page, size, skip = _paginate(page, size)

    q: Dict[str, Any] = {"tenant": tenant}
    if from_date and to_date:
        q["date"] = {"$gte": from_date.isoformat(), "$lte": to_date.isoformat()}
    elif from_date:
        q["date"] = {"$gte": from_date.isoformat()}
    elif to_date:
        q["date"] = {"$lte": to_date.isoformat()}

    total = report_repo.count_documents(q)
    items = [
        _public_report(d)
        for d in col.find(q).sort("date", -1).skip(skip).limit(size)
    ]

    return {"items": items, "total": total, "page": page, "size": size}


def get_report_doc(tenant: str, date_str: str) -> Optional[Dict[str, Any]]:
    return report_repo.find_one_raw({"tenant": tenant, "date": date_str})


# ============================================================
# Download Resolution
# ============================================================

def _stream_from_bytes(data: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        iter([data]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"},
    )


def _stream_from_file(path: str, filename: str) -> StreamingResponse:
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


def resolve_report_download(doc: Dict[str, Any]):
    tenant = doc.get("tenant")
    date_str = doc.get("date")
    storage = doc.get("storage") or ""

    filename = _build_filename(tenant, date_str)

    # S3 / remote storage
    if StorageService.is_s3() and storage and not storage.startswith("/") and not storage.startswith("file://"):
        try:
            data = StorageService.get_report_bytes(storage)
            if data is None:
                return None
            return _stream_from_bytes(data, filename)
        except Exception:
            return None

    # Local file
    path = storage
    if storage.startswith("file://"):
        path = storage[len("file://"):]
    if path and os.path.exists(path):
        return _stream_from_file(path, filename)

    return None


# ============================================================
# Delivery
# ============================================================

def deliver_report_links(tenant: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    tenant_doc = TenantService.get_tenant(tenant) or {}
    owner_email = tenant_doc.get("owner_email")
    owner_phone = tenant_doc.get("owner_phone")

    url = get_presigned_or_file_url(doc) or doc.get("storage")
    sent_via: List[str] = []

    if owner_email:
        Messaging.send_email(
            owner_email,
            subject=f"Daily Report {doc.get('date')}",
            text_body=f"Your daily report for {tenant} is ready: {url}",
            tenant=tenant,
        )
        sent_via.append("email")

    if owner_phone:
        Messaging.send_whatsapp_text(
            owner_phone,
            f"Daily report {doc.get('date')} for {tenant}: {url}",
            tenant=tenant,
        )
        sent_via.append("whatsapp")

    col = _reports_col()
    col.update_one(
        {"tenant": tenant, "date": doc.get("date")},
        {"$set": {"sent_via": sent_via, "status": "sent", "sent_at": datetime.now(timezone.utc).replace(tzinfo=None)}},
    )
    new_doc = col.find_one({"tenant": tenant, "date": doc.get("date")})
    return _public_report(new_doc)


# ============================================================
# Public Shape
# ============================================================

def _public_report(d: Dict[str, Any] | None) -> Dict[str, Any]:
    if not d:
        return {}
    out = dict(d)
    out.pop("_id", None)
    out["url"] = get_presigned_or_file_url(out) or out.get("storage")
    return out
