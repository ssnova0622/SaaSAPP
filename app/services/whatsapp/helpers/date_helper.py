# app/services/whatsapp/helpers/date_helper.py
from __future__ import annotations
import datetime as dt
from typing import Any, Dict, Optional, Callable

from app.helpers.date_utils import format_date_for_tenant


def _default_get_settings(tenant: str) -> Dict[str, Any]:
    from app.core.container import get_tenant_service
    return get_tenant_service().get_tenant_settings(tenant) or {}


def format_tenant_date(
        tenant: str,
        date: dt.date,
        get_tenant_settings: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
) -> str:
    """Format date using tenant settings. Optional provider for DI/testing."""
    get_settings = get_tenant_settings or _default_get_settings
    settings = get_settings(tenant) or {}
    return format_date_for_tenant(date, settings)
