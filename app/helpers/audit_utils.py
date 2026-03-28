# app/helpers/audit_utils.py
"""
Standard audit fields for all collections: created_at, created_by, updated_at, updated_by.
- On insert: set all four (created_by and updated_by = same user; created_at and updated_at = same time).
- On update: set only updated_at, updated_by. Never overwrite created_at or created_by.
- Display: show "-" when created_by or updated_by is missing.
"""
from __future__ import annotations
from typing import Any, Dict, Optional

from app.helpers.date_utils import utcnow


def audit_fields_for_create(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Return dict with created_at, created_by, updated_at, updated_by for a new record."""
    now = utcnow()
    uid = (user_id or "").strip() or None
    return {
        "created_at": now,
        "created_by": uid,
        "updated_at": now,
        "updated_by": uid,
    }


def audit_fields_for_update(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Return dict with updated_at, updated_by only. Use for $set on updates."""
    now = utcnow()
    uid = (user_id or "").strip() or None
    return {
        "updated_at": now,
        "updated_by": uid,
    }


def display_created_by(value: Any, resolved_map: Optional[Dict[str, str]] = None) -> str:
    """Return display string for created_by; use '-' when missing."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return "-"
    if resolved_map and isinstance(value, str):
        return resolved_map.get(value) or value or "-"
    return str(value) if value else "-"


def display_updated_by(value: Any, resolved_map: Optional[Dict[str, str]] = None) -> str:
    """Return display string for updated_by; use '-' when missing."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return "-"
    if resolved_map and isinstance(value, str):
        return resolved_map.get(value) or value or "-"
    return str(value) if value else "-"
