# app/services/salon/appointments/appointment_canceler.py
from __future__ import annotations
from typing import Any, Dict, Optional
import datetime as dt
from zoneinfo import ZoneInfo

from app.services.core.tenant_service import TenantService
from app.services.core.user_service import UserService
from app.services.db import collections
from app.helpers.constants import (
    APPOINTMENT_STATUS_CANCELED,
    APPOINTMENT_STATUS_COMPLETED,
    APPOINTMENT_STATUS_NEEDS_RESCHEDULE,
    DEFAULT_TIMEZONE,
    SLOT_STATUS_AVAILABLE,
    SLOT_STATUS_BLOCKED,
)
from app.helpers.date_utils import format_date_for_tenant, utcnow
from app.helpers.phone_util import PhoneUtil
from app.core.realtime import get_notifier

from app.services.salon.slot_service import SlotService as SalonSlotService

from .followup_service import AppointmentFollowupService
from .messaging_service import AppointmentMessagingService


class AppointmentCanceler:
    @staticmethod
    async def cancel_appointment(
        tenant: str,
        appointment_id: str,
        reason: str = "canceled",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        tenants_col, pros_col, appts_col = collections()
        doc = appts_col.find_one({"tenant": tenant, "id": appointment_id})
        if not doc:
            raise ValueError("Appointment not found")

        status = (
            APPOINTMENT_STATUS_CANCELED
            if reason == APPOINTMENT_STATUS_CANCELED
            else APPOINTMENT_STATUS_NEEDS_RESCHEDULE
        )

        update_payload = {
            "status": status,
            "updated_at": utcnow(),
            "updated_by": user_id,
        }
        appts_col.update_one({"_id": doc["_id"]}, {"$set": update_payload})

        tenant_doc = TenantService.get_tenant_settings(tenant) or {}
        tz_name = tenant_doc.get("tz") or DEFAULT_TIMEZONE
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo(DEFAULT_TIMEZONE)

        if doc.get("start"):
            # When needs_reschedule, block the slot so it cannot be rebooked until rescheduled or canceled
            slot_status = SLOT_STATUS_BLOCKED if status == APPOINTMENT_STATUS_NEEDS_RESCHEDULE else SLOT_STATUS_AVAILABLE
            pro_key = (doc.get("professional_id") or "").strip() or (doc.get("professional") or "")
            if pro_key:
                SalonSlotService.set_slot_status(
                    tenant,
                    pro_key,
                    doc.get("time"),
                    slot_status,
                    date=doc.get("start").astimezone(tz).date(),
                    user_id=user_id,
                )

        if doc.get("status") == APPOINTMENT_STATUS_COMPLETED:
            price = float(doc.get("price") or 0.0)
            tenants_col.update_one({"_id": tenant}, {"$inc": {"revenue": -price}})

        try:
            AppointmentFollowupService.cancel(tenant, appointment_id)
        except Exception:
            pass

        dial = TenantService._get_tenant_country_code(tenant) or PhoneUtil.DEFAULT_DIAL_DIGITS
        cust_e164 = PhoneUtil.appointment_customer_e164(doc, dial)
        if cust_e164:
            try:
                if status == APPOINTMENT_STATUS_NEEDS_RESCHEDULE:
                    now_local = dt.datetime.now(tz)
                    today_str = now_local.date().isoformat()
                    tomorrow_str = (now_local.date() + dt.timedelta(days=1)).isoformat()
                    from app.services.whatsapp.usecases.salon.booking_flow import get_available_slots

                    prof = doc.get("professional")
                    today_slots: list = []
                    tomorrow_slots: list = []
                    if prof:
                        today_slots = await get_available_slots(
                            tenant, professional_name=prof, limit=3, date_str=today_str
                        )
                        tomorrow_slots = await get_available_slots(
                            tenant, professional_name=prof, limit=3, date_str=tomorrow_str
                        )
                    suggestion = ""
                    if today_slots:
                        suggestion += f"\nToday's slots: {', '.join(today_slots)}"
                    if tomorrow_slots:
                        suggestion += f"\nTomorrow's slots: {', '.join(tomorrow_slots)}"

                    AppointmentMessagingService.send_reschedule_prompt(
                        tenant,
                        cust_e164,
                        doc.get("professional"),
                        doc.get("time"),
                        suggestion,
                    )
                else:
                    AppointmentMessagingService.send_cancellation_prompt(
                        tenant,
                        cust_e164,
                        doc.get("professional"),
                        doc.get("time"),
                    )
            except Exception:
                pass

        user_ids = {doc.get("created_by"), user_id} - {None}
        user_names = UserService.resolve_user_names(list(user_ids)) if user_ids else {}
        created_by_name = user_names.get(doc.get("created_by")) or doc.get("created_by") or "system"
        updated_by_name = user_names.get(user_id) or user_id

        date_label = (
            format_date_for_tenant(doc.get("start").date(), tenant_doc) if doc.get("start") else None
        )

        await get_notifier().broadcast(
            {
                "type": "appointment.canceled",
                "tenant": tenant,
                "appointment": {
                    "id": appointment_id,
                    "professional": doc.get("professional"),
                    "time": doc.get("time"),
                    "status": status,
                    "date": date_label,
                    "created_by": created_by_name,
                    "updated_by": updated_by_name,
                },
            }
        )

        updated = appts_col.find_one({"tenant": tenant, "id": appointment_id})
        return {
            "id": updated["id"],
            "tenant": tenant,
            "customer_name": updated.get("customer_name", ""),
            "customer_phone": PhoneUtil.appointment_customer_e164(updated, dial),
            "professional": updated.get("professional", ""),
            "time": updated.get("time", ""),
            "date": date_label,
            "price": float(updated.get("price", 0.0)),
            "status": updated.get("status", status),
            "created_by": created_by_name,
            "updated_by": updated_by_name,
        }
