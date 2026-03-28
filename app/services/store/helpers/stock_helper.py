# app/services/store/helpers/stock_helper.py
from __future__ import annotations

from typing import Dict, List, Any, Optional

from app.services.store.inventory_service import InventoryService
from app.services.store.helpers.validation_helper import StoreValidationError
from app.services.store.helpers.unit_conversion_helper import UnitConversionHelper


class StockHelper:
    """
    Centralized stock logic used by checkout, orders, and inventory.
    Quantities are aggregated in product base unit so stock checks match inventory (stored in base unit).
    """

    # ---------------- Aggregation ----------------

    @staticmethod
    def aggregate_items(
        items: List[Dict[str, Any]],
        tenant: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Convert list of items → {sku: total_qty in product base unit}.
        If tenant is provided, each item's qty is converted from its unit to the product's base unit
        (e.g. 250 grams → 0.25 kg) so the result is comparable to inventory available_qty.
        """
        agg: Dict[str, float] = {}
        if not items:
            return agg

        get_product = None
        if tenant:
            from app.services.store.products_service import ProductService
            get_product = lambda sku: ProductService.get_product_by_sku(tenant, sku)

        for it in items or []:
            # Skip manual-entry items: no availability check or stock deduction
            if it.get("manual"):
                continue
            sku = str(it.get("sku") or "").strip()
            if not sku:
                continue
            qty = float(it.get("qty", 0))
            if qty <= 0:
                continue

            if get_product:
                prod = get_product(sku)
                if prod:
                    base_unit = prod.get("unit")
                    conversions = prod.get("unit_conversions") or []
                    item_unit = it.get("unit")
                    qty = UnitConversionHelper.convert_qty_to_base(
                        qty, item_unit, base_unit, conversions
                    )

            agg[sku] = agg.get(sku, 0.0) + qty
        return agg

    # ---------------- Diffs ----------------

    @staticmethod
    def compute_diffs(old: Dict[str, float], new: Dict[str, float]) -> Dict[str, float]:
        """
        Compute quantity differences between old and new item sets.
        Positive delta = more stock needed.
        Negative delta = stock should be returned.
        """
        diffs = {}
        all_skus = set(old.keys()) | set(new.keys())
        for sku in all_skus:
            diff = new.get(sku, 0.0) - old.get(sku, 0.0)
            if abs(diff) > 0.0001:
                diffs[sku] = diff
        return diffs

    # ---------------- Validation ----------------

    @staticmethod
    def ensure_stock_available(tenant: str, sku: str, required_qty: float):
        inv = InventoryService.get_inventory(tenant, sku)
        available = float(inv.get("available_qty", 0.0))
        if available < required_qty:
            raise StoreValidationError(
                f"Insufficient stock for SKU '{sku}' (have {available}, need {required_qty})"
            )

    # ---------------- Application ----------------

    @staticmethod
    def apply_stock_delta(tenant: str, sku: str, delta: float, reason: str):
        """
        Apply stock change (+delta or -delta) with validation.
        """
        if delta > 0:
            # returning stock
            return InventoryService.adjust_stock(
                tenant=tenant,
                sku=sku,
                delta=delta,
                reason=reason,
            )

        if delta < 0:
            # consuming stock
            StockHelper.ensure_stock_available(tenant, sku, abs(delta))
            return InventoryService.adjust_stock(
                tenant=tenant,
                sku=sku,
                delta=delta,
                reason=reason,
            )

        return InventoryService.get_inventory(tenant, sku)
