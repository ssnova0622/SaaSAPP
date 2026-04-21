from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.helpers.constants import DEFAULT_TIMEZONE
from app.helpers.money_format import format_money
from settings import env

# ── Palette ────────────────────────────────────────────────────────────────
_C: Dict[str, Any] = {
    "hdr_bg":  HexColor("#1e3a5f"),
    "sec_bg":  HexColor("#1d4ed8"),
    "kpi_rev": HexColor("#0f172a"),
    "kpi_svc": HexColor("#0d9488"),
    "kpi_st":  HexColor("#1d4ed8"),
    "kpi_warn":HexColor("#d97706"),
    "kpi_neg": HexColor("#b91c1c"),
    "success": HexColor("#15803d"),
    "cancel":  HexColor("#b91c1c"),
    "pending": HexColor("#b45309"),
    "tbl_hdr": HexColor("#334155"),
    "tbl_alt": HexColor("#f1f5f9"),
    "border":  HexColor("#cbd5e1"),
    "muted":   HexColor("#64748b"),
    "gold":    HexColor("#ca8a04"),
}

# Usable page width (A4 = 595.27 pt, 36 pt margin each side)
PW = A4[0] - 72


# ── Style helpers ─────────────────────────────────────────────────────────

def _ps(
    name: str,
    size: int = 9,
    bold: bool = False,
    align: int = TA_LEFT,
    color: Any = None,
    leading: Optional[int] = None,
) -> ParagraphStyle:
    return ParagraphStyle(
        name,
        fontSize=size,
        fontName="Helvetica-Bold" if bold else "Helvetica",
        alignment=align,
        textColor=color or colors.black,
        leading=leading or (size + 3),
    )


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def _section_header(story: list, text: str) -> None:
    t = Table(
        [[_p(f'<font color="white"><b>{text}</b></font>',
             _ps("sh", 11, bold=True, align=TA_LEFT))]],
        colWidths=[PW],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _C["sec_bg"]),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))


def _kpi_row(kpis: List[Dict[str, Any]]) -> Table:
    """Row of KPI cards. Each dict: {label, value, sub?, color?}."""
    n = len(kpis) or 1
    cw = PW / n
    label_s = _ps("kl", 7, align=TA_CENTER, color=colors.white)
    value_s = _ps("kv", 14, bold=True, align=TA_CENTER, color=colors.white, leading=17)
    sub_s   = _ps("ks", 7, align=TA_CENTER, color=HexColor("#cbd5e1"))
    data = [
        [_p(k["label"].upper(), label_s) for k in kpis],
        [_p(str(k["value"]), value_s) for k in kpis],
        [_p(str(k.get("sub") or ""), sub_s) for k in kpis],
    ]
    t = Table(data, colWidths=[cw] * n)
    cmds: List[Any] = [
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 9),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("LINEAFTER",    (0, 0), (-2, -1), 0.5, HexColor("#0f172a")),
    ]
    for i, k in enumerate(kpis):
        cmds.append(("BACKGROUND", (i, 0), (i, -1), k.get("color", _C["kpi_st"])))
    t.setStyle(TableStyle(cmds))
    return t


def _tbl(data: List[List], col_widths: List[float],
         left_cols: Optional[List[int]] = None) -> Table:
    """Standard table: dark header + alternating rows."""
    t = Table(data, colWidths=col_widths, repeatRows=1)
    left = left_cols or [0]
    base = [
        ("BACKGROUND",  (0, 0), (-1, 0), _C["tbl_hdr"]),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",(0, 0), (-1, -1), 5),
        ("GRID",        (0, 0), (-1, -1), 0.25, _C["border"]),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, _C["tbl_alt"]]),
    ]
    for col in left:
        base.append(("ALIGN", (col, 1), (col, -1), "LEFT"))
    t.setStyle(TableStyle(base))
    return t


def _sub_heading(story: list, text: str) -> None:
    story.append(_p(f"<b>{text}</b>", _ps("h3", 9, bold=True, color=_C["hdr_bg"])))
    story.append(Spacer(1, 4))


# ── Main builder ─────────────────────────────────────────────────────────

def build_daily_report(
    tenant: str,
    day: date,
    snapshot: Dict[str, Any],
    to_date: Optional[date] = None,
) -> Tuple[str, bytes]:
    """Build a rich, informative daily report PDF for the given tenant and period."""
    buf = BytesIO()
    date_label = day.isoformat()
    if to_date and to_date != day:
        date_label = f"{day.isoformat()} to {to_date.isoformat()}"

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36,
        title=f"Daily Report - {tenant} - {date_label}",
    )
    story: List[Any] = []

    tz = str(snapshot.get("tz") or env.str("DEFAULT_TZ", DEFAULT_TIMEZONE))
    currency = str(snapshot.get("currency") or "INR").strip().upper() or "INR"
    business_name = str(snapshot.get("business_name") or tenant).strip()

    def _m(a: Any) -> str:
        try:
            return format_money(float(a), currency)
        except Exception:
            return format_money(0.0, currency)

    mods = {str(m).strip().lower() for m in (snapshot.get("modules") or []) if str(m).strip()}
    if snapshot.get("has_appointments_module") is not None:
        is_service = bool(snapshot.get("has_appointments_module"))
        is_store   = bool(snapshot.get("has_store_module"))
    else:
        is_service = ("salon" in mods) or ("clinic" in mods)
        is_store   = "store" in mods

    totals       = snapshot.get("totals") or {}
    rows         = snapshot.get("rows") or []
    order_rows   = snapshot.get("order_rows") or []
    top_selling  = snapshot.get("top_selling_today") or []
    low_stock    = snapshot.get("low_stock") or []
    top_customers = snapshot.get("top_customer_today") or []
    status_counts = totals.get("status_counts") or {}
    order_sb     = totals.get("order_status_breakdown") or snapshot.get("order_status_breakdown") or {}

    svc_revenue  = float(totals.get("revenue") or 0.0)
    svc_appts    = int(totals.get("appointments") or 0)
    svc_cancels  = int(totals.get("cancellations") or 0)
    store_revenue = float(totals.get("store_revenue") or 0.0)
    store_orders  = int(totals.get("orders_count") or 0)
    store_units   = float(totals.get("units_sold") or 0.0)
    total_rev     = svc_revenue + store_revenue

    # ── Compute per-professional stats from appointment rows ───────────
    prof_stats: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        p = str(r.get("professional") or "Unassigned").strip() or "Unassigned"
        if p not in prof_stats:
            prof_stats[p] = {"name": p, "total": 0, "completed": 0, "cancelled": 0, "revenue": 0.0}
        prof_stats[p]["total"] += 1
        st = str(r.get("status", "")).lower()
        if st == "completed":
            prof_stats[p]["completed"] += 1
            prof_stats[p]["revenue"] += float(r.get("price") or 0.0)
        elif st in ("canceled", "cancelled"):
            prof_stats[p]["cancelled"] += 1

    # ── HEADER ────────────────────────────────────────────────────────
    hdr = Table(
        [[
            _p(f'<font color="white"><b>{business_name.upper()}</b></font>',
               _ps("hn", 14, bold=True, align=TA_LEFT, color=colors.white)),
            _p(
                f'<font color="white"><b>DAILY BUSINESS REPORT</b></font><br/>'
                f'<font color="#94a3b8">{date_label}  |  {tz}</font>',
                _ps("hd", 10, align=TA_RIGHT, color=colors.white),
            ),
        ]],
        colWidths=[PW * 0.55, PW * 0.45],
    )
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), _C["hdr_bg"]),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 14))

    # ── KPI BOXES ─────────────────────────────────────────────────────
    kpis: List[Dict[str, Any]] = []

    sub_rev = ""
    if is_service and is_store:
        sub_rev = f"Services: {_m(svc_revenue)} | Store: {_m(store_revenue)}"
    elif is_service:
        sub_rev = f'From {status_counts.get("completed", 0)} completed visit(s)'
    elif is_store:
        sub_rev = f"From {store_orders} order(s)"
    kpis.append({"label": "Total Revenue", "value": _m(total_rev), "sub": sub_rev, "color": _C["kpi_rev"]})

    if is_service:
        comp = int(status_counts.get("completed") or 0)
        book = int(status_counts.get("booked") or 0)
        kpis.append({
            "label": "Appointments",
            "value": str(svc_appts),
            "sub": f"Done: {comp}  |  Pending: {book}",
            "color": _C["kpi_svc"],
        })
        if svc_cancels > 0:
            rate = round(svc_cancels / max(1, svc_appts + svc_cancels) * 100, 1)
            kpis.append({
                "label": "Cancellations",
                "value": str(svc_cancels),
                "sub": f"{rate}% rate",
                "color": _C["kpi_neg"],
            })

    if is_store:
        placed = int(order_sb.get("placed") or 0)
        kpis.append({
            "label": "Store Orders",
            "value": str(store_orders),
            "sub": f"Pending: {placed}  |  Units: {store_units:.0f}",
            "color": _C["kpi_st"],
        })

    if low_stock:
        kpis.append({
            "label": "Stock Alerts",
            "value": str(len(low_stock)),
            "sub": "items low / critical",
            "color": _C["kpi_warn"],
        })

    if kpis:
        story.append(_kpi_row(kpis[:5]))
        story.append(Spacer(1, 18))

    # ── SALON / CLINIC SECTION ─────────────────────────────────────────
    if is_service:
        _section_header(story, "SALON / CLINIC PERFORMANCE")

        # Appointment status summary line
        status_label_map = [
            ("Completed", "completed"), ("Booked", "booked"),
            ("Cancelled", "canceled"), ("No-show", "no_show"),
            ("Needs Reschedule", "needs_reschedule"),
        ]
        sc_parts = [
            f"<b>{lbl}:</b> {int(status_counts.get(k, 0))}"
            for lbl, k in status_label_map
            if status_counts.get(k, 0) > 0
        ]
        if sc_parts:
            story.append(_p("  |  ".join(sc_parts), _ps("sc", 9, leading=12)))
            story.append(Spacer(1, 5))

        comp_n = int(status_counts.get("completed") or 0)
        avg_val = svc_revenue / max(1, comp_n)
        story.append(_p(
            f"Completed Revenue: <b>{_m(svc_revenue)}</b>  |  "
            f"Average per Completed Visit: <b>{_m(avg_val)}</b>",
            _ps("rv", 9, leading=12),
        ))
        story.append(Spacer(1, 12))

        # Appointments table
        _sub_heading(story, "Appointment Details")
        appt_data: List[List[Any]] = [["Time", "Professional", "Customer", f"Value ({currency})", "Status"]]
        for r in rows:
            appt_data.append([
                str(r.get("time") or ""),
                str(r.get("professional") or "")[:22],
                str(r.get("customer") or "")[:28],
                _m(float(r.get("price") or 0.0)),
                str(r.get("status") or "").capitalize(),
            ])
        if not rows:
            appt_data.append(["—", "—", "No appointments this period", "—", "—"])

        appt_t = Table(appt_data, repeatRows=1, colWidths=[60, 118, 175, 80, 90])
        appt_cmds: List[Any] = [
            ("BACKGROUND",    (0, 0), (-1, 0), _C["tbl_hdr"]),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("ALIGN",         (2, 1), (2, -1), "LEFT"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 5),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
            ("GRID",          (0, 0), (-1, -1), 0.25, _C["border"]),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, _C["tbl_alt"]]),
        ]
        for i, r in enumerate(rows, 1):
            st = str(r.get("status", "")).lower()
            if st == "completed":
                appt_cmds += [
                    ("TEXTCOLOR", (4, i), (4, i), _C["success"]),
                    ("FONTNAME",  (4, i), (4, i), "Helvetica-Bold"),
                ]
            elif st in ("canceled", "cancelled"):
                appt_cmds.append(("TEXTCOLOR", (4, i), (4, i), _C["cancel"]))
            elif st in ("booked", "scheduled"):
                appt_cmds.append(("TEXTCOLOR", (4, i), (4, i), _C["pending"]))
        appt_t.setStyle(TableStyle(appt_cmds))
        story.append(appt_t)
        story.append(Spacer(1, 14))

        # Professional performance table
        if prof_stats:
            _sub_heading(story, "Professional Performance")
            pd_data: List[List[Any]] = [
                ["Professional", "Total", "Completed", "Cancelled", f"Revenue ({currency})", "Rate"]
            ]
            for pv in sorted(prof_stats.values(), key=lambda x: -x["revenue"]):
                rate = f'{pv["completed"] / max(1, pv["total"]) * 100:.0f}%'
                pd_data.append([
                    pv["name"][:26],
                    str(pv["total"]),
                    str(pv["completed"]),
                    str(pv["cancelled"]),
                    _m(pv["revenue"]),
                    rate,
                ])
            prof_t = Table(pd_data, repeatRows=1, colWidths=[148, 48, 72, 70, 113, 72])
            prof_t.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0), _C["tbl_hdr"]),
                ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
                ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",      (0, 0), (-1, -1), 8),
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("ALIGN",         (0, 1), (0, -1), "LEFT"),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
                ("GRID",          (0, 0), (-1, -1), 0.25, _C["border"]),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, _C["tbl_alt"]]),
            ]))
            story.append(prof_t)
            story.append(Spacer(1, 18))

    # ── STORE SECTION ─────────────────────────────────────────────────
    if is_store:
        _section_header(story, "STORE SALES REPORT")

        placed     = int(order_sb.get("placed") or 0)
        confirmed  = int(order_sb.get("confirmed") or 0)
        delivered  = int(order_sb.get("delivered") or 0)
        canceled_o = int(order_sb.get("canceled") or 0)

        placed_txt = (
            f"<b>Placed/Pending: {placed}</b>" if placed > 0 else f"Placed/Pending: {placed}"
        )
        story.append(_p(
            f"{placed_txt}  |  Confirmed: {confirmed}  |  Delivered: {delivered}"
            f"  |  Cancelled: {canceled_o}"
            f"  |  <b>Revenue: {_m(store_revenue)}</b>"
            f"  |  Units Sold: {store_units:.0f}",
            _ps("osv", 9, leading=12),
        ))
        story.append(Spacer(1, 12))

        # Product sales detail
        if order_rows:
            _sub_heading(story, "Product Sales Detail")
            od: List[List[Any]] = [
                ["Product", "Qty", f"Amount ({currency})", f"Profit ({currency})", "Customer", "Status"]
            ]
            for r in order_rows[:30]:
                od.append([
                    str(r.get("product") or "")[:25],
                    f'{float(r.get("qty") or 0):.0f}',
                    _m(float(r.get("total") or 0.0)),
                    _m(float(r.get("profit") or 0.0)),
                    str(r.get("customer") or "Guest")[:20],
                    str(r.get("status") or "").capitalize(),
                ])
            od_t = _tbl(od, [140, 35, 80, 80, 110, 78])
            story.append(od_t)
            story.append(Spacer(1, 12))

        # Top products
        if top_selling:
            _sub_heading(story, "Top Products by Units Sold")
            tp: List[List[Any]] = [["#", "Product", "Units Sold", f"Revenue ({currency})"]]
            for i, r in enumerate(top_selling[:10], 1):
                tp.append([
                    str(i),
                    str(r.get("name") or r.get("sku") or "—")[:38],
                    f'{float(r.get("qty") or 0):,.0f}',
                    _m(float(r.get("revenue") or 0)),
                ])
            tp_t = Table(tp, repeatRows=1, colWidths=[28, 265, 90, 140])
            tp_cmds: List[Any] = [
                ("BACKGROUND",    (0, 0), (-1, 0), _C["tbl_hdr"]),
                ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
                ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",      (0, 0), (-1, -1), 8),
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("ALIGN",         (1, 1), (1, -1), "LEFT"),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING",   (0, 0), (-1, -1), 5),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
                ("GRID",          (0, 0), (-1, -1), 0.25, _C["border"]),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, _C["tbl_alt"]]),
                ("TEXTCOLOR",     (0, 1), (0, 3), _C["gold"]),
                ("FONTNAME",      (0, 1), (0, 3), "Helvetica-Bold"),
            ]
            tp_t.setStyle(TableStyle(tp_cmds))
            story.append(tp_t)
            story.append(Spacer(1, 12))

        # Top customers
        if top_customers:
            _sub_heading(story, "Top Customers by Spend")
            tc: List[List[Any]] = [["#", "Customer", "Orders", f"Total Spend ({currency})"]]
            for i, r in enumerate(top_customers[:5], 1):
                lbl = str(r.get("name") or r.get("phone") or "Guest")[:32]
                tc.append([str(i), lbl, str(r.get("orders") or 0), _m(float(r.get("total") or 0))])
            tc_t = Table(tc, repeatRows=1, colWidths=[28, 280, 60, 155])
            tc_t.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, 0), _C["tbl_hdr"]),
                ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
                ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",      (0, 0), (-1, -1), 8),
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("ALIGN",         (1, 1), (1, -1), "LEFT"),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING",   (0, 0), (-1, -1), 5),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
                ("GRID",          (0, 0), (-1, -1), 0.25, _C["border"]),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, _C["tbl_alt"]]),
            ]))
            story.append(tc_t)
            story.append(Spacer(1, 12))

        # Low stock alerts
        if low_stock:
            story.append(_p(
                f'<font color="#b91c1c"><b>STOCK ALERT — {len(low_stock)} item(s) need restocking</b></font>',
                _ps("alrt", 9, bold=True),
            ))
            story.append(Spacer(1, 4))
            ls: List[List[Any]] = [["Product / SKU", "Available Qty", "Alert Level"]]
            for r in low_stock[:20]:
                qty = float(r.get("available_qty") or 0)
                lvl = "CRITICAL" if qty <= 3 else "LOW"
                ls.append([str(r.get("name") or r.get("sku") or "—")[:42], f"{qty:,.0f}", lvl])
            ls_t = Table(ls, repeatRows=1, colWidths=[285, 100, 138])
            ls_cmds: List[Any] = [
                ("BACKGROUND",    (0, 0), (-1, 0), _C["tbl_hdr"]),
                ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
                ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",      (0, 0), (-1, -1), 8),
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("ALIGN",         (0, 1), (0, -1), "LEFT"),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING",   (0, 0), (-1, -1), 5),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
                ("GRID",          (0, 0), (-1, -1), 0.25, _C["border"]),
                ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, _C["tbl_alt"]]),
            ]
            for i, r in enumerate(low_stock[:20], 1):
                qty = float(r.get("available_qty") or 0)
                if qty <= 3:
                    ls_cmds += [
                        ("TEXTCOLOR", (2, i), (2, i), _C["cancel"]),
                        ("FONTNAME",  (2, i), (2, i), "Helvetica-Bold"),
                    ]
                else:
                    ls_cmds.append(("TEXTCOLOR", (2, i), (2, i), _C["pending"]))
            ls_t.setStyle(TableStyle(ls_cmds))
            story.append(ls_t)
            story.append(Spacer(1, 12))

    # ── FOOTER ────────────────────────────────────────────────────────
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_C["border"]))
    story.append(Spacer(1, 6))
    story.append(_p(
        f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')} UTC"
        f"  |  Workspace: {tenant}  |  Period: {date_label}",
        _ps("ftr", 7, align=TA_CENTER, color=_C["muted"]),
    ))

    doc.build(story)
    pdf_bytes = buf.getvalue()
    buf.close()

    if to_date and to_date != day:
        fname = f"report-{tenant}-{day.isoformat()}-to-{to_date.isoformat()}.pdf"
    else:
        fname = f"daily-{tenant}-{day.isoformat()}.pdf"
    return fname, pdf_bytes
