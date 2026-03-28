# app/services/store/orders_service.py
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from pymongo import ReturnDocument

from app.helpers.date_utils import utcnow
from app.services.db import get_db
from app.services.store.helpers.price_helper import PriceHelper
from app.services.store.helpers.stock_helper import StockHelper
from app.services.store.inventory_service import InventoryService
from app.services.store.helpers.validation_helper import StoreValidationError
from app.services.store.helpers.constants import (
    ORDER_STATUS_CANCELED,
    PAYMENT_STATUS_PAID,
    PAYMENT_METHOD_ONLINE,
)


class OrdersService:
    @staticmethod
    def _col():
        return get_db().get_collection("orders")

    # ---------------- Orders ----------------

    @classmethod
    def list_orders(
            cls,
            tenant: str,
            statuses: Optional[List[str]] = None,
            search: Optional[str] = None,
            page: int = 1,
            size: int = 50,
    ) -> Dict[str, Any]:
        col = cls._col()
        q: Dict[str, Any] = {"tenant": tenant}

        if statuses:
            q["status"] = {"$in": statuses}

        if search:
            s = str(search).strip()
            q["$or"] = [
                {"id": {"$regex": s, "$options": "i"}},
                {"customer.phone": {"$regex": s, "$options": "i"}},
                {"customer.name": {"$regex": s, "$options": "i"}},
                {"address.label": {"$regex": s, "$options": "i"}},
                {"address.line1": {"$regex": s, "$options": "i"}},
            ]

        page = max(1, int(page or 1))
        size = max(1, min(200, int(size or 50)))
        skip = (page - 1) * size

        total = col.count_documents(q)
        items: List[Dict[str, Any]] = []

        for d in col.find(q).sort("created_at", -1).skip(skip).limit(size):
            row = dict(d)
            row.pop("_id", None)
            items.append(row)

        return {"items": items, "total": total, "page": page, "size": size}

    @classmethod
    def get_order(cls, tenant: str, order_id: str) -> Optional[Dict[str, Any]]:
        col = cls._col()
        oid = (order_id or "").strip()
        doc = col.find_one({"tenant": tenant, "id": oid})
        if not doc and oid.upper().startswith("ORD-"):
            doc = col.find_one({"tenant": tenant, "id": oid.upper()})
        if not doc:
            return None
        out = dict(doc)
        out.pop("_id", None)
        return out

    # ---------------- Status Updates ----------------

    @classmethod
    def update_order_status(cls, tenant: str, order_id: str, status: str) -> Dict[str, Any]:
        col = cls._col()

        allowed = {
            "placed",
            "confirmed",
            "picking",
            "ready_for_pickup",
            "out_for_delivery",
            "delivered",
            ORDER_STATUS_CANCELED,
        }
        if status not in allowed:
            raise StoreValidationError("Invalid status")

        doc = col.find_one({"tenant": tenant, "id": order_id})
        if not doc:
            raise StoreValidationError("Order not found")

        now = utcnow()
        items_agg = cls._aggregate_items(doc.get("items") or [])
        inv_adjusted = bool(doc.get("inventory_adjusted", False))

        # Handle cancellation → restore stock (use unit-aware aggregation so qty is in base unit)
        if status == ORDER_STATUS_CANCELED and inv_adjusted:
            items_agg = StockHelper.aggregate_items(doc.get("items") or [], tenant=tenant)
            for sku, qty in items_agg.items():
                StockHelper.apply_stock_delta(tenant=tenant, sku=sku, delta=qty, reason="order_cancel")

            update_ops = {
                "$set": {
                    "status": status,
                    "updated_at": now,
                    "inventory_adjusted": False,
                },
                "$push": {
                    "timeline": {
                        "ts": now,
                        "event": status,
                        "meta": {"action": "revert", "items": items_agg},
                    }
                },
            }

            res = col.find_one_and_update(
                {"tenant": tenant, "id": order_id},
                update_ops,
                return_document=ReturnDocument.AFTER,
            )
        else:
            res = col.find_one_and_update(
                {"tenant": tenant, "id": order_id},
                {
                    "$set": {"status": status, "updated_at": now},
                    "$push": {"timeline": {"ts": now, "event": status}},
                },
                return_document=ReturnDocument.AFTER,
            )

        if not res:
            raise StoreValidationError("Order not found")

        out = dict(res)
        out.pop("_id", None)
        return out

    @classmethod
    def set_order_payment_status(cls, tenant: str, order_id: str, status: str) -> None:
        col = cls._col()
        set_doc: Dict[str, Any] = {"payment.status": status, "updated_at": utcnow()}
        if status == PAYMENT_STATUS_PAID:
            set_doc["payment.paid_at"] = utcnow()
        col.update_one(
            {"tenant": tenant, "id": order_id},
            {"$set": set_doc, "$push": {"timeline": {"ts": utcnow(), "event": f"payment_{status}"}}},
        )

    # ---------------- Item Updates ----------------

    @classmethod
    def update_order_items(
            cls,
            tenant: str,
            order_id: str,
            items: List[Dict[str, Any]],
            notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        col = cls._col()
        doc = col.find_one({"tenant": tenant, "id": order_id})

        if not doc:
            raise StoreValidationError("Order not found")

        if doc.get("status") not in ("placed", "confirmed", "picking"):
            raise StoreValidationError(f"Order cannot be edited in status '{doc.get('status')}'")

        if doc.get("payment", {}).get("method") == PAYMENT_METHOD_ONLINE and doc.get("payment", {}).get(
                "status") == PAYMENT_STATUS_PAID:
            raise StoreValidationError("Cannot edit items on a paid online order")

        clean = cls._clean_items(items)
        old_agg = StockHelper.aggregate_items(doc["items"], tenant=tenant)
        new_agg = StockHelper.aggregate_items(clean, tenant=tenant)
        diffs = StockHelper.compute_diffs(old_agg, new_agg)

        # Check stock for increases
        for sku, delta in diffs.items():
            if delta > 0:
                inv = InventoryService.get_inventory(tenant, sku)
                if inv["available_qty"] < delta:
                    raise StoreValidationError(
                        f"Insufficient stock for SKU '{sku}' (have {inv['available_qty']}, need {delta})"
                    )

        # Apply deltas
        for sku, delta in diffs.items():
            StockHelper.apply_stock_delta(tenant=tenant, sku=sku, delta=-delta, reason="order_edit")

        totals = {"subtotal": PriceHelper.calc_subtotal(clean)}
        now = utcnow()

        set_payload: Dict[str, Any] = {"items": clean, "totals": totals, "updated_at": now}
        if notes is not None:
            set_payload["notes"] = (str(notes).strip() or None)

        update_ops = {
            "$set": set_payload,
            "$push": {
                "timeline": {
                    "ts": now,
                    "event": "items_updated",
                    "meta": {"diffs": diffs},
                }
            },
        }

        res = col.find_one_and_update(
            {"tenant": tenant, "id": order_id},
            update_ops,
            return_document=ReturnDocument.AFTER,
        )

        out = dict(res)
        out.pop("_id", None)
        return out

    # ---------------- Helpers ----------------

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

    @staticmethod
    def _clean_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        clean = []
        for it in items or []:
            sku = str(it.get("sku") or "").strip()
            qty = float(it.get("qty", 0))
            if not sku or qty <= 0:
                continue
            row = {
                "sku": sku,
                "qty": qty,
                "price_snapshot": float(it.get("price_snapshot", 0)),
                "unit": it.get("unit"),
                "name": it.get("name"),
            }
            if it.get("manual") is True:
                row["manual"] = True
            if it.get("offer_applied") is True:
                row["offer_applied"] = True
            if it.get("price_before_offer") is not None:
                try:
                    row["price_before_offer"] = float(it["price_before_offer"])
                except (TypeError, ValueError):
                    pass
            clean.append(row)
        return clean

    @staticmethod
    def _compute_diffs(old: Dict[str, float], new: Dict[str, float]) -> Dict[str, float]:
        diffs = {}
        all_skus = set(old.keys()) | set(new.keys())
        for sku in all_skus:
            diff = new.get(sku, 0.0) - old.get(sku, 0.0)
            if abs(diff) > 0.0001:
                diffs[sku] = diff
        return diffs
