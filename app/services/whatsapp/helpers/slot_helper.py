# app/services/whatsapp/helpers/slot_helper.py
from __future__ import annotations
import datetime as dt
from typing import List
from app.services.salon.slot_service import SlotService


def get_available_slots(
        tenant: str,
        professional: str,
        date: str,
        limit: int = 6,
) -> List[str]:
    """Return available slots for a professional on a date."""
    try:
        slots_data = SlotService.slot_range()  # fallback if async fails
    except Exception:
        slots_data = []

    # Try async availability via router
    try:
        from app.routers.slots import get_availability
        slots_data = get_availability(
            tenant=tenant,
            professional=professional,
            from_date=date,
            to_date=date,
            channel="whatsapp",
        )
    except Exception:
        pass

    times = []
    for item in slots_data:
        try:
            if item.bookable:
                t = dt.datetime.fromisoformat(item.start).strftime("%H:%M")
                times.append(t)
        except Exception:
            continue

    return times[:limit]
