# services/ai/modules/forecasting.py

import datetime as dt
from typing import Dict, List, Any
from app.helpers.date_utils import resolve_date_window, utcnow
from app.helpers.tools import to_float
from app.helpers.tools import resolve_product_names
from app.services.ai.helpers.inventory_utils import get_inventory_map
from app.services.ai.helpers.config import AI_DEFAULTS


class ForecastingService:
    """
    Provides forecasting utilities:
    - Low stock forecast
    - Sales forecast
    """

    def __init__(self, order_repo, product_repo, inventory_repo):
        self.order_repo = order_repo
        self.product_repo = product_repo
        self.inventory_repo = inventory_repo

    # ----------------------------------------------------------------------
    # LOW STOCK FORECAST
    # ----------------------------------------------------------------------

    def forecast_low_stock(
            self,
            tenant: str,
            days: int = None,
            lead_time: int = None,
            safety_days: int = None,
            top: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Compute low-stock forecast using moving-average demand.
        """
        if not tenant:
            raise ValueError("tenant is required")

        cfg = AI_DEFAULTS["forecast"]

        days = days or cfg["max_days"]
        lead_time = lead_time if lead_time is not None else cfg["lead_time"]
        safety_days = safety_days if safety_days is not None else cfg["safety_days"]
        top = top or cfg["top"]

        # Resolve date window
        window_start, _, _ = resolve_date_window(
            days,
            min_days=cfg["min_days"],
            max_days=cfg["max_days"],
        )

        # Fetch orders
        orders = self.order_repo.list_by_tenant(
            tenant,
            status_ne="canceled",
            since=window_start,
        )

        # Aggregate demand per SKU
        demand: Dict[str, float] = {}
        for order_doc in orders:
            for item in (order_doc.items or []):
                sku = str(item.get("sku") or "").strip()
                qty = to_float(item.get("qty"))
                if sku and qty > 0:
                    demand[sku] = demand.get(sku, 0.0) + qty

        skus = list(demand.keys())

        # Inventory lookup
        inv_map = get_inventory_map(tenant, skus, self.inventory_repo)

        # Product names
        name_map = resolve_product_names(tenant, skus, self.product_repo)

        # Build forecast rows
        results: List[Dict[str, Any]] = []
        for sku, total_qty in demand.items():
            daily = total_qty / days
            available = inv_map.get(sku, 0.0)

            days_to_stockout = (available / daily) if daily > 0 else float("inf")
            target_stock = daily * (lead_time + safety_days)
            reorder_qty = max(0.0, target_stock - available)

            results.append({
                "sku": sku,
                "name": name_map.get(sku, sku),
                "available_qty": round(available, 2),
                "daily_demand": round(daily, 3),
                "days_to_stockout": (
                    9999 if days_to_stockout == float("inf") else round(days_to_stockout, 1)
                ),
                "suggested_reorder_qty": round(reorder_qty, 2),
            })

        # Sort by urgency
        results.sort(key=lambda r: (r["days_to_stockout"], -r["daily_demand"]))

        return results[:top]

    # ----------------------------------------------------------------------
    # SALES FORECAST
    # ----------------------------------------------------------------------

    def sales_forecast(
            self,
            tenant: str,
            days: int = 30,
            horizon: int = 14,
    ) -> Dict[str, Any]:
        """
        Naive sales forecast using moving-average demand.
        """
        if not tenant:
            raise ValueError("tenant is required")

        days = max(7, min(120, int(days or 30)))
        horizon = max(1, min(90, int(horizon or 14)))

        window_start = utcnow() - dt.timedelta(days=days)

        total_qty = 0.0
        total_rev = 0.0

        orders = self.order_repo.list_by_tenant(
            tenant,
            status_ne="canceled",
            since=window_start,
        )

        for order_doc in orders:
            for item in (order_doc.items or []):
                qty = to_float(item.get("qty"))
                price = to_float(item.get("price_snapshot"))
                total_qty += qty
                total_rev += qty * price

        daily_demand = total_qty / days if days > 0 else 0.0
        avg_unit_price = (total_rev / total_qty) if total_qty > 0 else 0.0

        # Build forecast horizon
        items = []
        start_date = utcnow().date()

        for i in range(1, horizon + 1):
            d = (start_date + dt.timedelta(days=i)).isoformat()
            items.append({
                "date": d,
                "demand_units": round(daily_demand, 2),
                "revenue_estimate": round(daily_demand * avg_unit_price, 2),
            })

        return {
            "items": items,
            "days": days,
            "horizon": horizon,
            "daily_demand": round(daily_demand, 3),
            "avg_unit_price": round(avg_unit_price, 2),
        }
