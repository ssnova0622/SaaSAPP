# app/services/salon/appointments/messaging_service.py
from __future__ import annotations
import datetime as dt
from typing import Any, Dict
from zoneinfo import ZoneInfo
from datetime import timezone, timedelta

from app.helpers.constants import DEFAULT_TIMEZONE, APPOINTMENT_STATUS_NEEDS_RESCHEDULE
from app.services.core.messaging_service import Messaging


class AppointmentMessagingService:
    @staticmethod
    async def build_cancel_notification_message(tenant: str, appt: Dict[str, Any]) -> str:
        """Build WhatsApp message for after cancel: needs_reschedule (with slot suggestions) or canceled."""
        from app.core.container import get_tenant_service
        professional = appt.get("professional") or ""
        time_label = appt.get("time") or ""
        if appt.get("status") == APPOINTMENT_STATUS_NEEDS_RESCHEDULE:
            settings = get_tenant_service().get_tenant_settings(tenant) or {}
            tz_name = (settings.get("tz") or DEFAULT_TIMEZONE).strip()
            try:
                tz = ZoneInfo(tz_name)
            except Exception:
                tz = timezone(timedelta(hours=5, minutes=30))
            now_local = dt.datetime.now(tz)
            today_str = now_local.date().isoformat()
            tomorrow_str = (now_local.date() + dt.timedelta(days=1)).isoformat()
            from app.services.whatsapp.usecases.salon.salon_actions import SalonActions

            today_slots = await SalonActions.get_available_slots(
                tenant, professional_name=professional, limit=3, date_str=today_str
            )
            tomorrow_slots = await SalonActions.get_available_slots(
                tenant, professional_name=professional, limit=3, date_str=tomorrow_str
            )
            suggestion = ""
            if today_slots:
                suggestion += f"\nToday's slots: {', '.join(today_slots)}"
            if tomorrow_slots:
                suggestion += f"\nTomorrow's slots: {', '.join(tomorrow_slots)}"
            return f"Your appointment with {professional} at {time_label} needs to be rescheduled.{suggestion}\n\nPlease reply with 'menu' to pick a new timing."
        return f"Your appointment with {professional} at {time_label} has been canceled. Would you like to reschedule? Please reply with 'menu' to see available timings."


    @staticmethod
    def send_reschedule_prompt(
        tenant: str,
        customer_phone: str,
        professional: str,
        time: str,
        suggestion: str,
    ) -> None:
        msg = (
            f"Your appointment with {professional} at {time} needs to be rescheduled."
            f"{suggestion}\n\nPlease reply with 'menu' to pick a new timing."
        )
        Messaging.send_whatsapp_text(customer_phone, msg, tenant=tenant)

    @staticmethod
    def send_cancellation_prompt(
        tenant: str,
        customer_phone: str,
        professional: str,
        time: str,
    ) -> None:
        msg = (
            f"Your appointment with {professional} at {time} has been canceled. "
            "Would you like to reschedule? Please reply with 'menu' to see available timings."
        )
        Messaging.send_whatsapp_text(customer_phone, msg, tenant=tenant)

    @staticmethod
    def send_rescheduled(
        tenant: str,
        customer_phone: str,
        professional: str,
        time: str,
        date_str: str,
    ) -> None:
        msg = f"Your appointment with {professional} has been rescheduled to {time} on {date_str}."
        Messaging.send_whatsapp_text(customer_phone, msg, tenant=tenant)
