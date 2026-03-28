"""
AI feature gating for salon booking flows (no dependency on :mod:`booking_flow`).

Keeps :mod:`booking_timeslot_start` and :mod:`booking_fsm_handlers` from importing each other
only for tier / ``should_use_ai_in_flow`` checks.
"""


def is_ai_enabled_in_flow(tenant: str) -> bool:
    from app.services.whatsapp.tier_services import get_tier_service

    return get_tier_service(tenant).should_use_ai_in_flow()
