# app/services/store/helpers/unit_conversion_helper.py
from __future__ import annotations

from typing import Any, Dict, Optional


class UnitConversionHelper:
    """
    Handles all unit conversion logic for products.
    Supports:
    - Custom unit conversions (unit_conversions array)
    - Standard conversions (kg <-> gram, dozen <-> piece, pack of 6 <-> piece)
    """

    @staticmethod
    def convert_price(
        base_price: float,
        base_unit: Optional[str],
        target_unit: Optional[str],
        conversions: Optional[list[dict[str, Any]]] = None,
    ) -> float:
        """
        Convert price from base_unit to target_unit using:
        1. Custom conversions (preferred)
        2. Standard conversions (fallback)
        """

        if not target_unit or target_unit == base_unit:
            return base_price

        conversions = conversions or []

        # -------------------------
        # 1. Custom conversions
        # -------------------------
        conv = next((c for c in conversions if c.get("unit") == target_unit), None)
        if conv:
            factor = float(conv.get("factor") or 1.0)
            return base_price * factor

        # -------------------------
        # 2. Standard conversions
        # -------------------------

        # kg <-> gram
        if target_unit == "gram" and base_unit == "kg":
            return base_price * 0.001
        if target_unit == "kg" and base_unit == "gram":
            return base_price * 1000

        # dozen <-> piece
        if target_unit in ("pc", "pcs", "piece") and base_unit == "dozen":
            return base_price / 12.0
        if target_unit == "dozen" and base_unit in ("pc", "pcs", "piece"):
            return base_price * 12.0

        # pack of 6 <-> piece
        if target_unit in ("pc", "pcs", "piece") and base_unit == "pack of 6":
            return base_price / 6.0
        if target_unit == "pack of 6" and base_unit in ("pc", "pcs", "piece"):
            return base_price * 6.0

        # No conversion rule found → return base price
        return base_price

    _UNIT_ALIASES: Dict[str, str] = {
        "g": "gram", "grams": "gram", "gram": "gram",
        "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
        "pc": "pc", "pcs": "pcs", "piece": "piece", "pieces": "piece",
    }

    @classmethod
    def _normalize_unit(cls, unit: Optional[str]) -> Optional[str]:
        if not unit or not str(unit).strip():
            return None
        u = str(unit).strip().lower()
        return cls._UNIT_ALIASES.get(u) or u

    @staticmethod
    def convert_qty_to_base(
        qty: float,
        from_unit: Optional[str],
        base_unit: Optional[str],
        conversions: Optional[list] = None,
    ) -> float:
        """
        Convert quantity from from_unit to base_unit (for stock comparison).
        Inventory is stored in product base unit; order/cart items may be in selling unit (e.g. grams).
        Returns qty expressed in base_unit so it can be compared with available_qty.
        Accepts common aliases: g/grams/gram, kg/kgs/kilogram, etc.
        """
        if not base_unit or qty <= 0:
            return qty
        from_unit = UnitConversionHelper._normalize_unit(from_unit)
        base_unit_n = UnitConversionHelper._normalize_unit(base_unit)
        if not from_unit or from_unit == base_unit_n:
            return qty

        conversions = conversions or []

        # 1. Custom conversions: factor = "how many base units per 1 of from_unit"
        conv = next((c for c in conversions if UnitConversionHelper._normalize_unit(c.get("unit")) == from_unit), None)
        if conv:
            factor = float(conv.get("factor") or 1.0)
            return qty * factor

        # 2. Standard conversions (from_unit -> base_unit)
        if from_unit == "gram" and base_unit_n == "kg":
            return qty * 0.001
        if from_unit == "kg" and base_unit_n == "gram":
            return qty * 1000.0
        if from_unit in ("pc", "pcs", "piece") and base_unit_n == "dozen":
            return qty / 12.0
        if from_unit == "dozen" and base_unit_n in ("pc", "pcs", "piece"):
            return qty * 12.0
        if from_unit in ("pc", "pcs", "piece") and base_unit_n == "pack of 6":
            return qty / 6.0
        if from_unit == "pack of 6" and base_unit_n in ("pc", "pcs", "piece"):
            return qty * 6.0

        # No rule: assume same unit (e.g. both "kg" or unknown)
        return qty
