# app/services/salon/appointments/appointment_creator.py
from __future__ import annotations
from typing import Any, Dict, Optional
import datetime as dt
from zoneinfo import ZoneInfo

from app.services.core.tenant_service import TenantService
from app.services.core.user_service import UserService
from app.services.db import collections
from app.services.storage import Appointment
from app.helpers.date_utils import format_date_for_tenant, utcnow
from app.helpers.phone_utils import normalize_phone
from app.helpers.constants import APPOINTMENT_STATUS_BOOKED, DEFAULT_TIMEZONE
from app.core.realtime import get_notifier

from app.services.salon.professional_service import ProfessionalService

from .id_service import AppointmentIdService
from .overlap_service import OverlapService
from .followup_service import AppointmentFollowupService


class AppointmentCreator:
    @staticmethod
    async def create_appointment(
        tenant: str,
        payload: Any,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if isinstance(payload, dict):
            customer_name = payload.get("customer_name")
            customer_phone = payload.get("customer_phone")
            professional = payload.get("professional")
            professional_id_hint = (payload.get("professional_id") or "").strip() or None
            time = payload.get("time")
            date_str = payload.get("date")
            service = payload.get("service")
        else:
            customer_name = getattr(payload, "customer_name", None)
            customer_phone = getattr(payload, "customer_phone", None)
            professional = getattr(payload, "professional", None)
            professional_id_hint = (getattr(payload, "professional_id", None) or "").strip() or None
            time = getattr(payload, "time", None)
            date_str = getattr(payload, "date", None)
            service = getattr(payload, "service", None)

        tenants_col, pros_col, appts_col = collections()
        settings = TenantService.get_tenant_settings(tenant) or {}
        appt_settings = (settings.get("appointments") or {}) if isinstance(settings, dict) else {}
        slot_duration = int(appt_settings.get("slot_duration_minutes", 30) or 30)

        tz_name = str(appt_settings.get("timezone") or settings.get("tz") or DEFAULT_TIMEZONE)
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo(DEFAULT_TIMEZONE)

        if date_str:
            try:
                d = dt.date.fromisoformat(date_str)
            except Exception:
                raise ValueError("Invalid date_str. Use YYYY-MM-DD.")
        else:
            d = dt.datetime.now(tz).date()

        try:
            hh, mm = [int(x) for x in time.split(":", 1)]
            start_local = dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz)
            end_local = start_local + dt.timedelta(minutes=slot_duration)
        except Exception:
            raise ValueError("Invalid time format. Use HH:MM.")

        pro_key = professional_id_hint or (professional or "").strip()
        if not pro_key:
            raise ValueError("Professional not found")
        prof_doc = ProfessionalService.resolve_professional_raw(tenant, pro_key)
        if not bool(prof_doc.get("active", True)):
            raise ValueError("Professional is inactive")

        cap = int(prof_doc.get("capacity", 1) or 1)
        overlaps = OverlapService.count_overlapping(
            tenant,
            str(prof_doc.get("professional_id") or pro_key),
            start_local.isoformat(),
            end_local.isoformat(),
        )
        if overlaps >= cap:
            raise ValueError("Slot already booked (capacity reached)")

        cc = TenantService._get_tenant_country_code(tenant)
        normalized_phone = normalize_phone(customer_phone, country_code=cc)

        # Block booking if customer has too many no-shows (only when AI no-show is enabled)
        try:
            from app.services.ai.feature_gate import is_ai_capability_enabled
            from .no_show_block_service import is_blocked
            if is_ai_capability_enabled(tenant, "ai.no_show") and is_blocked(tenant, normalized_phone):
                raise ValueError(
                    "Booking blocked: this phone number has too many no-shows. "
                    "Please contact the salon or use the Blocked list in Admin to reset if appropriate."
                )
        except ValueError:
            raise
        except Exception:
            pass

        price = float(prof_doc.get("price", 0.0))
        prof_name = str(prof_doc.get("name") or professional or "")
        prof_pid = str(prof_doc.get("professional_id") or "")
        new_id = AppointmentIdService.generate_id(tenant, prof_pid or prof_name, user_id)

        appt = Appointment(
            id=new_id,
            customer_name=customer_name,
            customer_phone=normalized_phone,
            professional=prof_name,
            time=time,
            price=price,
            status=APPOINTMENT_STATUS_BOOKED,
            created_at= utcnow(),
            created_by=user_id,
            start=start_local,
            end=end_local,
            professional_id=prof_pid or None,
        )
        appts_col.insert_one(
            {
                "tenant": tenant,
                "id": appt.id,
                "customer_name": appt.customer_name,
                "customer_phone": appt.customer_phone,
                "professional": appt.professional,
                "professional_id": appt.professional_id,
                "time": appt.time,
                "price": appt.price,
                "status": appt.status,
                "created_at": appt.created_at,
                "created_by": appt.created_by,
                "updated_by": appt.created_by,
                "start": appt.start,
                "end": appt.end,
                "service": service,
            }
        )

        try:
            AppointmentFollowupService.schedule(
                tenant=tenant,
                appointment_id=appt.id,
                customer_name=appt.customer_name,
                customer_phone=appt.customer_phone,
                professional=appt.professional,
                time_label=appt.time,
            )
        except Exception:
            pass

        try:
            from app.services.core.customer_service import CustomerService

            CustomerService.ensure_customer_if_absent(
                tenant,
                str(customer_name or "").strip(),
                normalized_phone,
                user_id=user_id,
            )
        except Exception:
            pass

        user_ids = {appt.created_by} - {None}
        user_names = UserService.resolve_user_names(list(user_ids)) if user_ids else {}
        created_by_name = user_names.get(appt.created_by) or appt.created_by or "system"
        updated_by_name = created_by_name

        date_label = format_date_for_tenant(appt.start.date(), settings) if appt.start else None

        await get_notifier().broadcast(
            {
                "type": "appointment.created",
                "tenant": tenant,
                "appointment": {
                    "id": appt.id,
                    "customer_name": appt.customer_name,
                    "customer_phone": appt.customer_phone,
                    "professional": appt.professional,
                    "time": appt.time,
                    "price": appt.price,
                    "status": appt.status,
                    "date": date_label,
                    "created_by": created_by_name,
                    "updated_by": updated_by_name,
                },
            }
        )

        return {
            "id": appt.id,
            "tenant": tenant,
            "customer_name": appt.customer_name,
            "customer_phone": appt.customer_phone,
            "professional": appt.professional,
            "professional_id": appt.professional_id,
            "time": appt.time,
            "date": date_label,
            "price": appt.price,
            "status": appt.status,
            "created_by": created_by_name,
            "updated_by": updated_by_name,
        }
