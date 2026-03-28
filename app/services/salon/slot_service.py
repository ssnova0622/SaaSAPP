# app/services/salon/slot_service.py
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from app.helpers.date_utils import utcnow, get_tz
from app.services.db import collections
from app.services.storage import Slot
from app.services.core.tenant_service import TenantService
from app.services.salon.professional_service import ProfessionalService
from app.helpers.constants import DEFAULT_TIMEZONE, APPOINTMENT_STATUS_NEEDS_RESCHEDULE, SLOT_STATUS_AVAILABLE


class SlotService:
    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------

    @staticmethod
    def set_slot_status(
        tenant: str,
        professional: str,
        time: str,
        status: str,
        date: Optional[dt.date] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """Set a single slot's status (available|blocked) for a date or today's template.
        When setting to blocked, any appointment with status needs_reschedule for this slot
        is auto-canceled: the admin block takes precedence even if the slot was scheduled by someone else."""
        pros_col = ProfessionalService._pros_col()
        settings = TenantService.get_tenant_settings(tenant) or {}
        tz = get_tz(settings.get("tz"), fallback=DEFAULT_TIMEZONE)
        now_local = dt.datetime.now(tz)
        target_date = date or now_local.date()
        target_date_str = target_date.isoformat()
        update_payload: Dict[str, Any] = {
            "updated_at": utcnow(),
            "updated_by": user_id,
        }
        if target_date == now_local.date():
            pros_col.update_one(
                {"tenant": tenant, "name": professional, "slots.time": time},
                {"$set": {"slots.$.status": status, **update_payload}},
            )
        prof_doc = pros_col.find_one({"tenant": tenant, "name": professional})
        if not prof_doc:
            return
        overrides = prof_doc.get("date_overrides") or {}
        day_slots = list(overrides.get(target_date_str) or [])
        if not day_slots and prof_doc.get("slots"):
            day_slots = [{"time": s.get("time"), "status": s.get("status", SLOT_STATUS_AVAILABLE)} for s in prof_doc["slots"]]
        found = False
        for s in day_slots:
            if s.get("time") == time:
                s["status"] = status
                found = True
                break
        if not found:
            day_slots.append({"time": time, "status": status})
        pros_col.update_one(
            {"tenant": tenant, "name": professional},
            {"$set": {f"date_overrides.{target_date_str}": day_slots, **update_payload}},
        )
        # If the slot status is blocked, we must cancel any needs_reschedule appointment for this slot,
        # because the admin is blocking the slot even if it was previously scheduled by someone else.
        if status == "blocked":
            SlotService._cancel_needs_reschedule_for_slot(
                tenant, professional, time, target_date, tz, update_payload
            )

    @staticmethod
    def _cancel_needs_reschedule_for_slot(
        tenant: str,
        professional: str,
        time: str,
        target_date: dt.date,
        tz: ZoneInfo,
        update_payload: Dict[str, Any],
    ) -> None:
        """Cancel any appointments with status needs_reschedule for the given slot (tenant, professional, time, date)."""
        _tenants, _pros, appts_col = collections()
        start_local = dt.datetime.combine(target_date, dt.time(0, 0, 0)).replace(tzinfo=tz)
        end_local = start_local + dt.timedelta(days=1)
        appts_col.update_many(
            {
                "tenant": tenant,
                "professional": professional,
                "time": time,
                "status": APPOINTMENT_STATUS_NEEDS_RESCHEDULE,
                "start": {"$gte": start_local, "$lt": end_local},
            },
            {"$set": {"status": "canceled", **update_payload}},
        )

    @staticmethod
    async def get_availability(
        tenant: str,
        professional: str,
        from_date: str,
        to_date: str,
        channel: str,
    ) -> List[Dict[str, Any]]:
        """
        Return availability slots for a professional between from_date and to_date (inclusive),
        respecting tenant settings, overrides, buffer, and channel horizon.
        """
        # Load raw document so date_overrides (blocked slots) are included; get_professional() uses a model that omits them
        pros_col = ProfessionalService._pros_col()
        p_doc = pros_col.find_one({"tenant": tenant, "name": professional})
        if not p_doc:
            raise ValueError("Professional not found")
        p_doc = dict(p_doc)
        p_doc.pop("_id", None)

        d_from, d_to = SlotService._parse_date_range(from_date, to_date)

        settings = TenantService.get_tenant_settings(tenant) or {}
        appt_cfg = (settings.get("appointments") or {}) if isinstance(settings, dict) else {}

        whatsapp_max_days = int(appt_cfg.get("whatsapp_max_days", 3) or 3)
        admin_max_days = int(appt_cfg.get("admin_max_days", 30) or 30)
        slot_duration = int(appt_cfg.get("slot_duration_minutes", 30) or 30)
        buffer_minutes = int(appt_cfg.get("buffer_minutes", 0) or 0)

        tz = SlotService._resolve_timezone(
            appt_cfg.get("timezone") or settings.get("tz") or "UTC"
        )

        horizon = whatsapp_max_days if channel == "whatsapp" else admin_max_days
        max_to = d_from + dt.timedelta(days=max(0, horizon))
        if d_to > max_to:
            d_to = max_to

        overrides = p_doc.get("date_overrides") or {}
        global_slots = SlotService._extract_global_slots(p_doc)

        now_local = dt.datetime.now(dt.timezone.utc).astimezone(tz)
        min_start = now_local + dt.timedelta(minutes=max(0, buffer_minutes))

        items: List[Dict[str, Any]] = []
        day = d_from

        while day <= d_to:
            if not SlotService._is_available_day(p_doc, day):
                day += dt.timedelta(days=1)
                continue

            dstr = day.isoformat()
            day_slots_data = overrides.get(dstr) or [
                {"time": t, "status": SLOT_STATUS_AVAILABLE} for t in global_slots
            ]
            from app.services.salon.appointments.appointment_service import AppointmentService
            booked_appts = await AppointmentService.list_appointments(
                tenant, professional=professional, date=dstr, status="booked"
            )
            needs_reschedule_appts = await AppointmentService.list_appointments(
                tenant, professional=professional, date=dstr, status="needs_reschedule"
            )
            booked_times = {a["time"] for a in booked_appts}
            needs_reschedule_times = {a["time"] for a in needs_reschedule_appts}

            for s_data in day_slots_data:
                tstr, s_status = SlotService._extract_slot_time_status(s_data)
                if not tstr:
                    continue

                start_local, end_local = SlotService._build_slot_datetimes(
                    day, tstr, tz, slot_duration
                )
                if start_local <= min_start:
                    continue

                is_booked = tstr in booked_times
                is_needs_reschedule = tstr in needs_reschedule_times
                # Slot is not bookable if booked, or if it has a needs_reschedule appointment (same as blocked)
                is_occupied = is_booked or is_needs_reschedule
                is_available = (s_status == SLOT_STATUS_AVAILABLE and not is_occupied)

                items.append(
                    {
                        "start": start_local.isoformat(),
                        "end": end_local.isoformat(),
                        "time": tstr,
                        "status": "booked" if is_booked else ("blocked" if is_needs_reschedule else s_status),
                        "bookable": is_available,
                        "capacity": 1,
                        "remaining": 0 if is_occupied or s_status == "blocked" else 1,
                        "blocked": s_status == "blocked" or is_needs_reschedule,
                    }
                )

            day += dt.timedelta(days=1)

        return items

    @staticmethod
    def update_professional_slots(
        tenant: str,
        professional: str,
        slots: List[Dict[str, Any]],
        date_str: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Any:
        """
        Convert dict slots -> Slot models and delegate to ProfessionalService.
        """
        new_slots = [
            Slot(time=s["time"], status=s.get("status", SLOT_STATUS_AVAILABLE)) for s in slots
        ]
        return ProfessionalService.update_professional_slots(
            tenant, professional, new_slots, date_str=date_str, user_id=user_id
        )

    @staticmethod
    def slot_range(
        start: int = 9,
        end: int = 17,
        step_minutes: int = 30,
    ) -> List[str]:
        """
        Return a list of time strings like `HH:MM` between `start` and `end` hours.
        `end` is exclusive (same behavior as `range`).
        """
        if step_minutes <= 0 or 60 % step_minutes != 0:
            raise ValueError("step_minutes must evenly divide 60")

        times: List[str] = []
        for h in range(start, end):
            for m in range(0, 60, step_minutes):
                times.append(f"{h:02d}:{m:02d}")
        return times

    @staticmethod
    def _slot_range(start: int = 9, end: int = 17) -> List[Any]:
        """
        Convenience wrapper returning Slot objects instead of strings.
        """
        return [Slot(time=t) for t in SlotService.slot_range(start=start, end=end, step_minutes=30)]

    # --------------------------------------------------------
    # Internal helpers
    # --------------------------------------------------------

    @staticmethod
    def _parse_date_range(from_date: str, to_date: str) -> tuple[dt.date, dt.date]:
        try:
            d_from = dt.date.fromisoformat(from_date)
            d_to = dt.date.fromisoformat(to_date)
        except Exception:
            raise ValueError("Invalid from/to date. Use YYYY-MM-DD.")

        if d_from > d_to:
            raise ValueError("from must be <= to")

        return d_from, d_to

    @staticmethod
    def _resolve_timezone(tz_name: str) -> ZoneInfo:
        try:
            return ZoneInfo(str(tz_name))
        except Exception:
            return ZoneInfo("UTC")

    @staticmethod
    def _extract_global_slots(p_doc: Dict[str, Any]) -> List[str]:
        slots_raw = p_doc.get("slots", [])
        global_slots: List[str] = []

        for s in slots_raw:
            if isinstance(s, dict):
                t = s.get("time")
            else:
                t = getattr(s, "time", None)
            if isinstance(t, str):
                global_slots.append(t)

        if not global_slots:
            global_slots = [f"{h:02d}:{m:02d}" for h in range(9, 19) for m in (0, 30)]

        return global_slots

    @staticmethod
    def _is_available_day(p_doc: Dict[str, Any], day: dt.date) -> bool:
        crit = p_doc.get("availability_criteria", "daily") or "daily"
        days_cfg = p_doc.get("available_days") or []

        if crit == "weekly" and days_cfg and day.weekday() not in days_cfg:
            return False
        if crit == "monthly" and days_cfg and day.day not in days_cfg:
            return False
        return True

    @staticmethod
    def _extract_slot_time_status(s_data: Any) -> tuple[Optional[str], str]:
        if isinstance(s_data, dict):
            tstr = s_data.get("time")
            s_status = s_data.get("status",SLOT_STATUS_AVAILABLE)
        else:
            tstr = getattr(s_data, "time", "")
            s_status = getattr(s_data, "status", SLOT_STATUS_AVAILABLE)
        return tstr, s_status

    @staticmethod
    def _build_slot_datetimes(
        day: dt.date,
        tstr: str,
        tz: ZoneInfo,
        slot_duration: int,
    ) -> tuple[dt.datetime, dt.datetime]:
        try:
            hh, mm = [int(x) for x in tstr.split(":", 1)]
        except Exception:
            raise ValueError("Invalid time format in slot")

        start_local = dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=tz)
        end_local = start_local + dt.timedelta(minutes=slot_duration)
        return start_local, end_local
