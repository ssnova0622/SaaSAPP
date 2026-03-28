"""
Workflow and booking message helpers. Used by action executor and routes.
"""
from __future__ import annotations
import datetime as dt
from typing import Any, Dict

from app.core.container import get_tenant_service
from app.services.core import message_templates as msg_tpl
from app.services.whatsapp.helpers.constants import WORKFLOW_COMPLETE_SENTINEL
from app.helpers.date_utils import format_date_for_display


def get_confirmation_msg(tenant: str, context: Dict[str, Any]) -> str:
    """Build a standard confirmation message for booking (configurable)."""
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    service = context.get("service", "appointment")
    slot = context.get("selected_slot", "N/A")
    prof = context.get("professional", "N/A")
    date_val = context.get("date")
    date_str = "N/A"
    if date_val:
        try:
            date_str = format_date_for_display(dt.date.fromisoformat(date_val), settings)
        except Exception:
            date_str = date_val
    return msg_tpl.get_message(
        tenant,
        "booking_confirm_prompt",
        service=service,
        professional=prof,
        time=slot,
        date=date_str,
    )


def workflow_has_custom_end_message(tenant: str) -> bool:
    """True if tenant has a custom end-flow message."""
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    custom = (settings.get("whatsapp_end_flow_message") or "").strip()
    return bool(custom)


def workflow_reply_or_welcome(tenant: str, reply: str) -> str:
    """When workflow returns the 'complete' message, return custom end-flow text (or default)."""
    if not reply or reply.strip() != WORKFLOW_COMPLETE_SENTINEL:
        return reply or ""
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    custom = (settings.get("whatsapp_end_flow_message") or "").strip()
    if custom:
        return custom
    tenant_name = str(settings.get("business_name") or settings.get("tenant") or tenant)
    return msg_tpl.get_message(tenant, "workflow_complete", tenant_name=tenant_name)
