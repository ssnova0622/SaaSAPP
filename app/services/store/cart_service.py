# app/services/store/cart_service.py
from __future__ import annotations

from typing import Any, Dict, List

from app.helpers.phone_util import PhoneUtil
from app.helpers.date_utils import utcnow
from app.services.core.tenant_service import TenantService
from app.services.db import get_db
from app.services.store.helpers.unit_conversion_helper import UnitConversionHelper
from app.services.store.products_service import ProductService
from app.services.store.helpers.price_helper import PriceHelper


class CartService:
    @staticmethod
    def _col():
        return get_db().get_collection("carts")

    @staticmethod
    def _key(tenant: str, pn: Dict[str, str]) -> Dict[str, Any]:
        return {
            "tenant": tenant,
            "customer_phone_number.code": pn["code"],
            "customer_phone_number.number": pn["number"],
        }

    @classmethod
    def _resolve_cart_doc(cls, col, tenant: str, pn: Dict[str, str]) -> Dict[str, Any]:
        flt = cls._key(tenant, pn)
        doc = col.find_one(flt)
        if doc:
            return doc
        e164 = PhoneUtil.to_e164(pn)
        leg = col.find_one({"tenant": tenant, "customer_phone": e164})
        if leg:
            col.update_one(
                {"_id": leg["_id"]},
                {"$set": {"customer_phone_number": pn}, "$unset": {"customer_phone": ""}},
            )
            doc = col.find_one(flt)
        return doc or {}

    @classmethod
    def get_cart(cls, tenant: str, phone: str) -> Dict[str, Any]:
        col = cls._col()
        phone = str(phone).strip()
        dial = TenantService._get_tenant_country_code(tenant) or PhoneUtil.DEFAULT_DIAL_DIGITS
        pn = PhoneUtil.prepare_storage(phone, dial)
        if not pn:
            raise ValueError("Invalid phone")
        doc = cls._resolve_cart_doc(col, tenant, pn)
        if not doc:
            now = utcnow()
            doc = {
                "tenant": tenant,
                "customer_phone_number": pn,
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
        dial = TenantService._get_tenant_country_code(tenant) or PhoneUtil.DEFAULT_DIAL_DIGITS
        pn = PhoneUtil.prepare_storage(phone, dial)
        if not pn:
            raise ValueError("Invalid phone")
        flt = cls._key(tenant, pn)

        clean: List[Dict[str, Any]] = []

        for it in items or []:
            sku = str(it.get("sku") or "").strip()
            if not sku:
                continue

            qty = max(0.0, float(it.get("qty", 0)))
            price = max(0.0, float(it.get("price_snapshot", 0)))
            unit = it.get("unit")

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
            flt,
            {
                "$set": {
                    "customer_phone_number": pn,
                    "items": clean,
                    "totals": totals,
                    "updated_at": now,
                    "status": "active",
                },
                "$unset": {"customer_phone": ""},
            },
            upsert=True,
        )

        return cls.get_cart(tenant, phone)
