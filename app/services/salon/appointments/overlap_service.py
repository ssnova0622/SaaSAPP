# app/services/salon/appointments/overlap_service.py
from __future__ import annotations
from typing import Dict, Any, Optional
import datetime as dt

from app.services.db import collections
from app.helpers.constants import (
    APPOINTMENT_STATUS_BOOKED,
    APPOINTMENT_STATUS_COMPLETED,
    APPOINTMENT_STATUS_NEEDS_RESCHEDULE,
)


class OverlapService:
    @staticmethod
    def count_overlapping(
        tenant: str,
        professional: str,
        start_iso: str,
        end_iso: str,
        exclude_appt_id: Optional[str] = None,
    ) -> int:
        _tenants, _pros, appts_col = collections()
        try:
            d_start = dt.datetime.fromisoformat(start_iso)
            d_end = dt.datetime.fromisoformat(end_iso)
        except Exception:
            return 0

        q: Dict[str, Any] = {
            "tenant": tenant,
            "professional": professional,
            "status": {"$in": [APPOINTMENT_STATUS_BOOKED, APPOINTMENT_STATUS_COMPLETED, APPOINTMENT_STATUS_NEEDS_RESCHEDULE]},
            "$or": [
                {"start": {"$lt": d_end, "$gte": d_start}},
                {"end": {"$gt": d_start, "$lte": d_end}},
                {"start": {"$lte": d_start}, "end": {"$gte": d_end}},
            ],
        }
        if exclude_appt_id:
            q["id"] = {"$ne": exclude_appt_id}

        return appts_col.count_documents(q)
