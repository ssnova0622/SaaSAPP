# app/services/salon/appointments/followup_service.py
from __future__ import annotations
from typing import Optional

from app.services.core import followups_service


class AppointmentFollowupService:
    @staticmethod
    def schedule(
        tenant: str,
        appointment_id: str,
        customer_name: str,
        customer_phone: Optional[str],
        professional: str,
        time_label: str,
    ) -> None:
        followups_service.schedule_for_appointment(
            tenant=tenant,
            appointment_id=appointment_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=None,
            professional=professional,
            time_label=time_label,
        )

    @staticmethod
    def cancel(tenant: str, appointment_id: str) -> None:
        followups_service.cancel_for_appointment(tenant, appointment_id)
