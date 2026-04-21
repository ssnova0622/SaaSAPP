from __future__ import annotations

import os
import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import ASCENDING

from app.helpers.constants import DEFAULT_TIMEZONE
from app.helpers.money_format import format_money

logger = logging.getLogger(__name__)

from app.services.db import get_db
from app.services.s3.storage import StorageService
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
    return StorageService.get_report_bytes(storage)


_DEF_TZ = env.str("DEFAULT_TZ", DEFAULT_TIMEZONE)


def _reports_col():
    db = get_db()
    col = db.get_collection("reports")
    col.create_index([("tenant", ASCENDING), ("date", ASCENDING)], unique=True)
    col.create_index([("tenant", ASCENDING), ("created_at", ASCENDING)])
    return col


def generate_and_store_report(
    tenant: str,
    day: date,
    to_date: Optional[date] = None,
    _snapshot: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build the daily/range report PDF, upload to S3 (or save locally) and persist metadata.
    Accepts an optional pre-built snapshot to avoid a redundant DB fetch when the caller
    already has one (e.g. run_daily_report in the facade).
    Returns the stored report document (public shape).
    """
    snapshot = _snapshot or Storage.get_report_snapshot(tenant, day, to_date)
    fname, pdf_bytes = build_daily_report(tenant, day, snapshot, to_date)

    date_str = day.isoformat()
    if to_date and to_date != day:
        date_str = f"{day.isoformat()}_to_{to_date.isoformat()}"

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


def get_presigned_or_file_url(doc: Dict[str, Any], expires_seconds: int = 86400) -> Optional[str]:
    storage = doc.get("storage")
    return StorageService.get_report_url(storage, expires_seconds) if storage else None


def _report_date_key_in_window(date_key: str, window_start: date, window_end: date) -> bool:
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


def list_reports(
    tenant: str,
    page: int = 1,
    size: int = 50,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> Dict[str, Any]:
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


def ensure_report_downloadable(
    tenant: str,
    date_str: str,
    force_regenerate: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Return a downloadable report document.
    - force_regenerate=True (default for the download endpoint): always rebuilds the PDF
      so the latest report design is used regardless of what was previously stored.
    - force_regenerate=False: only generates when no document exists yet.
    """
    if not force_regenerate:
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
    """Return a StreamingResponse for the PDF (S3 proxy or local file)."""
    tenant = doc.get("tenant")
    date_str = doc.get("date") or ""
    storage = doc.get("storage") or ""

    safe_tenant = str(tenant or "report").replace("/", "-")
    if "_to_" in date_str:
        filename = f"report-{safe_tenant}-{date_str.replace('_to_', '-to-')}.pdf"
    else:
        filename = f"daily-{safe_tenant}-{date_str}.pdf"

    if StorageService.is_s3() and storage and not storage.startswith("/") and not storage.startswith("file://"):
        try:
            data = StorageService.get_report_bytes(storage)
            if data is None:
                return None
            return StreamingResponse(
                iter([data]),
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        except Exception:
            return None

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


# ── Delivery helpers ──────────────────────────────────────────────────────

def _build_wa_summary(
    business_name: str,
    date_str: str,
    snapshot: Dict[str, Any],
) -> str:
    """Build a rich, module-aware WhatsApp text summary of the daily report."""
    totals       = snapshot.get("totals") or {}
    mods         = {str(m).strip().lower() for m in (snapshot.get("modules") or [])}
    is_service   = bool(snapshot.get("has_appointments_module")) or ("salon" in mods) or ("clinic" in mods)
    is_store     = bool(snapshot.get("has_store_module")) or ("store" in mods)
    currency     = str(snapshot.get("currency") or "INR").strip().upper() or "INR"

    def _m(a: Any) -> str:
        try:
            return format_money(float(a), currency)
        except Exception:
            return format_money(0.0, currency)

    svc_revenue   = float(totals.get("revenue") or 0.0)
    svc_appts     = int(totals.get("appointments") or 0)
    svc_cancels   = int(totals.get("cancellations") or 0)
    store_revenue = float(totals.get("store_revenue") or 0.0)
    store_orders  = int(totals.get("orders_count") or 0)
    store_units   = float(totals.get("units_sold") or 0.0)
    total_rev     = svc_revenue + store_revenue
    status_counts = totals.get("status_counts") or {}
    order_sb      = totals.get("order_status_breakdown") or snapshot.get("order_status_breakdown") or {}

    lines: List[str] = []
    lines.append(f"*Daily Report — {business_name}*")
    lines.append(f"Date: {date_str}")
    lines.append("")

    # Revenue summary
    lines.append(f"💰 *Total Revenue: {_m(total_rev)}*")
    if is_service and is_store:
        lines.append(f"   Services: {_m(svc_revenue)}  |  Store: {_m(store_revenue)}")
    lines.append("")

    # Salon / Clinic section
    if is_service:
        comp    = int(status_counts.get("completed") or 0)
        booked  = int(status_counts.get("booked") or 0)
        no_show = int(status_counts.get("no_show") or 0)
        avg_val = svc_revenue / max(1, comp)

        lines.append("💇 *SALON / CLINIC*")
        lines.append(f"• Appointments: {svc_appts}")
        lines.append(
            f"  ✓ Completed: {comp}  |  ⏳ Pending: {booked}"
            + (f"  |  ✗ Cancelled: {svc_cancels}" if svc_cancels else "")
            + (f"  |  ⚫ No-show: {no_show}" if no_show else "")
        )
        lines.append(f"• Revenue: {_m(svc_revenue)}")
        if comp > 0:
            lines.append(f"• Avg per Visit: {_m(avg_val)}")

        # Top professional
        rows = snapshot.get("rows") or []
        prof_stats: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            p = str(r.get("professional") or "").strip()
            if not p:
                continue
            if p not in prof_stats:
                prof_stats[p] = {"total": 0, "completed": 0, "revenue": 0.0}
            prof_stats[p]["total"] += 1
            if str(r.get("status", "")).lower() == "completed":
                prof_stats[p]["completed"] += 1
                prof_stats[p]["revenue"] += float(r.get("price") or 0.0)
        if prof_stats:
            top_p = max(prof_stats.items(), key=lambda kv: kv[1]["revenue"])
            lines.append(
                f"• Top Professional: *{top_p[0]}* "
                f"({top_p[1]['completed']} done, {_m(top_p[1]['revenue'])})"
            )
        lines.append("")

    # Store section
    if is_store:
        placed    = int(order_sb.get("placed") or 0)
        confirmed = int(order_sb.get("confirmed") or 0)
        canceled  = int(order_sb.get("canceled") or 0)

        lines.append("🛍️ *STORE SALES*")
        lines.append(f"• Orders: {store_orders}  |  Units Sold: {store_units:.0f}")
        status_parts = []
        if placed:
            status_parts.append(f"⏳ Pending: {placed}")
        if confirmed:
            status_parts.append(f"✓ Confirmed: {confirmed}")
        if canceled:
            status_parts.append(f"✗ Cancelled: {canceled}")
        if status_parts:
            lines.append("  " + "  |  ".join(status_parts))
        lines.append(f"• Revenue: {_m(store_revenue)}")

        top_selling = snapshot.get("top_selling_today") or []
        if top_selling:
            top_p_obj = top_selling[0]
            lines.append(
                f"• Best Seller: *{str(top_p_obj.get('name') or top_p_obj.get('sku') or '—')[:30]}*"
                f" ({float(top_p_obj.get('qty') or 0):.0f} units, {_m(float(top_p_obj.get('revenue') or 0))})"
            )

        top_customers = snapshot.get("top_customer_today") or []
        if top_customers:
            tc = top_customers[0]
            cname = str(tc.get("name") or tc.get("phone") or "Customer")[:25]
            lines.append(f"• Top Customer: *{cname}* ({tc.get('orders', 0)} orders, {_m(float(tc.get('total') or 0))})")

        # Low stock
        low_stock = snapshot.get("low_stock") or []
        if low_stock:
            lines.append("")
            lines.append(f"⚠️ *LOW STOCK ALERT ({len(low_stock)} item(s))*")
            for ls in low_stock[:5]:
                qty = float(ls.get("available_qty") or 0)
                name = str(ls.get("name") or ls.get("sku") or "—")[:30]
                tag = " ❗CRITICAL" if qty <= 3 else ""
                lines.append(f"  • {name}: {qty:.0f} units{tag}")
            if len(low_stock) > 5:
                lines.append(f"  ... and {len(low_stock) - 5} more item(s).")
        lines.append("")

    lines.append("📄 Full PDF report is attached.")
    return "\n".join(lines)


def _build_html_email(
    business_name: str,
    date_str: str,
    snapshot: Dict[str, Any],
    url: Optional[str],
) -> str:
    """Build a styled HTML email body for the daily report."""
    totals        = snapshot.get("totals") or {}
    mods          = {str(m).strip().lower() for m in (snapshot.get("modules") or [])}
    is_service    = bool(snapshot.get("has_appointments_module")) or ("salon" in mods) or ("clinic" in mods)
    is_store      = bool(snapshot.get("has_store_module")) or ("store" in mods)
    currency      = str(snapshot.get("currency") or "INR").strip().upper() or "INR"

    def _m(a: Any) -> str:
        try:
            return format_money(float(a), currency)
        except Exception:
            return format_money(0.0, currency)

    def _e(s: Any) -> str:
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    svc_revenue   = float(totals.get("revenue") or 0.0)
    svc_appts     = int(totals.get("appointments") or 0)
    svc_cancels   = int(totals.get("cancellations") or 0)
    store_revenue = float(totals.get("store_revenue") or 0.0)
    store_orders  = int(totals.get("orders_count") or 0)
    store_units   = float(totals.get("units_sold") or 0.0)
    total_rev     = svc_revenue + store_revenue
    status_counts = totals.get("status_counts") or {}
    order_sb      = totals.get("order_status_breakdown") or snapshot.get("order_status_breakdown") or {}
    rows          = snapshot.get("rows") or []
    top_selling   = snapshot.get("top_selling_today") or []
    low_stock     = snapshot.get("low_stock") or []
    top_customers = snapshot.get("top_customer_today") or []

    # Per-professional stats
    prof_stats: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        p = str(r.get("professional") or "").strip()
        if not p:
            continue
        if p not in prof_stats:
            prof_stats[p] = {"name": p, "total": 0, "completed": 0, "cancelled": 0, "revenue": 0.0}
        prof_stats[p]["total"] += 1
        st = str(r.get("status", "")).lower()
        if st == "completed":
            prof_stats[p]["completed"] += 1
            prof_stats[p]["revenue"] += float(r.get("price") or 0.0)
        elif st in ("canceled", "cancelled"):
            prof_stats[p]["cancelled"] += 1

    # ── KPI cards HTML ───────────────────────────────────────────────
    kpi_html_parts: List[str] = []

    sub_rev = ""
    if is_service and is_store:
        sub_rev = f"Services: {_m(svc_revenue)} | Store: {_m(store_revenue)}"
    elif is_service:
        sub_rev = f'{status_counts.get("completed", 0)} completed visit(s)'
    elif is_store:
        sub_rev = f"{store_orders} order(s)"

    kpi_html_parts.append(
        f'<td style="background:#0f172a;padding:14px 10px;text-align:center;border-right:1px solid #0f172a;">'
        f'<div style="color:rgba(255,255,255,.65);font-size:10px;text-transform:uppercase;letter-spacing:.05em;">Total Revenue</div>'
        f'<div style="color:#fff;font-size:20px;font-weight:bold;margin:4px 0;">{_e(_m(total_rev))}</div>'
        f'<div style="color:rgba(255,255,255,.45);font-size:10px;">{_e(sub_rev)}</div>'
        f'</td>'
    )
    if is_service:
        comp  = int(status_counts.get("completed") or 0)
        book  = int(status_counts.get("booked") or 0)
        kpi_html_parts.append(
            f'<td style="background:#0d9488;padding:14px 10px;text-align:center;border-right:1px solid #0f172a;">'
            f'<div style="color:rgba(255,255,255,.65);font-size:10px;text-transform:uppercase;letter-spacing:.05em;">Appointments</div>'
            f'<div style="color:#fff;font-size:20px;font-weight:bold;margin:4px 0;">{svc_appts}</div>'
            f'<div style="color:rgba(255,255,255,.45);font-size:10px;">Done: {comp} | Pending: {book}</div>'
            f'</td>'
        )
        if svc_cancels > 0:
            rate = round(svc_cancels / max(1, svc_appts + svc_cancels) * 100, 1)
            kpi_html_parts.append(
                f'<td style="background:#b91c1c;padding:14px 10px;text-align:center;border-right:1px solid #0f172a;">'
                f'<div style="color:rgba(255,255,255,.65);font-size:10px;text-transform:uppercase;letter-spacing:.05em;">Cancellations</div>'
                f'<div style="color:#fff;font-size:20px;font-weight:bold;margin:4px 0;">{svc_cancels}</div>'
                f'<div style="color:rgba(255,255,255,.45);font-size:10px;">{rate}% rate</div>'
                f'</td>'
            )
    if is_store:
        placed = int(order_sb.get("placed") or 0)
        kpi_html_parts.append(
            f'<td style="background:#1d4ed8;padding:14px 10px;text-align:center;border-right:1px solid #0f172a;">'
            f'<div style="color:rgba(255,255,255,.65);font-size:10px;text-transform:uppercase;letter-spacing:.05em;">Store Orders</div>'
            f'<div style="color:#fff;font-size:20px;font-weight:bold;margin:4px 0;">{store_orders}</div>'
            f'<div style="color:rgba(255,255,255,.45);font-size:10px;">Pending: {placed} | Units: {store_units:.0f}</div>'
            f'</td>'
        )
    if low_stock:
        kpi_html_parts.append(
            f'<td style="background:#d97706;padding:14px 10px;text-align:center;">'
            f'<div style="color:rgba(255,255,255,.65);font-size:10px;text-transform:uppercase;letter-spacing:.05em;">Stock Alerts</div>'
            f'<div style="color:#fff;font-size:20px;font-weight:bold;margin:4px 0;">{len(low_stock)}</div>'
            f'<div style="color:rgba(255,255,255,.45);font-size:10px;">items need restocking</div>'
            f'</td>'
        )

    kpi_table = (
        f'<table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">'
        f'<tr>{"".join(kpi_html_parts)}</tr>'
        f'</table>'
    )

    # ── Salon section HTML ───────────────────────────────────────────
    salon_html = ""
    if is_service:
        status_label_map = [
            ("Completed", "completed", "#15803d"),
            ("Booked",    "booked",    "#b45309"),
            ("Cancelled", "canceled",  "#b91c1c"),
            ("No-show",   "no_show",   "#7c3aed"),
        ]
        status_badges = ""
        for lbl, key, col in status_label_map:
            v = int(status_counts.get(key) or 0)
            if v > 0:
                status_badges += (
                    f'<span style="display:inline-block;background:{col};color:#fff;'
                    f'border-radius:4px;padding:2px 8px;font-size:11px;margin-right:6px;">'
                    f'{lbl}: {v}</span>'
                )

        comp_n  = int(status_counts.get("completed") or 0)
        avg_val = svc_revenue / max(1, comp_n)

        # Appointments table rows
        appt_rows_html = ""
        for r in rows[:30]:
            st = str(r.get("status") or "").lower()
            status_col = "#15803d" if st == "completed" else ("#b91c1c" if "cancel" in st else "#b45309")
            appt_rows_html += (
                f'<tr>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;">{_e(r.get("time",""))}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;">{_e(r.get("professional",""))}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;">{_e(r.get("customer",""))}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;text-align:right;">{_e(_m(float(r.get("price") or 0)))}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;color:{status_col};font-weight:bold;">{_e(str(r.get("status","")).capitalize())}</td>'
                f'</tr>'
            )
        if not rows:
            appt_rows_html = '<tr><td colspan="5" style="padding:8px;color:#94a3b8;text-align:center;">No appointments this period</td></tr>'

        # Professional performance rows
        prof_rows_html = ""
        for pv in sorted(prof_stats.values(), key=lambda x: -x["revenue"])[:10]:
            rate = f'{pv["completed"] / max(1, pv["total"]) * 100:.0f}%'
            prof_rows_html += (
                f'<tr>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;">{_e(pv["name"])}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;text-align:center;">{pv["total"]}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;text-align:center;color:#15803d;font-weight:bold;">{pv["completed"]}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;text-align:center;color:#b91c1c;">{pv["cancelled"]}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;text-align:right;">{_e(_m(pv["revenue"]))}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;text-align:center;">{rate}</td>'
                f'</tr>'
            )

        salon_html = f"""
<div style="margin-top:0;">
  <div style="background:#1d4ed8;color:#fff;padding:10px 20px;font-weight:bold;font-size:13px;text-transform:uppercase;letter-spacing:.04em;">
    Salon / Clinic Performance
  </div>
  <div style="padding:16px 20px;background:#fff;">
    <div style="margin-bottom:10px;">{status_badges}</div>
    <table style="width:100%;font-size:12px;border-collapse:collapse;">
      <tr>
        <td style="padding:4px 8px;color:#64748b;font-size:11px;">Completed Revenue</td>
        <td style="padding:4px 8px;font-weight:bold;">{_e(_m(svc_revenue))}</td>
        <td style="padding:4px 8px;color:#64748b;font-size:11px;">Avg per Visit</td>
        <td style="padding:4px 8px;font-weight:bold;">{_e(_m(avg_val))}</td>
        <td style="padding:4px 8px;color:#64748b;font-size:11px;">Cancellations</td>
        <td style="padding:4px 8px;font-weight:bold;color:#b91c1c;">{svc_cancels}</td>
      </tr>
    </table>
    <p style="font-size:12px;font-weight:bold;color:#1e3a5f;margin:16px 0 6px;">Appointment Details</p>
    <table style="width:100%;font-size:11px;border-collapse:collapse;">
      <thead>
        <tr style="background:#334155;color:#fff;">
          <th style="padding:6px 8px;text-align:left;">Time</th>
          <th style="padding:6px 8px;text-align:left;">Professional</th>
          <th style="padding:6px 8px;text-align:left;">Customer</th>
          <th style="padding:6px 8px;text-align:right;">Value</th>
          <th style="padding:6px 8px;text-align:left;">Status</th>
        </tr>
      </thead>
      <tbody>{appt_rows_html}</tbody>
    </table>
    {'<p style="font-size:12px;font-weight:bold;color:#1e3a5f;margin:16px 0 6px;">Professional Performance</p><table style="width:100%;font-size:11px;border-collapse:collapse;"><thead><tr style="background:#334155;color:#fff;"><th style="padding:6px 8px;text-align:left;">Professional</th><th style="padding:6px 8px;text-align:center;">Total</th><th style="padding:6px 8px;text-align:center;">Completed</th><th style="padding:6px 8px;text-align:center;">Cancelled</th><th style="padding:6px 8px;text-align:right;">Revenue</th><th style="padding:6px 8px;text-align:center;">Rate</th></tr></thead><tbody>' + prof_rows_html + '</tbody></table>' if prof_stats else ''}
  </div>
</div>"""

    # ── Store section HTML ───────────────────────────────────────────
    store_html = ""
    if is_store:
        placed    = int(order_sb.get("placed") or 0)
        confirmed = int(order_sb.get("confirmed") or 0)
        delivered = int(order_sb.get("delivered") or 0)
        canceled  = int(order_sb.get("canceled") or 0)

        # Top products rows
        tp_rows_html = ""
        for i, r in enumerate(top_selling[:10], 1):
            rank_col = "#ca8a04" if i <= 3 else "#334155"
            tp_rows_html += (
                f'<tr>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;text-align:center;font-weight:bold;color:{rank_col};">{i}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;">{_e(str(r.get("name") or r.get("sku") or "—")[:40])}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;text-align:center;">{float(r.get("qty") or 0):,.0f}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;text-align:right;">{_e(_m(float(r.get("revenue") or 0)))}</td>'
                f'</tr>'
            )

        # Top customers rows
        tc_rows_html = ""
        for i, r in enumerate(top_customers[:5], 1):
            lbl = str(r.get("name") or r.get("phone") or "Guest")[:30]
            tc_rows_html += (
                f'<tr>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;text-align:center;font-weight:bold;color:#ca8a04;">{i}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;">{_e(lbl)}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;text-align:center;">{r.get("orders", 0)}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;text-align:right;">{_e(_m(float(r.get("total") or 0)))}</td>'
                f'</tr>'
            )

        # Low stock rows
        ls_rows_html = ""
        for r in low_stock[:15]:
            qty = float(r.get("available_qty") or 0)
            lvl_col = "#b91c1c" if qty <= 3 else "#d97706"
            lvl     = "CRITICAL" if qty <= 3 else "LOW"
            ls_rows_html += (
                f'<tr>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;">{_e(str(r.get("name") or r.get("sku") or "—")[:40])}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;text-align:center;">{qty:,.0f}</td>'
                f'<td style="padding:5px 8px;border-bottom:1px solid #e2e8f0;text-align:center;font-weight:bold;color:{lvl_col};">{lvl}</td>'
                f'</tr>'
            )

        store_html = f"""
<div style="margin-top:0;">
  <div style="background:#1d4ed8;color:#fff;padding:10px 20px;font-weight:bold;font-size:13px;text-transform:uppercase;letter-spacing:.04em;">
    Store Sales Report
  </div>
  <div style="padding:16px 20px;background:#fff;">
    <table style="width:100%;font-size:12px;border-collapse:collapse;margin-bottom:12px;">
      <tr>
        <td style="padding:4px 8px;color:#64748b;font-size:11px;">Revenue</td>
        <td style="padding:4px 8px;font-weight:bold;">{_e(_m(store_revenue))}</td>
        <td style="padding:4px 8px;color:#64748b;font-size:11px;">Orders</td>
        <td style="padding:4px 8px;font-weight:bold;">{store_orders}</td>
        <td style="padding:4px 8px;color:#64748b;font-size:11px;">Units Sold</td>
        <td style="padding:4px 8px;font-weight:bold;">{store_units:.0f}</td>
      </tr>
      <tr>
        <td style="padding:4px 8px;color:#64748b;font-size:11px;">Pending</td>
        <td style="padding:4px 8px;font-weight:bold;color:{'#b91c1c' if placed > 0 else '#334155'};">{placed}</td>
        <td style="padding:4px 8px;color:#64748b;font-size:11px;">Confirmed</td>
        <td style="padding:4px 8px;font-weight:bold;color:#15803d;">{confirmed}</td>
        <td style="padding:4px 8px;color:#64748b;font-size:11px;">Cancelled</td>
        <td style="padding:4px 8px;font-weight:bold;">{canceled}</td>
      </tr>
    </table>
    {'<p style="font-size:12px;font-weight:bold;color:#1e3a5f;margin:12px 0 6px;">Top Products by Units Sold</p><table style="width:100%;font-size:11px;border-collapse:collapse;"><thead><tr style="background:#334155;color:#fff;"><th style="padding:6px 8px;text-align:center;width:36px;">#</th><th style="padding:6px 8px;text-align:left;">Product</th><th style="padding:6px 8px;text-align:center;">Units</th><th style="padding:6px 8px;text-align:right;">Revenue</th></tr></thead><tbody>' + tp_rows_html + '</tbody></table>' if top_selling else ''}
    {'<p style="font-size:12px;font-weight:bold;color:#1e3a5f;margin:16px 0 6px;">Top Customers by Spend</p><table style="width:100%;font-size:11px;border-collapse:collapse;"><thead><tr style="background:#334155;color:#fff;"><th style="padding:6px 8px;text-align:center;width:36px;">#</th><th style="padding:6px 8px;text-align:left;">Customer</th><th style="padding:6px 8px;text-align:center;">Orders</th><th style="padding:6px 8px;text-align:right;">Total Spend</th></tr></thead><tbody>' + tc_rows_html + '</tbody></table>' if top_customers else ''}
    {'<div style="background:#fef2f2;border:1px solid #fecaca;border-radius:6px;padding:12px 16px;margin-top:16px;"><p style="margin:0 0 8px;font-weight:bold;color:#b91c1c;font-size:12px;">&#9888; Stock Alert — ' + str(len(low_stock)) + ' item(s) running low</p><table style="width:100%;font-size:11px;border-collapse:collapse;"><thead><tr style="background:#334155;color:#fff;"><th style="padding:6px 8px;text-align:left;">Product / SKU</th><th style="padding:6px 8px;text-align:center;">Qty Left</th><th style="padding:6px 8px;text-align:center;">Level</th></tr></thead><tbody>' + ls_rows_html + '</tbody></table></div>' if low_stock else ''}
  </div>
</div>"""

    pdf_link_html = ""
    if url:
        pdf_link_html = (
            f'<p style="margin:0 0 8px;"><a href="{url}" style="background:#1d4ed8;color:#fff;'
            f'padding:8px 20px;border-radius:4px;text-decoration:none;font-size:13px;display:inline-block;">'
            f'Open / Download Full PDF Report</a></p>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Daily Report — {_e(business_name)}</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#1e293b;">
<table width="100%" cellspacing="0" cellpadding="0" style="background:#f1f5f9;">
  <tr>
    <td align="center" style="padding:24px 12px;">
      <table width="600" cellspacing="0" cellpadding="0" style="max-width:600px;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">

        <!-- Header -->
        <tr>
          <td style="background:#1e3a5f;padding:22px 24px;">
            <p style="margin:0;color:#fff;font-size:20px;font-weight:bold;">{_e(business_name)}</p>
            <p style="margin:4px 0 0;color:#94a3b8;font-size:13px;">Daily Business Report &nbsp;&#124;&nbsp; {_e(date_str)}</p>
          </td>
        </tr>

        <!-- KPI strip -->
        <tr>
          <td style="padding:0;border-bottom:2px solid #0f172a;">
            {kpi_table}
          </td>
        </tr>

        <!-- Salon section -->
        {'<tr><td style="padding:0;">' + salon_html + '</td></tr>' if is_service else ''}

        <!-- Store section -->
        {'<tr><td style="padding:0;border-top:4px solid #f1f5f9;">' + store_html + '</td></tr>' if is_store else ''}

        <!-- PDF Link -->
        <tr>
          <td style="padding:20px 24px;background:#f8fafc;border-top:1px solid #e2e8f0;">
            <p style="margin:0 0 12px;font-size:13px;color:#64748b;">
              The full PDF report is attached to this email. You can also open it online:
            </p>
            {pdf_link_html}
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:14px 24px;background:#f1f5f9;border-top:1px solid #e2e8f0;text-align:center;">
            <p style="margin:0;font-size:11px;color:#94a3b8;">
              Generated automatically &nbsp;&#124;&nbsp; {_e(date_str)} &nbsp;&#124;&nbsp; {_e(business_name)}
            </p>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


def deliver_report_links(
    tenant: str,
    doc: Dict[str, Any],
    snapshot: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Deliver the daily report: email with PDF + HTML body, WhatsApp with rich text summary.
    Pass `snapshot` (from generate_and_store_report) to avoid a redundant DB fetch.
    """
    tenant_doc    = Storage.get_tenant(tenant) or {}
    owner_email   = (tenant_doc.get("owner_email") or "").strip()
    owner_phone   = (tenant_doc.get("owner_phone") or "").strip()
    business_name = str(tenant_doc.get("business_name") or tenant_doc.get("name") or tenant)
    delivery      = str(tenant_doc.get("invoice_delivery") or "both").strip().lower()

    if delivery in ("email", "e-mail", "mail"):
        send_email, send_whatsapp = True, False
    elif delivery in ("whatsapp", "wa"):
        send_email, send_whatsapp = False, True
    else:
        send_email = send_whatsapp = True

    url      = get_presigned_or_file_url(doc) or doc.get("storage")
    date_str = doc.get("date", "")
    sent_via: List[str] = []

    # Resolve snapshot for rich message building (lazy fetch only if not provided)
    _snap: Dict[str, Any] = snapshot or {}

    def _get_snap() -> Dict[str, Any]:
        nonlocal _snap
        if not _snap:
            try:
                if "_to_" in date_str:
                    a, b = date_str.split("_to_", 1)
                    d0 = date.fromisoformat(a.strip())
                    d1 = date.fromisoformat(b.strip())
                else:
                    d0 = date.fromisoformat(date_str.strip())
                    d1 = None
                _snap = Storage.get_report_snapshot(tenant, d0, d1)
            except Exception:
                _snap = {}
        return _snap

    # ── Email ────────────────────────────────────────────────────────
    if owner_email and send_email:
        pdf_bytes = get_report_pdf_bytes(doc)
        subject   = f"Daily Report \u2013 {business_name} \u2013 {date_str}"
        text_body = (
            f"Your daily report for {business_name} ({date_str}) is attached.\n\n"
            f"You can also open the report here: {url}"
        )
        html_body: Optional[str] = None
        try:
            s = _get_snap()
            if s:
                html_body = _build_html_email(business_name, date_str, s, url)
        except Exception as html_err:
            logger.warning("HTML email body build failed for %s: %s", tenant, html_err)

        attachments = None
        if pdf_bytes:
            fname = f"daily-report-{tenant}-{date_str}.pdf"
            attachments = [(fname, pdf_bytes, "application/pdf")]
        try:
            Messaging.send_email(
                owner_email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                tenant=tenant,
                attachments=attachments,
            )
            sent_via.append("email")
        except Exception as e:
            logger.warning("Report email delivery failed for %s: %s", tenant, e)

    # ── WhatsApp ──────────────────────────────────────────────────────
    if owner_phone and send_whatsapp:
        wa_text = (
            f"Daily Report \u2013 {business_name} \u2013 {date_str}\n\n"
            f"Open your report (PDF): {url}"
        )
        wa_caption = f"Daily report \u2013 {business_name} \u2013 {date_str}"

        # Build rich summary if snapshot available
        try:
            s = _get_snap()
            if s:
                wa_text = _build_wa_summary(business_name, date_str, s)
        except Exception as wa_err:
            logger.warning("WA summary build failed for %s: %s", tenant, wa_err)

        presigned     = get_presigned_or_file_url(doc)
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
                        tenant, doc_err,
                    )
                    Messaging.send_whatsapp_text(owner_phone, wa_text, tenant=tenant)
            else:
                logger.info(
                    "Report WhatsApp: no public PDF URL for %s; sending rich text summary",
                    tenant,
                )
                Messaging.send_whatsapp_text(owner_phone, wa_text, tenant=tenant)
            sent_via.append("whatsapp")
        except Exception as e:
            logger.warning("Report WhatsApp delivery failed for %s: %s", tenant, e)

    col = _reports_col()
    col.update_one(
        {"tenant": tenant, "date": doc.get("date")},
        {"$set": {
            "sent_via": sent_via,
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).replace(tzinfo=None),
        }},
    )
    new_doc = col.find_one({"tenant": tenant, "date": doc.get("date")})
    return _public_report(new_doc)


def _public_report(d: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not d:
        return {}
    out = dict(d)
    out.pop("_id", None)
    out["url"] = get_presigned_or_file_url(out) or out.get("storage")
    return out
