# app/helpers/date_utils.py
"""
Date/time formatting and window helpers. Tenant-aware display formats; use from any module.
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Dict, Optional, Tuple
from zoneinfo import ZoneInfo

from app.helpers.constants import (
    DEFAULT_DISPLAY_DATE_FORMAT,
    DEFAULT_TIMEZONE,
    DISPLAY_DATE_FORMAT_STRFTIME,
)

logger = logging.getLogger(__name__)


def resolve_date_window(
        days: int = None,
        from_date: dt.date = None,
        to_date: dt.date = None,
        *,
        min_days: int = 7,
        max_days: int = 120,
) -> Tuple[dt.datetime, dt.datetime, int]:
    """Resolve a date window from explicit from_date/to_date or rolling days. Returns (window_start, window_end, days_diff)."""
    if from_date and to_date:
        start = dt.datetime.combine(from_date, dt.time.min)
        end = dt.datetime.combine(to_date, dt.time.max)
        return start, end, (to_date - from_date).days
    days = max(min_days, min(max_days, int(days or min_days)))
    end = utcnow()
    start = end - dt.timedelta(days=days)
    return start, end, days


def get_display_date_format(tenant_settings: Optional[Dict[str, Any]]) -> str:
    if not tenant_settings or not isinstance(tenant_settings, dict):
        return DEFAULT_DISPLAY_DATE_FORMAT
    fmt = tenant_settings.get("date_format") or DEFAULT_DISPLAY_DATE_FORMAT
    if fmt not in DISPLAY_DATE_FORMAT_STRFTIME:
        return DEFAULT_DISPLAY_DATE_FORMAT
    return fmt


def get_strftime_for_display(tenant_settings: Optional[Dict[str, Any]]) -> str:
    fmt = get_display_date_format(tenant_settings)
    return DISPLAY_DATE_FORMAT_STRFTIME.get(fmt, DISPLAY_DATE_FORMAT_STRFTIME[DEFAULT_DISPLAY_DATE_FORMAT])


def format_date_for_display(date_obj: Any, tenant_settings: Optional[Dict[str, Any]]) -> str:
    if date_obj is None:
        return ""
    strftime_fmt = get_strftime_for_display(tenant_settings)
    if isinstance(date_obj, (dt.date, dt.datetime)):
        try:
            return date_obj.strftime(strftime_fmt)
        except (ValueError, TypeError):
            return str(date_obj)
    return str(date_obj)


def format_date_for_tenant(date_obj: Any, tenant_settings: Optional[Dict[str, Any]]) -> str:
    return format_date_for_display(date_obj, tenant_settings)


def get_tenant_timezone_zoneinfo(tenant_settings: Optional[Dict[str, Any]]) -> ZoneInfo:
    tz_name = None
    if tenant_settings and isinstance(tenant_settings, dict):
        tz_name = tenant_settings.get("tz")
    return get_tz(tz_name, fallback=DEFAULT_TIMEZONE)


def parse_iso_date(date_str: Optional[str]) -> Optional[dt.date]:
    if not date_str or not isinstance(date_str, str):
        return None
    s = date_str.strip()
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _strptime_for_tenant(tenant_settings: Optional[Dict[str, Any]]) -> str:
    fmt = get_display_date_format(tenant_settings)
    return DISPLAY_DATE_FORMAT_STRFTIME.get(fmt, DISPLAY_DATE_FORMAT_STRFTIME[DEFAULT_DISPLAY_DATE_FORMAT])


def parse_user_date_input(text: str, tenant_settings: Optional[Dict[str, Any]]) -> Optional[dt.date]:
    if not text or not isinstance(text, str):
        return None
    import re
    s = text.strip()
    if not s:
        return None
    try:
        pattern = _strptime_for_tenant(tenant_settings)
        return dt.datetime.strptime(s, pattern).date()
    except (ValueError, TypeError):
        pass
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            return dt.date.fromisoformat(s)
    except (ValueError, TypeError):
        pass
    try:
        if re.match(r"^\d{2}-\d{2}-\d{4}$", s):
            return dt.datetime.strptime(s, "%d-%m-%Y").date()
    except (ValueError, TypeError):
        pass
    try:
        if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", s):
            return dt.datetime.strptime(s, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        pass
    try:
        if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", s):
            return dt.datetime.strptime(s, "%m/%d/%Y").date()
    except (ValueError, TypeError):
        pass
    return None


def get_tz(tz_name: Optional[str], fallback: Optional[str] = None) -> ZoneInfo:
    if fallback is None:
        fallback = DEFAULT_TIMEZONE
    name = (str(tz_name).strip() if tz_name else "") or fallback
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo(fallback)


def get_tenant_tz(settings: Optional[Dict[str, Any]]) -> ZoneInfo:
    """Return ZoneInfo for the tenant from a settings dict (e.g. from TenantService.get_tenant_settings).
    Uses settings['tz'] or app default. Safe to call with None/empty settings.
    """
    return get_tenant_timezone_zoneinfo(settings)


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
