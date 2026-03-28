"""
WhatsApp copy — always from tenant message templates.

Resolution order (see TenantStorage.get_tenant_settings):
1. tenant_message_templates collection (MongoDB) per tenant
2. Platform defaults + labels in ``default_message`` collection (see default_message_service)

Use template keys defined in the platform ``default_message`` document (e.g. wa_* keys).
Workflow step `label` in the admin UI still overrides prompts where supported.
"""
from __future__ import annotations

from typing import Any

from app.services.core import message_templates as _mt


def wa(tenant_id: str, key: str, **placeholders: Any) -> str:
    """Resolve a template key for this tenant. Returns empty string if key missing everywhere."""
    return _mt.get_message(tenant_id, key, **placeholders)
