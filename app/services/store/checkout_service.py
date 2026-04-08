# app/services/store/checkout_service.py
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional, List

from app.helpers.date_utils import utcnow
from app.services.db import get_db
from app.services.store.helpers.stock_helper import StockHelper
from app.services.core.tenant_service import TenantService
from app.services.payments.payments import get_payments_provider
from app.services.store.helpers.price_helper import PriceHelper
from app.services.store.helpers.validation_helper import StoreValidationError
from app.services.store.cart_service import CartService
from app.helpers.phone_util import PhoneUtil
from app.services.store.helpers.constants import (
    PAYMENT_STATUS_PENDING,
    PAYMENT_METHOD_COD,
    PAYMENT_METHOD_ONLINE,
)


class CheckoutService:
    @staticmethod
    def _carts():
        return get_db().get_collection("carts")

    @staticmethod
    def _orders():
        return get_db().get_collection("orders")

    # ---------------- Checkout ----------------

    @classmethod
    def checkout(
            cls,
            tenant: str,
            phone: str,
            fulfillment_mode: str,
            address: Optional[Dict[str, Any]],
            payment_method: str,
            discount_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Creates an order from the cart.
        Deducts inventory.
        Optionally applies cart-level discount (percent or amount).
        Creates payment intent if needed (amount = grand_total after discount).
        """

        tcfg = TenantService.get_tenant_settings(tenant) or {}
        cls._validate_fulfillment(tcfg, fulfillment_mode, address)

        carts = cls._carts()
        orders = cls._orders()

        dial = TenantService._get_tenant_country_code(tenant) or PhoneUtil.DEFAULT_DIAL_DIGITS
        pn = PhoneUtil.prepare_storage(str(phone).strip(), dial)
        if not pn:
            raise StoreValidationError("Invalid phone")
        cart = CartService._resolve_cart_doc(carts, tenant, pn)
        if not cart or not cart.get("items"):
            raise StoreValidationError("Cart is empty")

        items = cart["items"]
        subtotal = PriceHelper.calc_subtotal(items)
        discount_amount = 0.0
        if discount_info and isinstance(discount_info, dict):
            t = (discount_info.get("type") or "").lower()
            v = float(discount_info.get("value") or 0)
            if t == "percent" and 0 <= v <= 100:
                discount_amount = round(subtotal * (v / 100.0), 2)
            elif t == "amount" and v >= 0:
                discount_amount = min(round(float(v), 2), subtotal)
        grand_total = max(0.0, round(subtotal - discount_amount, 2))
        now = utcnow()

        # Aggregate quantities in product base unit (e.g. 200 gram → 0.2 kg) then deduct stock once
        items_agg = StockHelper.aggregate_items(items, tenant=tenant)
        for sku, qty in items_agg.items():
            StockHelper.apply_stock_delta(tenant=tenant, sku=sku, delta=-qty, reason="checkout")

        # Create order
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        totals = {"subtotal": subtotal, "grand_total": grand_total}
        if discount_amount > 0:
            totals["discount"] = discount_amount
        order_doc = {
            "tenant": tenant,
            "id": order_id,
            "customer": {"phone": phone, "name": cart.get("customer_name")},
            "items": items,
            "totals": totals,
            "discount_info": (dict(discount_info) if discount_amount > 0 and discount_info and isinstance(discount_info,
                                                                                                          dict) else None),
            "fulfillment": {"mode": fulfillment_mode, "address": address},
            "payment": {"method": payment_method, "status": PAYMENT_STATUS_PENDING},
            "status": "placed",
            "inventory_adjusted": True,
            "created_at": now,
            "updated_at": now,
            "timeline": [{"ts": now, "event": "placed"}],
        }

        orders.insert_one(order_doc)
        carts.delete_one(CartService._key(tenant, pn))

        # Payment intent uses grand_total (after discount)
        res = {"order_id": order_id, "status": "placed", "total": grand_total}

        if payment_method == PAYMENT_METHOD_ONLINE:
            provider = get_payments_provider(tenant)
            intent = provider.create_payment_intent(
                order_id=order_id,
                amount=grand_total,
                currency=(tcfg.get("payment_config") or {}).get("currency", "INR"),
            )
            orders.update_one(
                {"tenant": tenant, "id": order_id},
                {"$set": {"payment.intent_id": intent.intent_id}},
            )
            res.update(
                {"payment_url": intent.payment_url, "intent_id": intent.intent_id}
            )

        return res

    @classmethod
    def create_order_from_catalog(
            cls,
            tenant: str,
            items: List[Dict[str, Any]],
            customer_phone: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create an order from catalog cart (e.g. public catalog "Send to WhatsApp").
        No auth. Uses customer_phone if provided (e.g. dummy number for localhost testing), else "catalog".
        Deducts inventory and returns order_id for inclusion in WhatsApp message.
        """
        if not items:
            raise StoreValidationError("Cart is empty")

        tcfg = TenantService.get_tenant_settings(tenant) or {}
        if not bool(tcfg.get("store_enabled", True)):
            raise StoreValidationError("Store is disabled for tenant")

        phone = (customer_phone or "").strip() or "catalog"

        # Normalize items: require sku, qty, price_snapshot
        order_items = []
        for it in items:
            sku = str(it.get("sku") or "").strip()
            if not sku:
                continue
            try:
                qty = float(it.get("qty", 0))
                price = float(it.get("price_snapshot", 0))
            except (TypeError, ValueError):
                continue
            if qty <= 0:
                continue
            order_items.append({
                "sku": sku,
                "name": it.get("name") or sku,
                "qty": qty,
                "price_snapshot": price,
                "unit": it.get("unit"),
            })
        if not order_items:
            raise StoreValidationError("No valid items in cart")

        subtotal = PriceHelper.calc_subtotal(order_items)
        now = utcnow()
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        items_agg = StockHelper.aggregate_items(order_items, tenant=tenant)
        for sku, qty in items_agg.items():
            StockHelper.apply_stock_delta(tenant=tenant, sku=sku, delta=-qty, reason="checkout")

        order_doc = {
            "tenant": tenant,
            "id": order_id,
            "customer": {"phone": phone, "name": None},
            "items": order_items,
            "totals": {"subtotal": subtotal, "grand_total": subtotal},
            "fulfillment": {"mode": "pickup", "address": None},
            "payment": {"method": PAYMENT_METHOD_COD, "status": PAYMENT_STATUS_PENDING},
            "status": "placed",
            "inventory_adjusted": True,
            "created_at": now,
            "updated_at": now,
            "timeline": [{"ts": now, "event": "placed"}],
        }
        cls._orders().insert_one(order_doc)
        return {"order_id": order_id, "status": "placed", "total": subtotal}

    # ---------------- Helpers ----------------

    @staticmethod
    def _validate_fulfillment(tcfg: Dict[str, Any], mode: str, address: Optional[Dict[str, Any]]):
        if not bool(tcfg.get("store_enabled", True)):
            raise StoreValidationError("Store is disabled for tenant")

        deliv = tcfg.get("delivery_config") or {}

        if mode not in ("delivery", "pickup"):
            raise StoreValidationError("Invalid fulfillment_mode")

        if mode == "delivery" and not bool(deliv.get("delivery_enabled", True)):
            raise StoreValidationError("Delivery not enabled")

        if mode == "pickup" and not bool(deliv.get("pickup_enabled", True)):
            raise StoreValidationError("Pickup not enabled")

        if mode == "delivery" and not isinstance(address, dict):
            raise StoreValidationError("Address required for delivery")

    @staticmethod
    def _aggregate_items(items: List[Dict[str, Any]]) -> Dict[str, float]:
        agg: Dict[str, float] = {}
        for it in items or []:
            sku = str(it.get("sku") or "").strip()
            if not sku:
                continue
            qty = float(it.get("qty", 0))
            if qty <= 0:
                continue
            agg[sku] = agg.get(sku, 0.0) + qty
        return agg
