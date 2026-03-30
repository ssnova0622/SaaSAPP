from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Tuple, List, Dict, Any, Optional
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.helpers.constants import DEFAULT_TIMEZONE
from app.helpers.money_format import format_money
from settings import env


def build_daily_report(tenant: str, day: date, snapshot: Dict[str, Any], to_date: Optional[date] = None) -> Tuple[
    str, bytes]:
    """
    Build a report PDF for the given tenant and date range from a provided snapshot.
    If to_date is provided and different from day, it's a range report.
    Returns (filename, pdf_bytes).
    """
    # Prepare a buffer for PDF bytes
    buf = BytesIO()

    date_label = day.isoformat()
    if to_date and to_date != day:
        date_label = f"{day.isoformat()} to {to_date.isoformat()}"

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
        title=f"Report - {tenant} - {date_label}",
    )

    styles = getSampleStyleSheet()
    story: List = []

    tz = str(snapshot.get("tz") or env.str("DEFAULT_TZ", DEFAULT_TIMEZONE))
    title_text = "Business activity report"
    if to_date and to_date != day:
        title_text += " (date range)"
    else:
        title_text += " (single day)"
    title = Paragraph(f"<b>{title_text}</b>", styles["Title"])

    mods = {str(m).strip().lower() for m in (snapshot.get("modules") or []) if str(m).strip()}
    if snapshot.get("has_appointments_module") is not None:
        is_service = bool(snapshot.get("has_appointments_module"))
        is_store = bool(snapshot.get("has_store_module"))
    else:
        is_service = ("salon" in mods) or ("clinic" in mods)
        is_store = "store" in mods

    scope_bits = []
    if is_service:
        scope_bits.append("appointments / services")
    if is_store:
        scope_bits.append("store sales")
    scope_line = " and ".join(scope_bits) if scope_bits else "enabled workspace modules"
    meta = Paragraph(
        f"<b>Who this is for:</b> snapshot of <b>{scope_line}</b> for your business (only modules you use are included).<br/>"
        f"<b>Workspace:</b> {tenant}<br/><b>Period:</b> {date_label}<br/><b>Timezone:</b> {tz}",
        styles["Normal"],
    )

    story.append(title)
    story.append(Spacer(1, 12))
    story.append(meta)
    story.append(Spacer(1, 12))

    currency = str(snapshot.get("currency") or "INR").strip().upper() or "INR"

    def _money(a: float) -> str:
        return format_money(float(a), currency)

    totals_data = snapshot.get("totals") or {}
    story.append(Paragraph("<b>At a glance — read this first</b>", styles["Heading3"]))
    story.append(Spacer(1, 6))
    glance_lines: List[str] = []
    if is_service:
        appt_n = int(totals_data.get("appointments") or 0)
        canc_n = int(totals_data.get("cancellations") or 0)
        try:
            rev_svc = float(totals_data.get("revenue") or 0.0)
        except Exception:
            rev_svc = 0.0
        glance_lines.append(
            f"• <b>Services:</b> {appt_n} appointment row(s) in period; {canc_n} cancellation(s); "
            f"revenue from completed visits: <b>{_money(rev_svc)}</b>.",
        )
    if is_store:
        oc_n = int(totals_data.get("orders_count") or 0)
        try:
            sr_n = float(totals_data.get("store_revenue") or 0.0)
            us_n = float(totals_data.get("units_sold") or 0.0)
        except Exception:
            sr_n, us_n = 0.0, 0.0
        glance_lines.append(
            f"• <b>Store:</b> {oc_n} order(s) (excl. canceled where applicable), "
            f"<b>{_money(sr_n)}</b> revenue, <b>{us_n:,.0f}</b> units.",
        )
    if not glance_lines:
        glance_lines.append(
            "• No salon/clinic or store module is enabled for this workspace, or there was no activity in this period."
        )
    for line in glance_lines:
        story.append(Paragraph(line, styles["Normal"]))
    story.append(Spacer(1, 16))

    # 1. Service/Appointments Table (salon / clinic only)
    if is_service:
        service_rows = snapshot.get("rows") or []
        if service_rows or not is_store:
            story.append(Paragraph("<b>Appointments / Services</b>", styles["Heading3"]))
            story.append(Spacer(1, 6))

            data: List[List[str]] = [["Time", "Professional", "Customer", f"Price ({currency})", "Status"]]
            if service_rows:
                for r in service_rows:
                    time = str(r.get("time") or "")
                    professional = str(r.get("professional") or "")
                    customer = str(r.get("customer") or "")
                    try:
                        price_val = float(r.get("price") or 0.0)
                    except Exception:
                        price_val = 0.0
                    price = _money(price_val)
                    status = str(r.get("status") or "")
                    data.append([time, professional, customer, price, status])
            else:
                data.append(["—", "—", "No appointments", _money(0.0), "—"])

            table = Table(data, repeatRows=1, colWidths=[60, 100, 150, 60, 100])
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
            story.append(table)
            story.append(Spacer(1, 18))

    # 2. Store Sales Table
    if is_store:
        order_rows = snapshot.get("order_rows") or []
        if order_rows or not is_service:
            story.append(Paragraph("<b>Product Sales</b>", styles["Heading3"]))
            story.append(Spacer(1, 6))

            data: List[List[str]] = [
                ["Product", "Qty", f"Amount ({currency})", f"Profit ({currency})", "Customer", "Status"],
            ]
            if order_rows:
                for r in order_rows:
                    product = str(r.get("product") or "")
                    qty = str(r.get("qty") or "0")
                    try:
                        total_val = float(r.get("total") or 0.0)
                        profit_val = float(r.get("profit") or 0.0)
                    except Exception:
                        total_val = 0.0
                        profit_val = 0.0
                    amount = _money(total_val)
                    profit = _money(profit_val)
                    customer = str(r.get("customer") or "")
                    status = str(r.get("status") or "")
                    data.append([product, qty, amount, profit, customer, status])
            else:
                data.append(["—", "0", _money(0.0), _money(0.0), "No sales", "—"])

            table = Table(data, repeatRows=1, colWidths=[150, 40, 70, 70, 100, 70])
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
            story.append(table)
            story.append(Spacer(1, 18))

    orders_count = int(totals_data.get("orders_count") or 0)
    store_revenue = float(totals_data.get("store_revenue") or 0.0)
    units_sold = float(totals_data.get("units_sold") or 0.0)
    order_status_breakdown = totals_data.get("order_status_breakdown") or {}

    summary_lines: List[str] = []
    if is_service:
        appts = int(totals_data.get("appointments") or 0)
        canc = int(totals_data.get("cancellations") or 0)
        try:
            revenue_val = float(totals_data.get("revenue") or 0.0)
        except Exception:
            revenue_val = 0.0
        summary_lines.append(
            f"Services — Appointments (rows): {appts} • Cancellations: {canc} • Completed revenue: {_money(revenue_val)}"
        )

    if is_store:
        placed = int(order_status_breakdown.get("placed") or 0)
        confirmed = int(order_status_breakdown.get("confirmed") or 0)
        canceled = int(order_status_breakdown.get("canceled") or 0)
        order_heading = "Order summary (this period)" if (to_date and to_date != day) else "Order summary (this day)"
        story.append(Paragraph(f"<b>{order_heading}</b>", styles["Heading3"]))
        story.append(Spacer(1, 6))
        summary_text = (
            f"Placed: <b>{placed}</b> • Confirmed: <b>{confirmed}</b> • Cancelled: <b>{canceled}</b><br/>"
            f"Revenue: <b>{_money(store_revenue)}</b> • Units sold: <b>{units_sold:,.0f}</b>"
        )
        story.append(Paragraph(summary_text, styles["Normal"]))
        story.append(Spacer(1, 12))

        top_selling = snapshot.get("top_selling_today") or []
        if top_selling:
            story.append(Paragraph("<b>Most selling products today</b>", styles["Heading3"]))
            story.append(Spacer(1, 6))
            data_ts: List[List[str]] = [["Product", "Qty", f"Revenue ({currency})"]]
            for r in top_selling[:10]:
                data_ts.append([
                    str(r.get("name") or r.get("sku") or "—")[:40],
                    f"{float(r.get('qty') or 0):,.0f}",
                    _money(float(r.get("revenue") or 0)),
                ])
            table_ts = Table(data_ts, repeatRows=1, colWidths=[200, 60, 80])
            table_ts.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ])
            )
            story.append(table_ts)
            story.append(Spacer(1, 12))

        low_stock = snapshot.get("low_stock") or []
        if low_stock:
            story.append(Paragraph("<b>Stock running low soon</b>", styles["Heading3"]))
            story.append(Spacer(1, 6))
            data_ls: List[List[str]] = [["Product / SKU", "Available Qty"]]
            for r in low_stock[:15]:
                data_ls.append(
                    [str(r.get("name") or r.get("sku") or "—")[:50], f"{float(r.get('available_qty') or 0):,.0f}"])
            table_ls = Table(data_ls, repeatRows=1, colWidths=[250, 80])
            table_ls.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ])
            )
            story.append(table_ls)
            story.append(Spacer(1, 12))

        top_customer = snapshot.get("top_customer_today") or []
        if top_customer:
            story.append(Paragraph("<b>Top customers today (by spend)</b>", styles["Heading3"]))
            story.append(Spacer(1, 6))
            data_tc: List[List[str]] = [["Customer", "Orders", f"Total ({currency})"]]
            for r in top_customer[:5]:
                label = str(r.get("name") or r.get("phone") or "Guest")[:35]
                data_tc.append([label, str(r.get("orders") or 0), _money(float(r.get("total") or 0))])
            table_tc = Table(data_tc, repeatRows=1, colWidths=[180, 60, 90])
            table_tc.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ])
            )
            story.append(table_tc)
            story.append(Spacer(1, 12))

    if is_store and (orders_count > 0 or store_revenue > 0 or units_sold > 0):
        summary_lines.append(
            f"Store — Orders: {orders_count} • Units: {units_sold:,.0f} • Revenue: {_money(store_revenue)}"
        )

    status_counts = totals_data.get("status_counts") if is_service else None
    if status_counts and is_service:
        counts_parts = [f"{k.capitalize()}: {v}" for k, v in status_counts.items() if v > 0]
        if counts_parts:
            summary_lines.append("Appointment status — " + " • ".join(counts_parts))

    if not summary_lines:
        summary_lines.append("Totals — No enabled modules with data in this period, or all counts are zero.")

    totals = Paragraph("<br/>".join(summary_lines), styles["Normal"])
    generated = Paragraph(
        f"Generated at: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", styles["Italic"]
    )
    story.append(totals)
    story.append(Spacer(1, 6))
    story.append(generated)

    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()

    if to_date and to_date != day:
        filename = f"report-{tenant}-{day.isoformat()}-to-{to_date.isoformat()}.pdf"
    else:
        filename = f"daily-{tenant}-{day.isoformat()}.pdf"

    return filename, pdf_bytes
