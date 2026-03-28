# app/services/salon/appointments/id_service.py
from __future__ import annotations
from typing import Optional

from app.services.db import counters_collection
from app.services.salon.professional_service import ProfessionalService


class AppointmentIdService:
    @staticmethod
    def generate_id(
        tenant: str,
        professional: str,
        user_id: Optional[str] = None,
    ) -> str:
        source_prefix = (user_id or "SY")[:2].upper()

        prof_doc = ProfessionalService.get_professional(tenant, professional)
        if prof_doc:
            if isinstance(prof_doc, dict):
                prof_short = prof_doc.get("short_name")
            else:
                prof_short = getattr(prof_doc, "short_name", None)
        else:
            prof_short = "XX"

        if not prof_short:
            prof_short = "XX"

        col = counters_collection()
        counter_id = f"appt:{tenant}:{prof_short}"
        res = col.find_one_and_update(
            {"_id": counter_id},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True,
        )
        seq = res["seq"]
        return f"{source_prefix}-{prof_short}-{seq:04d}"
