# app/services/core/reports_facade.py
"""
Reports facade: single entry point for report generation, listing, download, and analytics.
Routers use get_reports_service() instead of Storage or reports_store directly.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from app.services.reports import reports_store
from app.services.storage_mongo import Storage
from app.helpers.constants import APPOINTMENT_STATUS_CANCELED, APPOINTMENT_STATUS_COMPLETED, DEFAULT_TIMEZONE
from app.helpers.constants_modules import SALON_MODULE, CLINIC_MODULE


class ReportsService:
    """Facade over reports_store and Storage analytics. Use via get_reports_service() from container."""

    @staticmethod
    def run_daily_report(
            tenant: str,
            day: Optional[date] = None,
            to_day: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Build PDF, store it, then email + WhatsApp per tenant invoice_delivery prefs."""
        from zoneinfo import ZoneInfo

        if day is None:
            tdoc = Storage.get_tenant(tenant) or {}
            tz_str = (tdoc.get("tz") or DEFAULT_TIMEZONE).strip()
            try:
                tz = ZoneInfo(tz_str)
            except Exception:
                tz = ZoneInfo(DEFAULT_TIMEZONE)
            day = datetime.now(tz).date()
        doc = reports_store.generate_and_store_report(tenant, day, to_day)
        try:
            doc = reports_store.deliver_report_links(tenant, doc)
        except Exception:
            pass
        return doc

    @staticmethod
    def list_reports(
            tenant: str,
            page: int = 1,
            size: int = 50,
            from_date: Optional[date] = None,
            to_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        return reports_store.list_reports(tenant, page=page, size=size, from_date=from_date, to_date=to_date)

    @staticmethod
    def get_report_doc(tenant: str, date_str: str) -> Optional[Dict[str, Any]]:
        return reports_store.get_report_doc(tenant, date_str)

    @staticmethod
    def ensure_report_downloadable(tenant: str, date_str: str) -> Optional[Dict[str, Any]]:
        return reports_store.ensure_report_downloadable(tenant, date_str)

    @staticmethod
    def resolve_report_download(doc: Dict[str, Any]):
        return reports_store.resolve_report_download(doc)

    @staticmethod
    def period_summary(
            tenant: str,
            days: Optional[int] = None,
            from_date: Optional[date] = None,
            to_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Single aggregated view for the Reports UI: KPIs, plain-language highlights, optional order status mix."""
        from app.helpers.date_utils import resolve_date_window
        from app.helpers.money_format import format_money, tenant_currency

        tdoc = Storage.get_tenant_settings(tenant) or {}
        currency = tenant_currency(tdoc)
        modules = tdoc.get("modules") or []
        is_store = "store" in modules
        is_service = ("salon" in modules) or ("clinic" in modules)

        sales = Storage.sales_timeseries(tenant=tenant, days=days, from_date=from_date, to_date=to_date)
        cust = Storage.customers_timeseries(tenant=tenant, days=days, from_date=from_date, to_date=to_date)

        total_revenue = sum(float(d.get("total_revenue") or 0) for d in sales)
        store_revenue = sum(float(d.get("store_revenue") or 0) for d in sales)
        service_revenue = sum(float(d.get("service_revenue") or 0) for d in sales)
        orders_count = sum(int(d.get("orders_count") or 0) for d in sales)
        units_sold = sum(float(d.get("units") or 0) for d in sales)
        appointments_count = sum(int(d.get("appts_count") or 0) for d in sales)
        new_customers = sum(int(d.get("new_customers") or 0) for d in cust)
        returning_customers = sum(int(d.get("returning_customers") or 0) for d in cust)

        order_status_breakdown: List[Dict[str, Any]] = []
        if is_store:
            order_status_breakdown = Storage.orders_by_status(
                tenant=tenant, days=days, from_date=from_date, to_date=to_date,
            )

        if from_date and to_date:
            period_from = from_date.isoformat()
            period_to = to_date.isoformat()
            label = f"{period_from} → {period_to}"
        else:
            roll_days = days if days is not None else 30
            _ws, _we, dd = resolve_date_window(roll_days, None, None, min_days=7, max_days=120)
            period_from = _ws.date().isoformat()
            period_to = _we.date().isoformat()
            label = f"Last {dd} days"

        highlights: List[str] = []
        if total_revenue > 0:
            highlights.append(
                f"Total revenue in this period: {format_money(total_revenue, currency)} (store + services).",
            )
        elif is_store or is_service:
            highlights.append("No revenue recorded in this period yet.")
        if is_store and orders_count:
            highlights.append(f"{orders_count} store order(s); {units_sold:,.0f} units sold (non-canceled).")
        if is_service and appointments_count:
            highlights.append(
                f"{appointments_count} appointment row(s) in the period (booked + completed, by creation date).",
            )
        if new_customers or returning_customers:
            highlights.append(
                f"Customer signals: {new_customers} new and {returning_customers} returning (daily roll-up).",
            )
        if is_store and order_status_breakdown:
            top = order_status_breakdown[0]
            highlights.append(
                f"Most common order status: {str(top.get('status') or '—').replace('_', ' ')} ({top.get('count', 0)}).",
            )
        if not highlights:
            highlights.append("No activity in this window — try a wider date range.")

        return {
            "tenant": tenant,
            "currency": currency,
            "modules": modules,
            "period": {"from": period_from, "to": period_to, "label": label},
            "kpis": {
                "total_revenue": round(total_revenue, 2),
                "store_revenue": round(store_revenue, 2),
                "service_revenue": round(service_revenue, 2),
                "orders_count": int(orders_count),
                "units_sold": round(units_sold, 2),
                "appointments_count": int(appointments_count),
                "new_customers": int(new_customers),
                "returning_customers": int(returning_customers),
            },
            "highlights": highlights[:8],
            "order_status_breakdown": order_status_breakdown[:10],
        }

    @staticmethod
    def sales_timeseries(
            tenant: str,
            days: Optional[int] = None,
            interval: str = "day",
            from_date: Optional[date] = None,
            to_date: Optional[date] = None,
    ) -> Any:
        return Storage.sales_timeseries(tenant=tenant, days=days, interval=interval, from_date=from_date,
                                        to_date=to_date)

    @staticmethod
    def orders_by_status(
            tenant: str,
            days: Optional[int] = None,
            from_date: Optional[date] = None,
            to_date: Optional[date] = None,
    ) -> Any:
        return Storage.orders_by_status(tenant=tenant, days=days, from_date=from_date, to_date=to_date)

    @staticmethod
    def category_mix(
            tenant: str,
            days: Optional[int] = None,
            from_date: Optional[date] = None,
            to_date: Optional[date] = None,
    ) -> Any:
        return Storage.category_mix(tenant=tenant, days=days, from_date=from_date, to_date=to_date)

    @staticmethod
    def professional_performance(
            tenant: str,
            days: Optional[int] = None,
            from_date: Optional[date] = None,
            to_date: Optional[date] = None,
    ) -> Any:
        return Storage.professional_performance(tenant=tenant, days=days, from_date=from_date, to_date=to_date)

    @staticmethod
    def customers_timeseries(
            tenant: str,
            days: Optional[int] = None,
            from_date: Optional[date] = None,
            to_date: Optional[date] = None,
    ) -> Any:
        return Storage.customers_timeseries(tenant=tenant, days=days, from_date=from_date, to_date=to_date)

    @staticmethod
    def top_sellers(tenant: str, days: int = 30, top: int = 5) -> Any:
        return Storage.top_sellers(tenant=tenant, days=days, top=top)

    @staticmethod
    def forecast_low_stock(
            tenant: str,
            days: int = 30,
            lead_time: int = 3,
            safety_days: int = 2,
            top: int = 5,
    ) -> Any:
        return Storage.forecast_low_stock(tenant=tenant, days=days, lead_time=lead_time, safety_days=safety_days,
                                          top=top)

    @staticmethod
    async def get_tenant_analytics(tenant: str) -> Dict[str, Any]:
        """Compute analytics for a tenant: total appointments, cancellations, revenue (appointments + store)."""
        from app.core.container import get_appointment_service, get_tenant_service
        appts: List[Dict[str, Any]] = await get_appointment_service().list_appointments(tenant=tenant)
        cancellations = sum(1 for a in appts if a.get("status") == APPOINTMENT_STATUS_CANCELED)
        revenue = sum(float(a.get("price", 0)) for a in appts if a.get("status") == APPOINTMENT_STATUS_COMPLETED)
        tdoc = get_tenant_service().get_tenant_settings(tenant) or {}
        if "store" in (tdoc.get("modules") or []):
            ts = Storage.sales_timeseries(tenant=tenant, days=30)
            revenue += sum(float(d.get("store_revenue", 0)) for d in (ts or []))
        return {
            "tenant": tenant,
            "total_appointments": len(appts),
            "cancellations": cancellations,
            "revenue": revenue,
        }

    @staticmethod
    async def get_dashboard_summary(tenant: str) -> Dict[str, Any]:
        """Build dashboard summary for a tenant (modules, sales, orders, no_show count, etc.)."""
        from app.core.container import get_tenant_service
        from app.services.store.facade import get_store_facade
        tdoc = get_tenant_service().get_tenant_settings(tenant) or {}
        modules = tdoc.get("modules") or []
        capabilities = [str(c).lower() for c in (tdoc.get("capabilities") or [])]
        sales = Storage.sales_timeseries(tenant=tenant, days=30)
        summary = {
            "tenant": tenant,
            "modules": modules,
            "capabilities": capabilities,
            "sales_30d": sales or [],
            "total_revenue_30d": sum(float(d.get("total_revenue", 0)) for d in (sales or [])),
        }
        if SALON_MODULE in modules or CLINIC_MODULE in modules:
            summary["professional_performance"] = Storage.professional_performance(tenant=tenant, days=30)
        if "store" in modules:
            summary["top_sellers"] = Storage.top_sellers(tenant=tenant, days=30, top=5)
            low = Storage.forecast_low_stock(tenant=tenant, days=30, top=5)
            summary["low_stock"] = low if isinstance(low, list) else (
                low.get("items", []) if isinstance(low, dict) else [])
            orders_res = get_store_facade().orders.list_orders(tenant=tenant, statuses=None, page=1, size=15,
                                                               search=None)
            summary["recent_orders"] = orders_res.get("items") or []
        from app.services.ai.feature_gate import is_ai_capability_enabled
        from app.helpers.constants_capabilities import CAP_AI_NO_SHOW
        if (SALON_MODULE in modules or CLINIC_MODULE in modules) and is_ai_capability_enabled(tenant, CAP_AI_NO_SHOW):
            try:
                from app.services.salon.appointments.no_show_block_service import list_blocked
                summary["no_show_blocked_count"] = len(list_blocked(tenant))
            except Exception:
                summary["no_show_blocked_count"] = 0
        return summary

    @staticmethod
    def run_daily_reports_all_tenants() -> List[Dict[str, Any]]:
        """Run daily report (generate + deliver) for every active tenant. Uses each tenant's local today. For admin/cron."""
        from zoneinfo import ZoneInfo
        import logging

        log = logging.getLogger(__name__)
        try:
            tenants = Storage.list_tenants_basic()
        except Exception as e:
            log.exception("run_daily_reports_all_tenants: cannot list tenants: %s", e)
            return [{"tenant": "*", "status": "error", "error": str(e)}]

        results: List[Dict[str, Any]] = []
        for t in tenants:
            tenant_id = t.get("tenant") or t.get("_id")
            if not tenant_id:
                continue
            if not bool(t.get("active", True)):
                results.append({"tenant": tenant_id, "status": "skipped", "reason": "inactive"})
                continue
            tz_str = (t.get("tz") or DEFAULT_TIMEZONE).strip()
            try:
                tz = ZoneInfo(tz_str)
            except Exception:
                tz = ZoneInfo(DEFAULT_TIMEZONE)
            today_local = datetime.now(tz).date()
            try:
                doc = ReportsService.run_daily_report(tenant_id, day=today_local)
                results.append({
                    "tenant": tenant_id,
                    "status": "ok",
                    "date": str(today_local),
                    "sent_via": list(doc.get("sent_via") or []),
                })
                log.info("Daily report run for tenant=%s date=%s", tenant_id, today_local)
            except Exception as e:
                results.append({"tenant": tenant_id, "status": "error", "error": str(e)})
                log.warning("Daily report failed for tenant=%s: %s", tenant_id, e)
        return results
