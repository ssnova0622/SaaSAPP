# app/helpers/tools.py
# Re-exports date/time helpers from date_utils (single source). Other generic helpers below.

from __future__ import annotations

from typing import Dict, List
import uuid


def resolve_product_names(tenant: str, skus: List[str], product_repo) -> Dict[str, str]:
    """
    Build a map of SKU → human-readable product name.
    Works with any product_repo that provides find_by_skus(tenant, skus) and find_by_variant_skus(tenant, skus).
    """
    name_map: Dict[str, str] = {}

    if not skus:
        return name_map

    # Base products
    for p in product_repo.find_by_skus(tenant, skus):
        name_map[str(p.sku)] = str(p.name or "")

    # Variants
    for vdoc in product_repo.find_by_variant_skus(tenant, skus):
        base_name = str(vdoc.name or "")
        for v in (vdoc.variants or []):
            vs = str(v.get("variant_sku") or "").strip()
            if not vs or vs not in skus or vs in name_map:
                continue

            attrs = v.get("attributes") or {}
            if isinstance(attrs, dict) and attrs:
                kv = ", ".join(f"{k}: {attrs[k]}" for k in attrs)
                name_map[vs] = f"{base_name} ({kv})"
            else:
                name_map[vs] = base_name

    return name_map


def to_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    try:
        return float(value)
    except Exception:
        return default


def to_int(value, default: int = 0) -> int:
    """Safely convert a value to int."""
    try:
        return int(value)
    except Exception:
        return default


def uuid4() -> str:
    return str(uuid.uuid4())
