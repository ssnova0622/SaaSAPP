# app/services/store/helpers/price_helper.py
from __future__ import annotations
from typing import Dict, Any


class PriceHelper:
    @staticmethod
    def calc_subtotal(items: list[dict[str, Any]]) -> float:
        subtotal = 0.0
        for it in items or []:
            try:
                qty = float(it.get("qty", 0))
                price = float(it.get("price_snapshot", 0))
            except Exception:
                qty, price = 0.0, 0.0
            subtotal += qty * price
        return float(subtotal)
