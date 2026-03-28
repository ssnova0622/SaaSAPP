# services/ai/modules/carts.py

import datetime as dt
from typing import Dict, Any

from app.helpers.date_utils import utcnow
from app.helpers.tools import to_float
from app.helpers.tools import resolve_product_names
from app.services.ai.helpers.config import AI_DEFAULTS


class CartRecoveryService:
    """
    Provides cart recovery analytics:
    - Total abandoned carts
    - Top abandoned SKUs
    """

    def __init__(self, cart_repo, product_repo):
        """
        Args:
            cart_repo: CartRepository
            product_repo: ProductRepository
        """
        self.cart_repo = cart_repo
        self.product_repo = product_repo

    # ----------------------------------------------------------------------
    # CART RECOVERY
    # ----------------------------------------------------------------------

    def cart_recovery(
            self,
            tenant: str,
            window_hours: int = None,
            top: int = None,
    ) -> Dict[str, Any]:
        """
        Cart recovery insights over a rolling window.
        """
        if not tenant:
            raise ValueError("tenant is required")

        cfg = AI_DEFAULTS["carts"]

        window_hours = max(1, min(168, int(window_hours or cfg["window_hours"])))
        top = max(1, min(100, int(top or cfg["top"])))

        since = utcnow() - dt.timedelta(hours=window_hours)

        query = {
            "tenant": tenant,
            "updated_at": {"$gte": since},
            "items.0": {"$exists": True},
        }

        total_abandoned = 0
        sku_agg: Dict[str, float] = {}

        try:
            cursor = self.cart_repo.get_collection().find(query, {"items": 1})
            for cart in cursor:
                total_abandoned += 1
                for item in (cart.get("items") or []):
                    sku = str(item.get("sku") or "").strip()
                    qty = to_float(item.get("qty"))
                    if sku and qty > 0:
                        sku_agg[sku] = sku_agg.get(sku, 0.0) + qty
        except Exception:
            total_abandoned = 0
            sku_agg = {}

        skus = list(sku_agg.keys())
        name_map = resolve_product_names(tenant, skus, self.product_repo)

        items = [
            {
                "sku": s,
                "name": name_map.get(s, s),
                "qty": round(q, 2),
            }
            for s, q in sku_agg.items()
        ]

        items.sort(key=lambda x: (-x["qty"], x["sku"]))

        return {
            "window_hours": window_hours,
            "total_abandoned": int(total_abandoned),
            "top_skus": items[:top],
        }
