"""Safe dynamic message rendering with {{placeholders}} for WhatsApp."""
from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Optional, Set

from app.core.container import get_tenant_service

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
_MAX_MESSAGE_LEN = 4096
_SCRIPT_TAG_RE = re.compile(r"<\s*script\b", re.IGNORECASE)
_ALLOWED_PLACEHOLDER_KEYS: Set[str] = frozenset({
    "name",
    "customer_name",
    "phone",
    "service",
    "professional",
    "date",
    "time",
    "business_name",
    "tenant",
    "order_id",
    "appointment_id",
})


def sanitize_message_text(text: str, *, max_len: int = _MAX_MESSAGE_LEN) -> str:
    """Strip control chars, block script tags, and cap length."""
    if not text:
        return ""
    cleaned = str(text).replace("\x00", "")
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
    if _SCRIPT_TAG_RE.search(cleaned):
        raise ValueError("Message contains disallowed content")
    if len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 3] + "..."
    return cleaned


def extract_placeholder_keys(text: str) -> Set[str]:
    return {m.group(1) for m in _PLACEHOLDER_RE.finditer(text or "")}


def validate_placeholders(text: str) -> Optional[str]:
    """Return error message if unknown placeholders are used."""
    keys = extract_placeholder_keys(text)
    unknown = keys - _ALLOWED_PLACEHOLDER_KEYS
    if unknown:
        return f"Unknown placeholders: {', '.join(sorted(unknown))}"
    return None


def build_tenant_render_context(
    tenant: str,
    *,
    phone: str = "",
    session_ctx: Optional[Mapping[str, Any]] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, str]:
    """Build placeholder values from tenant settings and session."""
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    ctx = session_ctx or {}
    out: Dict[str, str] = {
        "tenant": str(tenant),
        "business_name": str(
            settings.get("business_name") or settings.get("name") or tenant
        ),
        "phone": str(phone or ctx.get("customer_phone") or ""),
        "name": str(ctx.get("customer_name") or ctx.get("name") or ""),
        "customer_name": str(ctx.get("customer_name") or ctx.get("name") or ""),
        "service": str(ctx.get("service") or ""),
        "professional": str(ctx.get("professional") or ""),
        "date": str(ctx.get("date") or ctx.get("appointment_date") or ""),
        "time": str(ctx.get("time") or ctx.get("selected_slot") or ""),
        "order_id": str(ctx.get("order_id") or ""),
        "appointment_id": str(ctx.get("appointment_id") or ctx.get("reschedule_id") or ""),
    }
    if extra:
        for k, v in extra.items():
            key = str(k).strip()
            if key in _ALLOWED_PLACEHOLDER_KEYS:
                out[key] = str(v or "")
    return out


def render_message_template(
    text: str,
    context: Mapping[str, str],
    *,
    sanitize: bool = True,
) -> str:
    """Replace {{key}} placeholders; missing keys become empty string."""
    if not text:
        return ""

    def _repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(context.get(key, ""))

    rendered = _PLACEHOLDER_RE.sub(_repl, str(text))
    return sanitize_message_text(rendered) if sanitize else rendered
