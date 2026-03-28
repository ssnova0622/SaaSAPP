from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Tuple, List, Dict, Any, Optional
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.helpers.constants import DEFAULT_TIMEZONE
from settings import env


def build_daily_report(tenant: str, day: date, snapshot: Dict[str, Any], to_date: Optional[date] = None) -> Tuple[str, bytes]:
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
    title_text = "Daily Report" if not to_date or to_date == day else "Range Report"
    title = Paragraph(f"<b>{title_text}</b>", styles["Title"])
    meta = Paragraph(
        f"Tenant: <b>{tenant}</b><br/>Date: <b>{date_label}</b><br/>Timezone: <b>{tz}</b>",
        styles["Normal"],
    )

    story.append(title)
    story.append(Spacer(1, 12))
    story.append(meta)
    story.append(Spacer(1, 18))

    modules = snapshot.get("modules") or []
    is_store = "store" in modules
    is_service = ("salon" in modules) or ("clinic" in modules) or (not modules) # Fallback to service if no modules

    # 1. Service/Appointments Table
    if is_service:
        service_rows = snapshot.get("rows") or []
        if service_rows or not is_store:
            story.append(Paragraph("<b>Appointments / Services</b>", styles["Heading3"]))
            story.append(Spacer(1, 6))
            
            data: List[List[str]] = [["Time", "Professional", "Customer", "Price", "Status"]]
            if service_rows:
                for r in service_rows:
                    time = str(r.get("time") or "")
                    professional = str(r.get("professional") or "")
                    customer = str(r.get("customer") or "")
                    try:
                        price_val = float(r.get("price") or 0.0)
                    except Exception:
                        price_val = 0.0
                    price = f"{price_val:.2f}"
                    status = str(r.get("status") or "")
                    data.append([time, professional, customer, price, status])
            else:
                data.append(["—", "—", "No appointments", "0.00", "—"])

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
            
            data: List[List[str]] = [["Product", "Qty", "Amount", "Profit", "Customer", "Status"]]
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
                    amount = f"{total_val:.2f}"
                    profit = f"{profit_val:.2f}"
                    customer = str(r.get("customer") or "")
                    status = str(r.get("status") or "")
                    data.append([product, qty, amount, profit, customer, status])
            else:
                data.append(["—", "0", "0.00", "0.00", "No sales", "—"])

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

    totals_data = snapshot.get("totals") or {}
    appts = int(totals_data.get("appointments") or 0)
    canc = int(totals_data.get("cancellations") or 0)
    try:
        revenue_val = float(totals_data.get("revenue") or 0.0)
    except Exception:
        revenue_val = 0.0

    totals_text = f"Totals — Appointments: {appts} • Cancellations: {canc} • Revenue: {revenue_val:.2f}"

    orders_count = int(totals_data.get("orders_count") or 0)
    store_revenue = float(totals_data.get("store_revenue") or 0.0)
    units_sold = float(totals_data.get("units_sold") or 0.0)
    order_status_breakdown = totals_data.get("order_status_breakdown") or {}

    if is_store:
        placed = int(order_status_breakdown.get("placed") or 0)
        confirmed = int(order_status_breakdown.get("confirmed") or 0)
        canceled = int(order_status_breakdown.get("canceled") or 0)
        story.append(Paragraph("<b>Today's order summary</b>", styles["Heading3"]))
        story.append(Spacer(1, 6))
        summary_text = (
            f"Orders placed: <b>{placed}</b> • Confirmed: <b>{confirmed}</b> • Cancelled: <b>{canceled}</b><br/>"
            f"Revenue (today): <b>₹{store_revenue:,.2f}</b> • Units sold: <b>{units_sold:,.0f}</b>"
        )
        story.append(Paragraph(summary_text, styles["Normal"]))
        story.append(Spacer(1, 12))

        top_selling = snapshot.get("top_selling_today") or []
        if top_selling:
            story.append(Paragraph("<b>Most selling products today</b>", styles["Heading3"]))
            story.append(Spacer(1, 6))
            data_ts: List[List[str]] = [["Product", "Qty", "Revenue (₹)"]]
            for r in top_selling[:10]:
                data_ts.append([
                    str(r.get("name") or r.get("sku") or "—")[:40],
                    f"{float(r.get('qty') or 0):,.0f}",
                    f"{float(r.get('revenue') or 0):,.2f}",
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
                data_ls.append([str(r.get("name") or r.get("sku") or "—")[:50], f"{float(r.get('available_qty') or 0):,.0f}"])
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
            data_tc: List[List[str]] = [["Customer", "Orders", "Total (₹)"]]
            for r in top_customer[:5]:
                label = str(r.get("name") or r.get("phone") or "Guest")[:35]
                data_tc.append([label, str(r.get("orders") or 0), f"{float(r.get('total') or 0):,.2f}"])
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

    if orders_count > 0 or store_revenue > 0 or units_sold > 0:
        totals_text += f"<br/>Store — Orders: {orders_count} • Units: {units_sold} • Revenue: ₹{store_revenue:,.2f}"

    status_counts = totals_data.get("status_counts")
    if status_counts:
        counts_parts = [f"{k.capitalize()}: {v}" for k, v in status_counts.items() if v > 0]
        if counts_parts:
            totals_text += "<br/>Status Breakdown: " + " • ".join(counts_parts)

    totals = Paragraph(totals_text, styles["Normal"])
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
