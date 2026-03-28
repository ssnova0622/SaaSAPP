# app/services/salon/appointments/appointment_rescheduler.py
from __future__ import annotations
from typing import Dict, Any, Optional
import datetime as dt
from zoneinfo import ZoneInfo

from app.services.core.tenant_service import TenantService
from app.services.core.user_service import UserService
from app.services.db import collections
from app.helpers.constants import SLOT_STATUS_BLOCKED, DEFAULT_TIMEZONE, SLOT_STATUS_AVAILABLE
from app.helpers.date_utils import format_date_for_tenant, utcnow
from app.core.realtime import get_notifier

from .overlap_service import OverlapService
from .slot_service import SlotService
from .messaging_service import AppointmentMessagingService


class AppointmentRescheduler:
    @staticmethod
    async def reschedule_appointment(
        tenant: str,
        appointment_id: str,
        new_time: str,
        new_date: Optional[str] = None,
        user_id: Optional[str] = None,
        new_professional: Optional[str] = None,
    ) -> Dict[str, Any]:
        tenants_col, pros_col, appts_col = collections()
        doc = appts_col.find_one({"tenant": tenant, "id": appointment_id})
        if not doc:
            raise ValueError("Appointment not found")

        tenant_doc = TenantService.get_tenant_settings(tenant) or {}
        tz_name = tenant_doc.get("tz") or DEFAULT_TIMEZONE
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo(DEFAULT_TIMEZONE)

        stored_professional = doc.get("professional")

        if doc.get("start"):
            SlotService.set_slot_status(
                tenant,
                stored_professional,
                doc.get("time"),
                SLOT_STATUS_AVAILABLE,
                date=doc.get("start").astimezone(tz).date(),
            )

        appt_settings = (tenant_doc.get("appointments") or {}) if isinstance(tenant_doc, dict) else {}
        slot_duration = int(appt_settings.get("slot_duration_minutes", 30) or 30)

        if new_date:
            try:
                d = dt.date.fromisoformat(new_date)
            except Exception:
                raise ValueError("Invalid date_str. Use YYYY-MM-DD.")
        else:
            d = dt.datetime.now(tz).date()

        try:
            hh, mm = [int(x) for x in new_time.split(":", 1)]
            start_local = dt.datetime(d.year, d.month, d.day, hh, mm, tzinfo=tz)
            end_local = start_local + dt.timedelta(minutes=slot_duration)
        except Exception:
            raise ValueError("Invalid time format. Use HH:MM.")

        override = (new_professional or "").strip()
        professional = override or stored_professional
        prof_doc = pros_col.find_one(
            {"tenant": tenant, "name": professional},
            {"active": 1, "capacity": 1, "price": 1},
        )
        if not prof_doc:
            raise ValueError("Professional not found")

        cap = int(prof_doc.get("capacity", 1) or 1)
        prof_doc_full = pros_col.find_one(
            {"tenant": tenant, "name": professional},
            {"date_overrides": 1},
        )
        overrides = (prof_doc_full.get("date_overrides") or {}) if prof_doc_full else {}
        target_date_str = d.isoformat()
        day_slots = overrides.get(target_date_str) or []
        target_slot = next((s for s in day_slots if s.get("time") == new_time), None)
        if target_slot and target_slot.get("status") == SLOT_STATUS_BLOCKED:
            raise ValueError("Slot is blocked and cannot be booked")

        overlaps = OverlapService.count_overlapping(
            tenant,
            professional,
            start_local.isoformat(),
            end_local.isoformat(),
            exclude_appt_id=appointment_id,
        )
        if overlaps >= cap:
            raise ValueError("New slot already booked (capacity reached)")

        is_today = d == dt.datetime.now(tz).date()
        if is_today:
            pros_col.update_one(
                {
                    "tenant": tenant,
                    "name": professional,
                    "slots": {"$elemMatch": {"time": new_time, "status": SLOT_STATUS_AVAILABLE}},
                },
                {"$set": {"slots.$.status": "booked"}},
            )

        now = utcnow()
        update_fields: Dict[str, Any] = {
            "time": new_time,
            "start": start_local,
            "end": end_local,
            "updated_at": now,
            "updated_by": user_id,
        }
        if professional != stored_professional:
            update_fields["professional"] = professional
            update_fields["price"] = float((prof_doc or {}).get("price", 0.0) or 0.0)

        appts_col.update_one(
            {"_id": doc["_id"]},
            {"$set": update_fields},
        )

        date_str = format_date_for_tenant(start_local.date(), tenant_doc)
        if doc.get("customer_phone"):
            try:
                AppointmentMessagingService.send_rescheduled(
                    tenant,
                    doc.get("customer_phone"),
                    professional,
                    new_time,
                    date_str,
                )
            except Exception:
                pass

        user_ids = {doc.get("created_by"), user_id} - {None}
        user_names = UserService.resolve_user_names(list(user_ids)) if user_ids else {}
        created_by_name = user_names.get(doc.get("created_by")) or doc.get("created_by") or "system"
        updated_by_name = user_names.get(user_id) or user_id

        await get_notifier().broadcast(
            {
                "type": "appointment.rescheduled",
                "tenant": tenant,
                "appointment": {
                    "id": appointment_id,
                    "professional": professional,
                    "time": new_time,
                    "status": doc.get("status"),
                    "date": date_str,
                    "created_by": created_by_name,
                    "updated_by": updated_by_name,
                },
            }
        )

        updated = appts_col.find_one({"_id": doc["_id"]})
        return {
            "id": str(updated.get("id") or updated.get("_id") or appointment_id),
            "tenant": tenant,
            "customer_name": str(updated.get("customer_name") or ""),
            "customer_phone": str(updated.get("customer_phone") or ""),
            "professional": professional,
            "time": new_time,
            "date": date_str,
            "price": float(updated.get("price", 0.0)),
            "status": str(updated.get("status") or ""),
            "created_by": created_by_name,
            "updated_by": updated_by_name,
        }
