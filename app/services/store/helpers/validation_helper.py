# app/services/store/helpers/validation_helper.py
from __future__ import annotations
from typing import Any, Dict, List


class StoreValidationError(ValueError):
    pass


class StoreValidationHelper:
    @staticmethod
    def require_non_empty_str(value: Any, field: str) -> str:
        s = str(value or "").strip()
        if not s:
            raise StoreValidationError(f"{field} is required")
        return s

    @staticmethod
    def require_in(value: str, allowed: List[str], field: str) -> str:
        if value not in allowed:
            raise StoreValidationError(f"{field} must be one of: {', '.join(allowed)}")
        return value
