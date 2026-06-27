"""User-facing labels for bookings — hides internal sentinels (N/A, __no_professional__)."""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.services.whatsapp.helpers import constants as WMSG

_NO_PROF_VALUES = frozenset({
    "",
    WMSG.PROF_SENTINEL_NO_PROF.lower(),
    WMSG.LABEL_AUTO_ASSIGNED.lower(),
    WMSG.LABEL_NA.lower(),
    "auto-assigned",
    "no_professional",
    "no professional",
})


def is_no_professional_name(professional: Optional[str]) -> bool:
    """True when booking is resource / no-stylist (not a real professional name)."""
    prof = str(professional or "").strip()
    if not prof:
        return True
    return prof.lower() in _NO_PROF_VALUES


def format_booking_party_label(
    professional: Optional[str] = None,
    service: Optional[str] = None,
    *,
    fallback: str = "your appointment",
) -> str:
    """Display name for stylist, court, or service — never exposes internal sentinels."""
    if not is_no_professional_name(professional):
        return str(professional).strip()
    svc = str(service or "").strip()
    if svc:
        return svc
    return fallback


def format_time_display(time_val: Optional[str]) -> str:
    t = str(time_val or "").strip()
    return t if t else "—"


def format_appt_list_party(appt: Dict[str, Any]) -> str:
    """One-line party label for appointment pick lists."""
    return format_booking_party_label(
        appt.get("professional"),
        appt.get("service"),
        fallback="Booking",
    )


def build_reschedule_confirm_prompt(appt: Dict[str, Any], date_str: str) -> str:
    """Confirm reschedule — wording adapts to stylist vs resource booking."""
    time_s = format_time_display(appt.get("time"))
    party = format_booking_party_label(appt.get("professional"), appt.get("service"))
    if is_no_professional_name(appt.get("professional")):
        if appt.get("service"):
            return (
                f"Are you sure you want to reschedule your *{party}* booking "
                f"at {time_s} on {date_str}?\n1) Yes\n2) No"
            )
        return (
            f"Are you sure you want to reschedule your appointment "
            f"at {time_s} on {date_str}?\n1) Yes\n2) No"
        )
    return WMSG.MSG_ARE_YOU_SURE_RESCHEDULE.format(
        prof=party,
        time=time_s,
        date=date_str,
    )


def build_cancel_confirm_prompt(appt: Dict[str, Any], date_str: str) -> str:
    """Confirm cancel — wording adapts to stylist vs resource booking."""
    time_s = format_time_display(appt.get("time"))
    party = format_booking_party_label(appt.get("professional"), appt.get("service"))
    if is_no_professional_name(appt.get("professional")):
        if appt.get("service"):
            return (
                f"Are you sure you want to cancel your *{party}* booking "
                f"at {time_s} on {date_str}?\n1) Yes\n2) No"
            )
        return (
            f"Are you sure you want to cancel your appointment "
            f"at {time_s} on {date_str}?\n1) Yes\n2) No"
        )
    return WMSG.MSG_ARE_YOU_SURE_CANCEL.format(
        prof=party,
        time=time_s,
        date=date_str,
    )


def build_choose_new_date_prompt(
    professional: Optional[str],
    service: Optional[str],
    *,
    is_reschedule: bool = False,
) -> str:
    """Date picker header for reschedule or new booking."""
    party = format_booking_party_label(professional, service)
    if is_reschedule:
        if is_no_professional_name(professional):
            if service:
                return f"Choose a new date for your *{party}* booking:"
            return "Choose a new date for your appointment:"
        return WMSG.MSG_CHOOSE_NEW_DATE.format(prof=party)
    return WMSG.MSG_PLEASE_CHOOSE_DATE.format(
        service=party if is_no_professional_name(professional) else (service or WMSG.LABEL_APPOINTMENT),
    )
