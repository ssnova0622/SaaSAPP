# app/services/salon/appointments/snapshot_service.py
from __future__ import annotations
from typing import Dict, Any, Optional
import datetime as dt

from app.services.db import collections
from app.helpers.constants import (
    APPOINTMENT_STATUS_BOOKED,
    APPOINTMENT_STATUS_CANCELED,
    APPOINTMENT_STATUS_COMPLETED,
)


class AppointmentSnapshotService:
    @staticmethod
    def get_report_snapshot(
        tenant: str,
        from_date: dt.date,
        to_date: Optional[dt.date] = None,
    ) -> Dict[str, Any]:
        _tenants, _pros, appts_col = collections()
        d_start = dt.datetime.combine(from_date, dt.time.min)
        d_end = dt.datetime.combine(to_date or from_date, dt.time.max)

        cursor = appts_col.find(
            {
                "tenant": tenant,
                "created_at": {"$gte": d_start, "$lte": d_end},
            }
        )
        appts = list(cursor)

        booked = [a for a in appts if a.get("status") == APPOINTMENT_STATUS_BOOKED]
        canceled = [a for a in appts if a.get("status") == APPOINTMENT_STATUS_CANCELED]
        completed = [a for a in appts if a.get("status") == APPOINTMENT_STATUS_COMPLETED]
        revenue = sum(float(a.get("price", 0.0)) for a in completed)

        return {
            "total_new_bookings": len(booked) + len(completed),
            "cancellations": len(canceled),
            "completed": len(completed),
            "revenue": round(revenue, 2),
            "date_range": [from_date.isoformat(), (to_date or from_date).isoformat()],
        }
