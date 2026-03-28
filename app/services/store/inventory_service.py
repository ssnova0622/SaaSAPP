# app/services/store/inventory_service.py
from __future__ import annotations

from typing import Any, Dict, Optional

from app.helpers.date_utils import utcnow
from app.services.db import get_db
from app.services.store.helpers.validation_helper import StoreValidationError


class InventoryService:
    @staticmethod
    def _col():
        return get_db().get_collection("inventory")

    # ---------------- Inventory ----------------

    @classmethod
    def get_inventory(cls, tenant: str, sku: str) -> Dict[str, Any]:
        col = cls._col()
        doc = col.find_one({"tenant": tenant, "sku": sku})
        qty = float(doc.get("available_qty", 0.0)) if doc else 0.0
        return {"sku": sku, "available_qty": qty}

    @classmethod
    def set_inventory_qty(
        cls,
        tenant: str,
        sku: str,
        qty: float,
        user_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        col = cls._col()
        now = utcnow()

        update_doc = {
            "$set": {
                "tenant": tenant,
                "sku": sku,
                "available_qty": float(qty),
                "updated_at": now,
                "updated_by": user_id,
                "reason": reason,
            },
            "$setOnInsert": {
                "created_at": now,
                "created_by": user_id,
            },
        }

        col.update_one({"tenant": tenant, "sku": sku}, update_doc, upsert=True)
        return {"sku": sku, "available_qty": float(qty)}

    @classmethod
    def adjust_stock(
        cls,
        tenant: str,
        sku: str,
        delta: float,
        user_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Adjust stock by +delta or -delta.
        Prevents negative inventory.
        """
        inv = cls.get_inventory(tenant, sku)
        cur = float(inv.get("available_qty", 0.0))
        new_qty = cur + float(delta)

        if new_qty < 0:
            raise StoreValidationError(
                f"Insufficient stock for SKU '{sku}' (have {cur}, need {abs(delta)})"
            )

        return cls.set_inventory_qty(
            tenant=tenant,
            sku=sku,
            qty=new_qty,
            user_id=user_id,
            reason=reason,
        )
