"""
Workflow and booking message helpers. Used by action executor and routes.
"""
from __future__ import annotations
import datetime as dt
from typing import Any, Dict

from app.core.container import get_tenant_service
from app.services.core import message_templates as msg_tpl
from app.services.whatsapp.helpers.constants import WORKFLOW_COMPLETE_SENTINEL
from app.services.whatsapp.usecases.salon.booking_display import format_booking_party_label
from app.helpers.date_utils import format_date_for_display


def get_confirmation_msg(tenant: str, context: Dict[str, Any]) -> str:
    """Build a standard confirmation message for booking (configurable)."""
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    service = context.get("service", "appointment")
    slot = (context.get("selected_slot") or context.get("time") or "").strip()

    # Time range display: "09:00 – 11:00 (2h)" / "09:00" / "All day" (date-only)
    end_time   = (context.get("end_time") or "").strip()
    num_slots  = int(context.get("num_slots") or 1)
    slot_dur   = int(context.get("slot_duration_minutes") or 0)
    total_dur  = int(context.get("total_duration_minutes") or 0)
    if not slot:
        time_display = "All day"   # date-only booking (no SELECT_TIME in workflow)
    elif end_time and slot != end_time:
        total_min = total_dur or (num_slots * slot_dur if slot_dur else (num_slots * 60 if num_slots > 1 else 0))
        if total_min and total_min % 60 == 0:
            dur_label = f"{total_min // 60}h"
        elif total_min:
            dur_label = f"{total_min}min"
        else:
            dur_label = ""
        time_display = f"{slot} – {end_time}" + (f" ({dur_label})" if dur_label else "")
    else:
        time_display = slot

    prof = format_booking_party_label(
        context.get("professional"),
        context.get("service"),
        fallback="Admin / Staff",
    )
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
        time=time_display,
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
