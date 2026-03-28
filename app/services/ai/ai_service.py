# services/ai/ai_service.py

from typing import Dict, Any, List, Optional, Tuple
import datetime as dt

from app.helpers.tools import uuid4
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.cart_repository import CartRepository

from app.services.db import get_db

# AI Modules
from app.services.ai.modules.forecasting import ForecastingService
from app.services.ai.modules.sales import SalesService
from app.services.ai.modules.customers import CustomersService
from app.services.ai.modules.categories import CategoriesService
from app.services.ai.modules.carts import CartRecoveryService
from app.services.ai.modules.professionals import ProfessionalsService
from app.helpers.date_utils import resolve_date_window, utcnow

from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.customer_repository import CustomerRepository


class AiService:
    """
    Thin orchestrator for all AI analytics modules.
    Contains no business logic — only delegates to domain modules.
    """

    def __init__(self):
        # Repositories
        self.order_repo = OrderRepository()
        self.product_repo = ProductRepository()
        self.inventory_repo = InventoryRepository()
        self.cart_repo = CartRepository()
        self.appt_repo = AppointmentRepository()
        self.event_repo = AnalyticsRepository()
        self.cust_repo = CustomerRepository()

        # Domain modules
        self.forecasting = ForecastingService(
            order_repo=self.order_repo,
            product_repo=self.product_repo,
            inventory_repo=self.inventory_repo,
        )

        self.sales = SalesService(
            order_repo=self.order_repo,
            product_repo=self.product_repo,
            appt_repo=self.appt_repo,
        )

        self.customers = CustomersService(
            customer_repo=self.cust_repo,
            order_repo=self.order_repo,
        )

        self.categories = CategoriesService(
            order_repo=self.order_repo,
            product_repo=self.product_repo,
        )

        self.carts = CartRecoveryService(
            cart_repo=self.cart_repo,
            product_repo=self.product_repo,
        )

        self.professionals = ProfessionalsService(
            appt_repo=self.appt_repo,
        )

    # ----------------------------------------------------------------------
    # INTERNAL COLLECTION HELPERS
    # ----------------------------------------------------------------------

    def _collections(self):
        """
        Returns (tenant_collection, product_collection, appointments_collection)
        for modules that need raw DB access.
        """
        db = get_db()
        return (
            db.get_collection("tenants"),
            db.get_collection("products"),
            db.get_collection("appointments"),
        )

    def _customers_collection(self):
        return get_db().get_collection("customers")

    # ----------------------------------------------------------------------
    # PUBLIC API — SUMMARY
    # ----------------------------------------------------------------------

    def predictions_summary(self, tenant: str, days: int = 30) -> Dict[str, Any]:
        """
        Aggregate summary for dashboard.
        """
        low_stock = self.forecast_low_stock(tenant, top=10)
        top_sellers = self.top_sellers(tenant, days=days, top=5)

        # Abandoned carts in last 24h
        since_24h = utcnow() - dt.timedelta(hours=24)
        abandoned_count = self.cart_repo.count_abandoned(tenant, since_24h)

        return {
            "tenant": tenant,
            "days": days,
            "generated_at": utcnow().isoformat(),
            "low_stock_count": len(low_stock),
            "predicted_oos_next_7d": len([i for i in low_stock if i["days_to_stockout"] <= 7]),
            "top_seller_skus": [i["sku"] for i in top_sellers],
            "abandoned_carts_24h": abandoned_count,
            "anomaly_alerts": 0,
        }

    # ----------------------------------------------------------------------
    # PUBLIC API — FORECASTING
    # ----------------------------------------------------------------------

    def forecast_low_stock(
            self,
            tenant: str,
            days: int = None,
            lead_time: int = None,
            safety_days: int = None,
            top: int = None,
    ):
        return self.forecasting.forecast_low_stock(
            tenant=tenant,
            days=days,
            lead_time=lead_time,
            safety_days=safety_days,
            top=top,
        )

    def sales_forecast(
            self,
            tenant: str,
            days: int = 30,
            horizon: int = 14,
    ):
        return self.forecasting.sales_forecast(
            tenant=tenant,
            days=days,
            horizon=horizon,
        )

    # ----------------------------------------------------------------------
    # PUBLIC API — SALES
    # ----------------------------------------------------------------------

    def top_sellers(
            self,
            tenant: str,
            days: int = None,
            top: int = None,
    ):
        return self.sales.top_sellers(
            tenant=tenant,
            days=days,
            top=top,
        )

    def sales_timeseries(
            self,
            tenant: str,
            days: int = None,
            from_date: dt.date = None,
            to_date: dt.date = None,
    ):
        return self.sales.sales_timeseries(
            tenant=tenant,
            days=days,
            from_date=from_date,
            to_date=to_date,
        )

    def orders_by_status(
            self,
            tenant: str,
            days: int = None,
            from_date: dt.date = None,
            to_date: dt.date = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregate orders by status over a window.
        """
        if not tenant:
            raise ValueError("tenant is required")

        # Resolve date window
        window_start, window_end, days_diff = resolve_date_window(
            days or 30,
            from_date,
            to_date,
        )

        buckets: Dict[str, Dict[str, int]] = {}

        cursor = self.order_repo.get_collection().find(
            {
                "tenant": tenant,
                "created_at": {"$gte": window_start, "$lte": window_end},
            },
            {"created_at": 1, "status": 1},
        )

        for doc in cursor:
            created = doc.get("created_at") or utcnow()
            key = created.date().isoformat()
            status = str(doc.get("status") or "unknown")

            bucket = buckets.setdefault(key, {})
            bucket[status] = bucket.get(status, 0) + 1

        # Build output
        out: List[Dict[str, Any]] = []
        end_date = to_date or utcnow().date()

        for i in range(days_diff, -1, -1):
            d = (end_date - dt.timedelta(days=i)).isoformat()
            b = buckets.get(d) or {}
            out.append({"date": d, "statuses": b})

        return out

    # ----------------------------------------------------------------------
    # PUBLIC API — CUSTOMERS
    # ----------------------------------------------------------------------

    def customers_timeseries(
            self,
            tenant: str,
            days: int = None,
            from_date: dt.date = None,
            to_date: dt.date = None,
    ):
        return self.customers.customers_timeseries(
            tenant=tenant,
            days=days,
            from_date=from_date,
            to_date=to_date,
        )

    # ----------------------------------------------------------------------
    # PUBLIC API — CATEGORIES
    # ----------------------------------------------------------------------

    def category_mix(
            self,
            tenant: str,
            days: int = None,
            from_date: dt.date = None,
            to_date: dt.date = None,
    ):
        return self.categories.category_mix(
            tenant=tenant,
            days=days,
            from_date=from_date,
            to_date=to_date,
        )

    # ----------------------------------------------------------------------
    # PUBLIC API — CARTS
    # ----------------------------------------------------------------------

    def cart_recovery(
            self,
            tenant: str,
            window_hours: int = None,
            top: int = None,
    ):
        return self.carts.cart_recovery(
            tenant=tenant,
            window_hours=window_hours,
            top=top,
        )

    # ----------------------------------------------------------------------
    # PUBLIC API — PROFESSIONALS (SYNC + ASYNC)
    # ----------------------------------------------------------------------

    def professional_performance(
            self,
            tenant: str,
            days: int = None,
            from_date: dt.date = None,
            to_date: dt.date = None,
    ):
        return self.professionals.professional_performance(
            tenant=tenant,
            days=days,
            from_date=from_date,
            to_date=to_date,
        )

    async def list_available_slots_for_first_professional(
            self,
            tenant: str,
    ):
        return await self.professionals.list_available_slots_for_first_professional(
            tenant=tenant
        )

    async def list_times_for_professional_label(
            self,
            tenant: str,
            professional: str,
            limit: int = 10,
    ):
        return await self.professionals.list_times_for_professional_label(
            tenant=tenant,
            professional=professional,
            limit=limit,
        )

    async def recommend_slots(
            self,
            tenant: str,
            professional: Optional[str] = None,
            top: int = 3,
    ):
        return await self.professionals.recommend_slots(
            tenant=tenant,
            professional=professional,
            top=top,
        )

    # ----------------------------------------------------------------------
    # GENERIC EVENT LOGGING
    # ----------------------------------------------------------------------

    def insert_event(self, tenant: str, data: Dict[str, Any]):
        """
        Minimal analytics event logging.
        """
        if not tenant:
            raise ValueError("tenant is required")

        ev_type = str((data or {}).get("type") or "").strip()
        if not ev_type:
            raise ValueError("event 'type' is required")

        ts = data.get("ts")
        if not isinstance(ts, (int, float)):
            ts = utcnow().timestamp()

        from app.repositories.analytics_repository import AnalyticsEvent
        event = AnalyticsEvent(
            tenant=tenant,
            id=uuid4(),
            type=ev_type,
            ts=float(ts),
            data=data.get("data") or {},
            created_at=utcnow(),
        )

        self.event_repo.insert_one(event)
        return event.dict()
