"""
First screen / continuation logic for the salon booking flow: ``start_timeslot_flow``.

Slot listing and professional enumeration stay on :mod:`booking_flow`; they are pulled in via a
lazy import inside :func:`start_timeslot_flow` to avoid circular imports with :mod:`booking_flow`.
Mode preservation uses :data:`booking_fsm_modes.BOOKING_FSM_MODES_KEEP_CTX`.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional

from app.core.container import get_appointment_service, get_salon_services, get_tenant_service
from app.helpers.constants import APPOINTMENT_STATUS_NEEDS_RESCHEDULE
from app.helpers.date_utils import (
    format_date_for_display,
    get_display_date_format,
    get_tenant_timezone_zoneinfo,
)
from app.services.whatsapp.helpers import constants as WMSG
from app.services.whatsapp.session_flow_service import get_session, save_session
from app.services.whatsapp.usecases.salon.booking_ai_gate import is_ai_enabled_in_flow
from app.services.whatsapp.usecases.salon.booking_ctx_utils import sync_booking_ctx_from_flow_data
from app.services.whatsapp.usecases.salon.booking_fsm_modes import BOOKING_FSM_MODES_KEEP_CTX
from app.services.whatsapp.workflow_message_helper import get_confirmation_msg

try:
    from app.services.ai import AIPredictor  # type: ignore
except Exception:
    AIPredictor = None  # type: ignore

_WORKFLOW_SESSION_KEYS = ("workflow_id", "step_idx", "waiting_for_input", "flow_data")


def _preserve_workflow_session_keys(session: Dict[str, Any], ctx: Dict[str, Any]) -> None:
    """Keep active WhatsApp workflow metadata when rebuilding booking FSM ctx."""
    prev = session.get("ctx") or {}
    for k in _WORKFLOW_SESSION_KEYS:
        if k in prev:
            ctx[k] = prev[k]


async def start_timeslot_flow(
        tenant: str,
        phone: str,
        entities: Optional[Dict[str, Any]] = None,
) -> str:
    """Initialize or continue the appointment booking flow. Returns next message."""
    from app.services.whatsapp.usecases.salon import booking_flow as bf

    get_available_slots = bf.get_available_slots
    list_professionals = bf.list_professionals

    session = get_session(tenant, phone)
    _top = session.get("ctx")
    if isinstance(_top, dict):
        sync_booking_ctx_from_flow_data(_top)
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    biz_category = str(settings.get("category") or WMSG.BIZ_CATEGORY_SALON).lower()

    appts = await get_appointment_service().list_appointments(
        tenant, search_type="phone", search_value=phone, status=APPOINTMENT_STATUS_NEEDS_RESCHEDULE
    )
    needs_reschedule_id = appts[0]["id"] if appts else None
    prompt_prefix = (
        WMSG.MSG_NEEDS_RESCHEDULE_INTRO.format(appt_id=needs_reschedule_id)
        if needs_reschedule_id
        else ""
    )

    prev_ctx = session.get("ctx") or {}
    existing_reschedule_id = prev_ctx.get("reschedule_id")
    ctx = dict(prev_ctx)
    if str(ctx.get("mode") or "").lower() not in BOOKING_FSM_MODES_KEEP_CTX:
        ctx = {"mode": "select_service", "reschedule_id": existing_reschedule_id or needs_reschedule_id}
    elif needs_reschedule_id and not existing_reschedule_id:
        ctx["reschedule_id"] = needs_reschedule_id

    if entities:
        if entities.get("service"):
            ctx["service"] = entities["service"]
            if ctx["mode"] == "select_service":
                ctx["mode"] = "select_date"
        prof_name = entities.get("professional_name")
        if prof_name and AIPredictor and is_ai_enabled_in_flow(tenant):
            try:
                matches = AIPredictor().search_professionals(tenant, prof_name)
                if matches:
                    ctx["professional"] = matches[0].get("name")
            except Exception:
                pass
        target_date = entities.get("date")
        date_marker = entities.get("date_marker")
        tz = get_tenant_timezone_zoneinfo(settings)
        today = dt.datetime.now(tz).date()
        if target_date:
            ctx["date"] = target_date
        elif date_marker == "today":
            ctx["date"] = today.isoformat()
        elif date_marker == "tomorrow":
            ctx["date"] = (today + dt.timedelta(days=1)).isoformat()
        if ctx.get("date"):
            if ctx.get("reschedule_id"):
                ctx["mode"] = "select_slot" if ctx.get("professional") else "select_prof_new"
            elif ctx.get("service"):
                ctx["mode"] = "select_slot" if ctx.get("professional") else "select_prof_new"
            else:
                ctx["mode"] = "select_service"

    _preserve_workflow_session_keys(session, ctx)
    session["ctx"] = ctx
    save_session(tenant, phone, session)

    if ctx["mode"] == "select_service":
        if ctx.get("skip_services") and not ctx.get("force_services"):
            ctx["mode"] = "select_date"
            save_session(tenant, phone, session)
            return await start_timeslot_flow(tenant, phone)
        if ctx.get("service"):
            ctx["mode"] = "select_date"
            save_session(tenant, phone, session)
            return await start_timeslot_flow(tenant, phone)
        db_services = get_salon_services().list_services(tenant)
        if db_services:
            services = [s["name"] for s in db_services if s.get("active", True)]
        else:
            if not ctx.get("force_services"):
                ctx["mode"] = "select_date"
                save_session(tenant, phone, session)
                return await start_timeslot_flow(tenant, phone)
            if biz_category == WMSG.BIZ_CATEGORY_CLINIC:
                services = list(WMSG.BOOKING_SERVICES_FALLBACK_CLINIC)
            elif biz_category == WMSG.BIZ_CATEGORY_CAR_SHOWROOM:
                services = list(WMSG.BOOKING_SERVICES_FALLBACK_SHOWROOM)
            else:
                services = list(WMSG.BOOKING_SERVICES_FALLBACK_SALON)
        lines = [WMSG.MSG_BOOKING_SERVICE_PROMPT.format(prefix=prompt_prefix)]
        for i, s in enumerate(services, start=1):
            lines.append(f"{i}) {s}")
        ctx["available_services"] = services
        save_session(tenant, phone, session)
        return "\n".join(lines)

    if not ctx.get("date") and ctx["mode"] in ("select_date", "select_prof_new", "select_slot"):
        if ctx.get("skip_timeslot") and not ctx.get("force_timeslot"):
            tz = get_tenant_timezone_zoneinfo(settings)
            today = dt.datetime.now(tz).date()
            ctx["date"] = today.isoformat()
            ctx["selected_slot"] = WMSG.BOOKING_SLOT_SKIP_ANYTIME
            ctx["mode"] = "confirm_booking"
            save_session(tenant, phone, session)
            return get_confirmation_msg(tenant, ctx)
        if ctx.get("mode") == "select_prof_new" and ctx.get("skip_services"):
            pros = list_professionals(tenant, service=ctx.get("service"))
            if pros:
                ctx["professionals"] = pros
                save_session(tenant, phone, session)
                lines = [WMSG.MSG_DO_YOU_PREFER_STAFF]
                for i, name in enumerate(pros, start=1):
                    lines.append(f"{i}) {name}")
                # lines.append(f"{len(pros) + 1}) {WMSG.MSG_NO_AUTO_ASSIGN}")
                return "\n".join(lines)
        ctx["mode"] = "select_date"
        save_session(tenant, phone, session)
        tz = get_tenant_timezone_zoneinfo(settings)
        today = dt.datetime.now(tz).date()
        tomorrow = today + dt.timedelta(days=1)
        today_fmt = format_date_for_display(today, settings)
        tomorrow_fmt = format_date_for_display(tomorrow, settings)
        preferred_format = get_display_date_format(settings)
        if ctx.get("reschedule_id") and ctx.get("professional"):
            date_prompt = WMSG.MSG_CHOOSE_NEW_DATE.format(prof=ctx.get("professional"))
        else:
            date_prompt = WMSG.MSG_PLEASE_CHOOSE_DATE.format(
                service=ctx.get("service", WMSG.LABEL_APPOINTMENT),
            )
        lines = [
            date_prompt,
            WMSG.MSG_DATE_ROW_TODAY.format(display=today_fmt),
            WMSG.MSG_DATE_ROW_TOMORROW.format(display=tomorrow_fmt),
            WMSG.MSG_DATE_ROW_OTHER.format(fmt=preferred_format),
        ]
        return "\n".join(lines)

    if ctx.get("date"):
        if ctx.get("skip_professional") and not ctx.get("force_professionals"):
            ctx["professional"] = WMSG.LABEL_AUTO_ASSIGNED
            return await start_timeslot_flow(tenant, phone)
        pros = list_professionals(tenant, date_str=ctx["date"], service=ctx.get("service"))
        if not pros:
            ctx["mode"] = "select_date"
            save_session(tenant, phone, session)
            return WMSG.MSG_NO_PROFESSIONALS_DATE.format(
                date=ctx["date"],
                service=ctx.get("service", WMSG.MSG_REQUESTED_SERVICE_FALLBACK),
            )
        if ctx.get("professional"):
            if ctx.get("professional") == WMSG.LABEL_AUTO_ASSIGNED:
                for p in pros:
                    slots = await get_available_slots(tenant, professional_name=p, date_str=ctx["date"])
                    if slots:
                        ctx["professional"] = p
                        break
                else:
                    return WMSG.MSG_NO_SLOTS_ANY_PROFESSIONAL.format(date=ctx["date"])
            slots = await get_available_slots(tenant, professional_name=ctx["professional"], date_str=ctx["date"])
            if slots:
                ctx["mode"] = "select_slot"
                ctx["available_slots"] = slots
                save_session(tenant, phone, session)
                lines = [WMSG.MSG_AVAILABLE_TIME_SLOTS_ON.format(prof=ctx["professional"], date=ctx["date"])]
                for i, time in enumerate(slots, start=1):
                    lines.append(f"{i}) {time}")
                lines.append(WMSG.MSG_REPLY_CHOOSE_SLOT_MULTILINE)
                return "\n".join(lines)
            ctx["mode"] = "select_prof_new"
            ctx["professionals"] = pros
            save_session(tenant, phone, session)
            lines = [WMSG.MSG_NO_SLOTS_FOR_PROFESSIONAL.format(prof=ctx["professional"], date=ctx["date"])]
            for i, name in enumerate(pros, start=1):
                lines.append(f"{i}) {name}")
            return "\n".join(lines)
        else:
            ctx["mode"] = "select_prof_new"
            ctx["professionals"] = pros
            save_session(tenant, phone, session)
            lines = [WMSG.MSG_DO_YOU_PREFER_STAFF]
            for i, name in enumerate(pros, start=1):
                lines.append(f"{i}) {name}")
            # lines.append(f"{len(pros) + 1}) {WMSG.MSG_NO_AUTO_ASSIGN}")
            return "\n".join(lines)

    return WMSG.MSG_SOMETHING_WENT_WRONG
