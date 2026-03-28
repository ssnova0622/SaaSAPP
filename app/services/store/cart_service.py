# app/services/store/cart_service.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.helpers.date_utils import utcnow
from app.services.db import get_db
from app.services.store.helpers.unit_conversion_helper import UnitConversionHelper
from app.services.store.products_service import ProductService
from app.services.store.helpers.price_helper import PriceHelper


class CartService:
    @staticmethod
    def _col():
        return get_db().get_collection("carts")

    # ---------------- Carts ----------------

    @classmethod
    def get_cart(cls, tenant: str, phone: str) -> Dict[str, Any]:
        col = cls._col()
        phone = str(phone).strip()

        doc = col.find_one({"tenant": tenant, "customer_phone": phone})
        if not doc:
            now = utcnow()
            doc = {
                "tenant": tenant,
                "customer_phone": phone,
                "items": [],
                "totals": {"subtotal": 0.0},
                "updated_at": now,
                "status": "active",
            }
            col.insert_one(doc)

        out = dict(doc)
        out.pop("_id", None)
        return out

    @classmethod
    def put_cart(
            cls,
            tenant: str,
            phone: str,
            items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        col = cls._col()
        phone = str(phone).strip()

        clean: List[Dict[str, Any]] = []

        for it in items or []:
            sku = str(it.get("sku") or "").strip()
            if not sku:
                continue

            qty = max(0.0, float(it.get("qty", 0)))
            price = max(0.0, float(it.get("price_snapshot", 0)))
            unit = it.get("unit")

            # Only recalc when price is missing (e.g. legacy or incomplete payload).
            # When client sends a positive price_snapshot (e.g. offer price), preserve it.
            if price <= 0:
                prod = ProductService.get_product_by_sku(tenant, sku)
                if prod:
                    base_price = float(prod.get("price") or 0.0)
                    base_unit = prod.get("unit")
                    conversions = prod.get("unit_conversions") or []
                    price = UnitConversionHelper.convert_price(base_price=base_price, base_unit=base_unit,
                                                               target_unit=unit,
                                                               conversions=conversions, )

            if qty <= 0:
                continue

            clean.append(
                {
                    "sku": sku,
                    "qty": qty,
                    "price_snapshot": price,
                    "unit": unit,
                    "name": it.get("name"),
                    "manual": bool(it.get("manual", False)),
                }
            )

        totals = {"subtotal": PriceHelper.calc_subtotal(clean)}
        now = utcnow()

        col.update_one(
            {"tenant": tenant, "customer_phone": phone},
            {
                "$set": {
                    "items": clean,
                    "totals": totals,
                    "updated_at": now,
                    "status": "active",
                }
            },
            upsert=True,
        )

        return cls.get_cart(tenant, phone)
