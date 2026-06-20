# app/services/salon/appointments/overlap_service.py
from __future__ import annotations
from typing import Dict, Any, Optional
import datetime as dt

from app.services.db import collections
from app.services.salon.professional_service import ProfessionalService
from app.helpers.constants import (
    APPOINTMENT_STATUS_BOOKED,
    APPOINTMENT_STATUS_COMPLETED,
    APPOINTMENT_STATUS_NEEDS_RESCHEDULE,
)


class OverlapService:
    @staticmethod
    def count_overlapping(
        tenant: str,
        professional_key: str,
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

        try:
            prof_doc = ProfessionalService.resolve_professional_raw(tenant, professional_key)
            match = ProfessionalService.appointment_match_query(prof_doc)
        except ValueError:
            return 0

        time_or = [
            {"start": {"$lt": d_end, "$gte": d_start}},
            {"end": {"$gt": d_start, "$lte": d_end}},
            {"start": {"$lte": d_start}, "end": {"$gte": d_end}},
        ]
        status_q = {
            "status": {"$in": [APPOINTMENT_STATUS_BOOKED, APPOINTMENT_STATUS_COMPLETED, APPOINTMENT_STATUS_NEEDS_RESCHEDULE]},
        }
        if "$or" in match:
            q: Dict[str, Any] = {
                "tenant": tenant,
                **status_q,
                "$and": [
                    match,
                    {"$or": time_or},
                ],
            }
        else:
            q = {
                "tenant": tenant,
                **match,
                **status_q,
                "$or": time_or,
            }
        if exclude_appt_id:
            q["id"] = {"$ne": exclude_appt_id}

        return appts_col.count_documents(q)

    @staticmethod
    def count_service_overlapping(
        tenant: str,
        service_name: str,
        start_iso: str,
        end_iso: str,
        exclude_appt_id: Optional[str] = None,
    ) -> int:
        """Count bookings for a shared resource (court/room) identified by service name
        that overlap with [start_iso, end_iso).

        Used when there is no dedicated professional — the service itself is the resource
        (e.g. 'Badminton Court', 'Meeting Room A').  Prevents double-booking of courts /
        shared spaces across no-professional bookings.
        """
        _tenants, _pros, appts_col = collections()
        try:
            d_start = dt.datetime.fromisoformat(start_iso)
            d_end   = dt.datetime.fromisoformat(end_iso)
        except Exception:
            return 0

        # Half-open interval overlap: existing [A,B) overlaps proposed [S,E) when A < E and S < B
        time_or = [
            {"start": {"$lt": d_end},  "end": {"$gt": d_start}},
        ]
        # Query ALL bookings for this service (regardless of professional field).
        # For courts / shared resources the service name IS the unique resource identifier.
        q: Dict[str, Any] = {
            "tenant":  tenant,
            "service": service_name,
            "status": {"$in": [APPOINTMENT_STATUS_BOOKED, APPOINTMENT_STATUS_NEEDS_RESCHEDULE]},
            "$and": [{"$or": time_or}],
        }
        if exclude_appt_id:
            q["id"] = {"$ne": exclude_appt_id}

        return appts_col.count_documents(q)
