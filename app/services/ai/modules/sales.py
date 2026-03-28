# services/ai/modules/sales.py

import datetime as dt
from typing import Dict, List, Any
from app.helpers.date_utils import resolve_date_window, utcnow
from app.helpers.tools import to_float, resolve_product_names
from app.services.ai.helpers.config import AI_DEFAULTS


class SalesService:
    """
    Provides sales analytics:
    - Top sellers
    - Sales timeseries (orders + appointments)
    """

    def __init__(self, order_repo, product_repo, appt_repo):
        """
        Args:
            order_repo: OrderRepository
            product_repo: ProductRepository
            appt_repo: AppointmentRepository
        """
        self.order_repo = order_repo
        self.product_repo = product_repo
        self.appt_repo = appt_repo

    # ----------------------------------------------------------------------
    # TOP SELLERS
    # ----------------------------------------------------------------------

    def top_sellers(
            self,
            tenant: str,
            days: int = None,
            top: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Aggregate top sellers by quantity and revenue.
        """
        if not tenant:
            raise ValueError("tenant is required")

        cfg = AI_DEFAULTS["sales"]
        days = days or cfg["timeseries_days"]
        top = top or cfg["top_sellers"]

        # Resolve date window
        window_start, _, _ = resolve_date_window(days)

        # Fetch orders
        orders = self.order_repo.list_by_tenant(
            tenant,
            status_ne="canceled",
            since=window_start,
        )

        # Aggregate per SKU
        agg: Dict[str, Dict[str, float]] = {}

        for order_doc in orders:
            for item in (order_doc.items or []):
                sku = str(item.get("sku") or "").strip()
                qty = to_float(item.get("qty"))
                price = to_float(item.get("price_snapshot"))

                if not sku or qty <= 0:
                    continue

                row = agg.setdefault(sku, {"sku": sku, "qty": 0.0, "revenue": 0.0})
                row["qty"] += qty
                row["revenue"] += qty * price

        if not agg:
            return []

        skus = list(agg.keys())

        # Resolve product names
        name_map = resolve_product_names(tenant, skus, self.product_repo)

        # Final formatting
        items = []
        for sku, row in agg.items():
            items.append({
                "sku": sku,
                "name": name_map.get(sku, sku),
                "qty": round(row["qty"], 2),
                "revenue": round(row["revenue"], 2),
            })

        # Sort by qty desc, then revenue desc
        items.sort(key=lambda x: (-x["qty"], -x["revenue"]))

        return items[:top]

    # ----------------------------------------------------------------------
    # SALES TIMESERIES
    # ----------------------------------------------------------------------

    def sales_timeseries(
            self,
            tenant: str,
            days: int = None,
            from_date: dt.date = None,
            to_date: dt.date = None,
    ) -> List[Dict[str, Any]]:
        """
        Return per-day totals for orders and appointments (excluding canceled).
        Supports:
        - store module (orders)
        - salon/clinic module (appointments)
        """
        if not tenant:
            raise ValueError("tenant is required")

        # Resolve date window
        window_start, window_end, days_diff = resolve_date_window(
            days,
            from_date,
            to_date,
        )

        # Determine tenant modules
        from app.services.core.tenant_service import TenantService
        tenant_doc = TenantService.get_tenant_settings(tenant) or {}
        modules = tenant_doc.get("modules") or []

        is_store = "store" in modules
        is_service = ("salon" in modules) or ("clinic" in modules)

        buckets: Dict[str, Dict[str, float]] = {}

        # ------------------------------
        # STORE ORDERS
        # ------------------------------
        if is_store:
            cursor = self.order_repo.get_collection().find(
                {
                    "tenant": tenant,
                    "status": {"$ne": "canceled"},
                    "created_at": {"$gte": window_start, "$lte": window_end},
                },
                {"created_at": 1, "items": 1, "totals": 1},
            )

            for doc in cursor:
                created = doc.get("created_at") or utcnow()
                key = created.date().isoformat()

                bucket = buckets.setdefault(
                    key,
                    {
                        "orders_count": 0.0,
                        "units": 0.0,
                        "store_revenue": 0.0,
                        "appts_count": 0.0,
                        "service_revenue": 0.0,
                    },
                )

                bucket["orders_count"] += 1
                bucket["store_revenue"] += to_float(doc.get("totals", {}).get("subtotal"))

                for item in (doc.get("items") or []):
                    bucket["units"] += to_float(item.get("qty"))

        # ------------------------------
        # APPOINTMENTS (SALON/CLINIC)
        # ------------------------------
        if is_service:
            cursor = self.appt_repo.get_collection().find(
                {
                    "tenant": tenant,
                    "status": {"$in": ["booked", "completed"]},
                    "created_at": {"$gte": window_start, "$lte": window_end},
                },
                {"created_at": 1, "price": 1, "status": 1},
            )

            for doc in cursor:
                created = doc.get("created_at") or utcnow()
                key = created.date().isoformat()

                bucket = buckets.setdefault(
                    key,
                    {
                        "orders_count": 0.0,
                        "units": 0.0,
                        "store_revenue": 0.0,
                        "appts_count": 0.0,
                        "service_revenue": 0.0,
                    },
                )

                bucket["appts_count"] += 1
                if doc.get("status") == "completed":
                    bucket["service_revenue"] += to_float(doc.get("price"))

        # ------------------------------
        # Build output timeseries
        # ------------------------------
        out: List[Dict[str, Any]] = []
        end_date = to_date or utcnow().date()

        for i in range(days_diff, -1, -1):
            d = (end_date - dt.timedelta(days=i)).isoformat()
            b = buckets.get(d) or {
                "orders_count": 0,
                "units": 0,
                "store_revenue": 0,
                "appts_count": 0,
                "service_revenue": 0,
            }

            out.append({
                "date": d,
                "orders_count": int(b["orders_count"]),
                "units": round(b["units"], 2),
                "store_revenue": round(b["store_revenue"], 2),
                "appts_count": int(b["appts_count"]),
                "service_revenue": round(b["service_revenue"], 2),
                "total_revenue": round(b["store_revenue"] + b["service_revenue"], 2),
            })

        return out
