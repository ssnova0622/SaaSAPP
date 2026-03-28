# services/ai/modules/categories.py
import datetime as dt
from typing import Dict, List, Any
from app.helpers.tools import to_float
from app.services.ai.helpers.config import AI_DEFAULTS
from app.helpers.date_utils import resolve_date_window


class CategoriesService:
    """
    Provides category-level analytics:
    - Revenue and quantity by category
    """

    def __init__(self, order_repo, product_repo):
        """
        Args:
            order_repo: OrderRepository
            product_repo: ProductRepository
        """
        self.order_repo = order_repo
        self.product_repo = product_repo

    # ----------------------------------------------------------------------
    # CATEGORY MIX
    # ----------------------------------------------------------------------

    def category_mix(
            self,
            tenant: str,
            days: int = None,
            from_date: dt.date = None,
            to_date: dt.date = None,
    ) -> List[Dict[str, Any]]:
        """
        Return revenue/qty by product category.
        """
        if not tenant:
            raise ValueError("tenant is required")

        cfg = AI_DEFAULTS["categories"]

        # Resolve date window
        window_start, window_end, _ = resolve_date_window(
            days or cfg["days"],
            from_date,
            to_date,
        )

        # Aggregate per SKU
        per_sku: Dict[str, Dict[str, float]] = {}

        cursor = self.order_repo.get_collection().find(
            {
                "tenant": tenant,
                "status": {"$ne": "canceled"},
                "created_at": {"$gte": window_start, "$lte": window_end},
            },
            {"items": 1},
        )

        for order_doc in cursor:
            for item in (order_doc.get("items") or []):
                sku = str(item.get("sku") or "").strip()
                qty = to_float(item.get("qty"))
                price = to_float(item.get("price_snapshot"))

                if not sku or qty <= 0:
                    continue

                row = per_sku.setdefault(sku, {"qty": 0.0, "revenue": 0.0})
                row["qty"] += qty
                row["revenue"] += qty * price

        if not per_sku:
            return []

        skus = list(per_sku.keys())

        # Map SKU → category
        cat_map: Dict[str, str] = {}

        # Base products
        for p in self.product_repo.get_collection().find(
                {"tenant": tenant, "sku": {"$in": skus}},
                {"sku": 1, "category": 1},
        ):
            cat_map[str(p.get("sku"))] = str(p.get("category") or "Uncategorized")

        # Variants
        variant_docs = self.product_repo.get_collection().find(
            {"tenant": tenant, "variants.variant_sku": {"$in": skus}},
            {"category": 1, "variants": 1},
        )

        for vdoc in variant_docs:
            cat = str(vdoc.get("category") or "Uncategorized")
            for v in (vdoc.get("variants") or []):
                vs = str(v.get("variant_sku") or "").strip()
                if vs in skus and vs not in cat_map:
                    cat_map[vs] = cat

        # Aggregate per category
        per_cat: Dict[str, Dict[str, float]] = {}

        for sku, agg in per_sku.items():
            cat = cat_map.get(sku, "Uncategorized")
            row = per_cat.setdefault(cat, {"qty": 0.0, "revenue": 0.0})
            row["qty"] += agg["qty"]
            row["revenue"] += agg["revenue"]

        total_rev = sum(v["revenue"] for v in per_cat.values()) or 1.0

        # Build output
        items = [
            {
                "category": c,
                "qty": round(v["qty"], 2),
                "revenue": round(v["revenue"], 2),
                "share_revenue": round((v["revenue"] / total_rev) * 100.0, 2),
            }
            for c, v in per_cat.items()
        ]

        items.sort(key=lambda x: (-x["revenue"], x["category"]))

        return items
