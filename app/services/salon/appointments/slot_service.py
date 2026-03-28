# app/services/salon/appointments/slot_service.py
from __future__ import annotations
from typing import Optional
import datetime as dt

from app.services.db import collections
from app.helpers.constants import SLOT_STATUS_AVAILABLE, SLOT_STATUS_BLOCKED


class SlotService:
    @staticmethod
    def set_slot_status(
        tenant: str,
        professional: str,
        time: str,
        status: str,
        date: Optional[dt.date] = None,
    ) -> None:
        tenants_col, pros_col, _ = collections()
        if date:
            dstr = date.isoformat()
            prof = pros_col.find_one({"tenant": tenant, "name": professional})
            if not prof:
                return
            overrides = dict(prof.get("date_overrides") or {})
            day_slots = list(overrides.get(dstr) or [])
            # When no override for this date, initialize from global slots so we don't wipe other slots
            if not day_slots and prof.get("slots"):
                day_slots = [
                    {"time": s.get("time"), "status": s.get("status", SLOT_STATUS_AVAILABLE)}
                    for s in prof["slots"]
                ]
            found = False
            for s in day_slots:
                if s.get("time") == time:
                    s["status"] = status
                    found = True
                    break
            if not found:
                day_slots.append({"time": time, "status": status})
            overrides[dstr] = day_slots
            pros_col.update_one({"_id": prof["_id"]}, {"$set": {"date_overrides": overrides}})
        else:
            pros_col.update_one(
                {"tenant": tenant, "name": professional, "slots.time": time},
                {"$set": {"slots.$.status": status}},
            )

    @staticmethod
    def is_blocked(
        tenant: str,
        professional: str,
        date: dt.date,
        time: str,
    ) -> bool:
        _, pros_col, _ = collections()
        prof = pros_col.find_one(
            {"tenant": tenant, "name": professional},
            {"date_overrides": 1},
        )
        if not prof:
            return False
        overrides = prof.get("date_overrides") or {}
        day_slots = overrides.get(date.isoformat()) or []
        for s in day_slots:
            if s.get("time") == time and s.get("status") == SLOT_STATUS_BLOCKED:
                return True
        return False
