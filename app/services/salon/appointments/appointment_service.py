# app/services/salon/appointments/appointment_service.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
import datetime as dt

from .appointment_creator import AppointmentCreator
from .appointment_canceler import AppointmentCanceler
from .appointment_rescheduler import AppointmentRescheduler
from .appointment_status_service import AppointmentStatusService
from .listing_service import AppointmentListingService
from .snapshot_service import AppointmentSnapshotService


class AppointmentService:
    @staticmethod
    async def list_appointments(
            tenant: str,
            professional: Optional[str] = None,
            date: Optional[str] = None,
            status: Optional[str] = None,
            search_type: Optional[str] = None,
            search_value: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return await AppointmentListingService.list_appointments(
            tenant=tenant,
            professional=professional,
            date=date,
            status=status,
            search_type=search_type,
            search_value=search_value,
        )

    @staticmethod
    def get_report_snapshot(
            tenant: str,
            from_date: dt.date,
            to_date: Optional[dt.date] = None,
    ) -> Dict[str, Any]:
        return AppointmentSnapshotService.get_report_snapshot(
            tenant=tenant,
            from_date=from_date,
            to_date=to_date,
        )

    @staticmethod
    async def create_appointment(
            tenant: str,
            payload: Any,
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await AppointmentCreator.create_appointment(
            tenant=tenant,
            payload=payload,
            user_id=user_id,
        )

    @staticmethod
    async def cancel_appointment(
            tenant: str,
            appointment_id: str,
            reason: str = "canceled",
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await AppointmentCanceler.cancel_appointment(
            tenant=tenant,
            appointment_id=appointment_id,
            reason=reason,
            user_id=user_id,
        )

    @staticmethod
    async def reschedule_appointment(
            tenant: str,
            appointment_id: str,
            new_time: str,
            new_date: Optional[str] = None,
            user_id: Optional[str] = None,
            new_professional: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await AppointmentRescheduler.reschedule_appointment(
            tenant=tenant,
            appointment_id=appointment_id,
            new_time=new_time,
            new_date=new_date,
            user_id=user_id,
            new_professional=new_professional,
        )

    @staticmethod
    def update_appointment_status(
            tenant: str,
            appointment_id: str,
            status: str,
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return AppointmentStatusService.update_status(
            tenant=tenant,
            appointment_id=appointment_id,
            status=status,
            user_id=user_id,
        )
