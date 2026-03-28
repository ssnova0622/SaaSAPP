# app/services/core/reports_facade.py
"""
Reports facade: single entry point for report generation, listing, download, and analytics.
Routers use get_reports_service() instead of Storage or reports_store directly.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from app.services.reports import reports_store
from app.services.storage_mongo import Storage
from app.helpers.constants import APPOINTMENT_STATUS_CANCELED, APPOINTMENT_STATUS_COMPLETED
from app.helpers.constants_modules import SALON_MODULE, CLINIC_MODULE


class ReportsService:
    """Facade over reports_store and Storage analytics. Use via get_reports_service() from container."""

    @staticmethod
    def run_daily_report(
            tenant: str,
            day: Optional[date] = None,
            to_day: Optional[date] = None,
    ) -> Dict[str, Any]:
        doc = reports_store.generate_and_store_report(tenant, day or date.today(), to_day)
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
    def resolve_report_download(doc: Dict[str, Any]):
        return reports_store.resolve_report_download(doc)

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
        """Run daily report (generate + deliver) for every tenant. Uses each tenant's local today. For cron."""
        from datetime import datetime as dt_now
        from zoneinfo import ZoneInfo
        from app.helpers.constants import DEFAULT_TIMEZONE
        from app.services import reports_store
        import logging
        log = logging.getLogger(__name__)
        tenants = Storage.list_tenants_basic()
        results = []
        for t in tenants:
            tenant_id = t.get("tenant") or t.get("_id")
            if not tenant_id:
                continue
            tz_str = (t.get("tz") or DEFAULT_TIMEZONE).strip()
            try:
                tz = ZoneInfo(tz_str)
            except Exception:
                tz = ZoneInfo(DEFAULT_TIMEZONE)
            today_local = dt_now.now(tz).date()
            try:
                doc = reports_store.generate_and_store_report(tenant_id, today_local)
                reports_store.deliver_report_links(tenant_id, doc)
                results.append({"tenant": tenant_id, "status": "ok", "date": str(today_local)})
                log.info("Daily report run for tenant=%s date=%s", tenant_id, today_local)
            except Exception as e:
                results.append({"tenant": tenant_id, "status": "error", "error": str(e)})
                log.warning("Daily report failed for tenant=%s: %s", tenant_id, e)
        return results
