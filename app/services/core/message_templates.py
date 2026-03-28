"""
Tenant-configurable message templates (template-based messaging / configurable auto-replies).

Platform defaults and row labels live in MongoDB ``default_message`` (document ``platform``).
Tenant overrides are only in ``tenant_message_templates``.
"""
from __future__ import annotations

import re
from typing import Any, Dict

from app.core.container import get_tenant_service


def list_whatsapp_admin_template_keys() -> list[str]:
    """All keys in ``default_message`` (admin Messages screen uses grouped sections)."""
    from app.services.core.default_message_service import list_all_default_message_keys

    return list_all_default_message_keys()


def get_message(tenant_id: str, key: str, **placeholders: Any) -> str:
    """
    Resolve a message template for the tenant.
    Uses tenant settings (merged defaults + overrides), then ``default_message`` alone.
    """
    settings = get_tenant_service().get_tenant_settings(tenant_id) or {}
    templates = settings.get("message_templates") or settings.get("templates") or {}
    if not isinstance(templates, dict):
        templates = {}
    template = templates.get(key)
    if not template:
        try:
            from app.services.core.default_message_service import get_default_template

            template = get_default_template(key) or ""
        except Exception:
            template = ""
    if not template:
        return ""
    for k, v in placeholders.items():
        template = template.replace("{" + k + "}", str(v or ""))
    template = re.sub(r"\{[a-z_]+\}", "", template)
    template = re.sub(r"\n{3,}", "\n\n", template).strip()
    return template


def get_defaults() -> Dict[str, str]:
    """All platform template bodies from ``default_message`` (copy for callers)."""
    from app.services.core.default_message_service import get_default_templates_merged

    return dict(get_default_templates_merged())
