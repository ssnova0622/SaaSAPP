"""
Booking FSM mode handlers (one message → reply). Extracted from :mod:`booking_flow` for readability.

Uses lazy imports of :mod:`booking_flow` for ``start_timeslot_flow``, ``get_available_slots``,
and ``_finalize_booking`` to avoid circular imports at module load time.
``is_ai_enabled_in_flow`` is re-exported from :mod:`booking_ai_gate`.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from app.core.container import get_customer_service, get_tenant_service
from app.helpers.constants_capabilities import CAP_AI_APPOINTMENT_RECS
from app.helpers.date_utils import (
    format_date_for_display,
    get_display_date_format,
    get_tenant_timezone_zoneinfo,
    parse_user_date_input,
)
from app.services.core import message_templates as msg_tpl
from app.services.whatsapp.helpers import constants as WMSG
from app.services.whatsapp.session_flow_service import reset_session_to_root, save_session
from app.services.whatsapp.usecases.salon.booking_ai_gate import is_ai_enabled_in_flow
from app.services.whatsapp.usecases.salon.booking_time_utils import (
    format_time_12h,
    parse_time_input,
    slots_near_time,
)
from app.services.whatsapp.usecases.utils import choice_to_index, parse_yes_no
from app.services.whatsapp.workflow_message_helper import get_confirmation_msg

try:
    from app.services.ai import AIPredictor  # type: ignore
except Exception:
    AIPredictor = None  # type: ignore

try:
    from app.services.ai.feature_gate import is_ai_capability_enabled
except Exception:
    def is_ai_capability_enabled(tenant: str, capability: str) -> bool:
        return False


async def handle_fsm_back(
        tenant: str,
        phone: str,
        session: Dict[str, Any],
        ctx: Dict[str, Any],
        mode: str,
        tree: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Handle ``back`` keyword; return a reply or ``None`` if this mode ignores back."""
    if mode == "select_date":
        ctx["mode"] = "select_service"
        save_session(tenant, phone, session)
        from app.services.whatsapp.usecases.salon.booking_flow import start_timeslot_flow

        return await start_timeslot_flow(tenant, phone)
    if mode in ("select_prof_new", "select_prof"):
        ctx["mode"] = "select_date"
        save_session(tenant, phone, session)
        from app.services.whatsapp.usecases.salon.booking_flow import start_timeslot_flow

        return await start_timeslot_flow(tenant, phone)
    if mode == "select_slot":
        pros = ctx.get("professionals")
        if pros and len(pros) > 1:
            ctx["mode"] = "select_prof_new"
            save_session(tenant, phone, session)
            lines = [WMSG.MSG_DO_YOU_PREFER_STAFF]
            for i, name in enumerate(pros, start=1):
                lines.append(f"{i}) {name}")
            lines.append(f"{len(pros) + 1}) {WMSG.MSG_NO_AUTO_ASSIGN}")
            return "\n".join(lines)
        ctx["mode"] = "select_date"
        save_session(tenant, phone, session)
        from app.services.whatsapp.usecases.salon.booking_flow import start_timeslot_flow

        return await start_timeslot_flow(tenant, phone)
    if mode == "confirm_booking":
        ctx["mode"] = "select_slot"
        save_session(tenant, phone, session)
        slots = ctx.get("available_slots") or []
        prof = ctx.get("professional") or ""
        lines = [WMSG.MSG_AVAILABLE_TIME_SLOTS.format(prof=prof)]
        for i, time in enumerate(slots, start=1):
            lines.append(f"{i}) {time}")
        lines.append(WMSG.MSG_REPLY_NUMBER_CHOOSE_SLOT)
        return "\n".join(lines)
    if mode == "ask_name":
        ctx["mode"] = "confirm_booking"
        save_session(tenant, phone, session)
        return get_confirmation_msg(tenant, ctx)
    return None


async def dispatch_booking_fsm_mode(
        tenant: str,
        phone: str,
        session: Dict[str, Any],
        ctx: Dict[str, Any],
        mode: str,
        input_text: str,
        norm_input: str,
        tree: Optional[Dict[str, Any]],
) -> Optional[str]:
    from app.services.whatsapp.usecases.salon.booking_flow import (
        get_available_slots,
        start_timeslot_flow,
        _finalize_booking,
        _reprompt_reschedule_confirm,
    )

    if mode == "select_service":
        services = ctx.get("available_services") or []
        idx = choice_to_index(input_text)
        if 1 <= (idx or 0) <= len(services):
            ctx["service"] = services[idx - 1]
            ctx["mode"] = "select_date"
            save_session(tenant, phone, session)
            return await start_timeslot_flow(tenant, phone)
        return WMSG.MSG_PLEASE_CHOOSE_SERVICE

    if mode == "select_date":
        settings = get_tenant_service().get_tenant_settings(tenant) or {}
        tz = get_tenant_timezone_zoneinfo(settings)
        today = dt.datetime.now(tz).date()
        chosen_date_str = ""
        idx = choice_to_index(input_text)
        if idx == 1:
            chosen_date_str = today.isoformat()
        elif idx == 2:
            chosen_date_str = (today + dt.timedelta(days=1)).isoformat()
        else:
            preferred_format = get_display_date_format(settings)
            parsed_date = parse_user_date_input(input_text, settings)
            if not parsed_date:
                return WMSG.MSG_INVALID_DATE_FORMAT.format(fmt=preferred_format)
            if parsed_date < today:
                return WMSG.MSG_DATE_IN_PAST.format(
                    date=format_date_for_display(parsed_date, settings),
                )
            chosen_date_str = parsed_date.isoformat()
        ctx["date"] = chosen_date_str
        save_session(tenant, phone, session)
        return await start_timeslot_flow(tenant, phone, entities={"date": chosen_date_str})

    if mode == "select_prof_new":
        pros = ctx.get("professionals") or []
        idx = choice_to_index(input_text)
        if idx == len(pros) + 1:
            ctx["professional"] = pros[0]
            ctx["mode"] = "select_slot"
            save_session(tenant, phone, session)
            return await start_timeslot_flow(tenant, phone)
        if not idx or idx < 1 or idx > len(pros):
            lines = [WMSG.MSG_PLEASE_CHOOSE_PROFESSIONAL]
            for i, name in enumerate(pros, start=1):
                lines.append(f"{i}) {name}")
            lines.append(f"{len(pros) + 1}) {WMSG.MSG_NO_AUTO_ASSIGN}")
            return "\n".join(lines)
        chosen_prof = pros[idx - 1]
        date_str = ctx.get("date")
        slots = await get_available_slots(tenant, chosen_prof, date_str=date_str)
        if not slots:
            return WMSG.MSG_NO_SLOTS_PRO_OR_DATE.format(prof=chosen_prof, date=date_str)
        settings = get_tenant_service().get_tenant_settings(tenant) or {}
        date_fmt = format_date_for_display(dt.date.fromisoformat(date_str), settings) if date_str else date_str
        ctx.update({"mode": "select_slot", "professional": chosen_prof, "available_slots": slots})
        save_session(tenant, phone, session)
        lines = [WMSG.MSG_AVAILABLE_TIME_SLOTS_ON.format(prof=chosen_prof, date=date_fmt)]
        for i, time in enumerate(slots, start=1):
            lines.append(f"{i}) {time}")
        lines.append(WMSG.MSG_REPLY_CHOOSE_SLOT_MULTILINE)
        return "\n".join(lines)

    if mode == "select_prof":
        pros = ctx.get("professionals") or []
        idx = choice_to_index(input_text)
        if not idx or idx < 1 or idx > len(pros):
            lines = [WMSG.MSG_PLEASE_CHOOSE_PROFESSIONAL]
            for i, name in enumerate(pros, start=1):
                lines.append(f"{i}) {name}")
            return "\n".join(lines)
        chosen_prof = pros[idx - 1]
        slots = await get_available_slots(tenant, chosen_prof)
        if not slots:
            return WMSG.MSG_NO_SLOTS_PROFESSIONAL_NOW.format(prof=chosen_prof)
        ordered_slots: List[str] = []
        seen_slots: set = set()
        recs: List[str] = []
        if AIPredictor and is_ai_capability_enabled(tenant, CAP_AI_APPOINTMENT_RECS):
            try:
                recs, _ = AIPredictor().recommend(
                    tenant=tenant, professional=chosen_prof, customer_phone=phone, top_k=3,
                )
            except Exception:
                recs = []
        for t in recs:
            if t and t not in seen_slots:
                seen_slots.add(t)
                ordered_slots.append(t)
        for t in slots:
            if t and t not in seen_slots:
                seen_slots.add(t)
                ordered_slots.append(t)
        ctx.update({"mode": "select_slot", "professional": chosen_prof, "available_slots": ordered_slots})
        save_session(tenant, phone, session)
        lines = []
        if recs:
            lines.append(WMSG.MSG_RECOMMENDED_TIMES.format(times=", ".join(recs)))
        lines.append(WMSG.MSG_AVAILABLE_TIME_SLOTS.format(prof=chosen_prof))
        for i, time in enumerate(ordered_slots, start=1):
            lines.append(f"{i}) {time}")
        lines.append(WMSG.MSG_REPLY_NUMBER_CHOOSE_SLOT)
        return "\n".join(lines)

    if mode == "select_slot":
        slots = ctx.get("available_slots") or []
        parsed_time = parse_time_input(input_text)
        if parsed_time is None and AIPredictor and is_ai_enabled_in_flow(tenant):
            try:
                parsed_time = AIPredictor().parse_preferred_time(input_text)
            except Exception:
                parsed_time = None
        if parsed_time:
            hour_24, minute = parsed_time
            prof = ctx.get("professional")
            date_str = ctx.get("date")
            all_slots = await get_available_slots(tenant, prof, limit=96, date_str=date_str) if (
                    prof and date_str) else []
            nearby = slots_near_time(all_slots, hour_24, minute, window_minutes=90, max_slots=8)
            display_time = format_time_12h(hour_24, minute)
            if nearby:
                ctx["available_slots"] = nearby
                save_session(tenant, phone, session)
                lines = [WMSG.MSG_SLOTS_NEAR.format(time=display_time)]
                for i, time in enumerate(nearby, start=1):
                    lines.append(f"{i}) {time}")
                lines.append(WMSG.MSG_REPLY_NUMBER_OR_ANOTHER_TIME)
                return "\n".join(lines)
            lines = [WMSG.MSG_NO_SLOTS_NEAR_TIME.format(time=display_time)]
            for i, time in enumerate(slots, start=1):
                lines.append(f"{i}) {time}")
            return "\n".join(lines)
        idx = choice_to_index(input_text)
        if not idx or idx < 1 or idx > len(slots):
            lines = [WMSG.MSG_PLEASE_CHOOSE_OPTION_SLOT.format(max=len(slots))]
            for i, time in enumerate(slots, start=1):
                lines.append(f"{i}) {time}")
            return "\n".join(lines)
        chosen_time = slots[idx - 1]
        ctx["selected_slot"] = chosen_time
        if ctx.get("reschedule_id"):
            ctx["mode"] = "confirm_booking"
            save_session(tenant, phone, session)
            settings = get_tenant_service().get_tenant_settings(tenant) or {}
            date_fmt = ctx.get("date") or ""
            try:
                if date_fmt:
                    date_fmt = format_date_for_display(dt.date.fromisoformat(date_fmt), settings)
            except Exception:
                pass
            prof_fb = ctx.get("professional") or WMSG.MSG_YOUR_SPECIALIST_FALLBACK
            return msg_tpl.get_message(
                tenant, "reschedule_confirm_prompt",
                date=date_fmt, time=chosen_time, professional=prof_fb,
            ) or WMSG.MSG_RESCHEDULE_CONFIRM_FALLBACK.format(
                date=date_fmt, time=chosen_time, professional=prof_fb,
            )
        ctx["mode"] = "confirm_booking"
        res = get_customer_service().list_customers(tenant, search=phone)
        customers = res.get("items") or []
        if customers:
            cust = customers[0]
            ctx["customer_name"] = cust.get("name")
            ctx["customer_phone"] = cust.get("phone")
            ctx["returning"] = True
            ctx["mode"] = "returning_choice"
            save_session(tenant, phone, session)
            return WMSG.MSG_WELCOME_BACK_BOOKING.format(name=ctx["customer_name"])
        save_session(tenant, phone, session)
        return get_confirmation_msg(tenant, ctx)

    if mode == "returning_choice":
        idx = choice_to_index(input_text)
        yn = parse_yes_no(input_text)
        pick_me = idx == 1 or yn is True
        pick_other = idx == 2 or yn is False
        if pick_me:
            ctx["mode"] = "confirm_booking"
            save_session(tenant, phone, session)
            return get_confirmation_msg(tenant, ctx)
        if pick_other:
            ctx["returning"] = False
            ctx["mode"] = "ask_name"
            save_session(tenant, phone, session)
            return WMSG.MSG_GOT_IT_CUSTOMER_NAME
        return WMSG.MSG_PLEASE_CHOOSE_FOR_ME

    if mode == "confirm_booking":
        yn = parse_yes_no(input_text)
        if yn is True:
            if ctx.get("reschedule_id"):
                return await _finalize_booking(tenant, phone, session)
            if ctx.get("returning"):
                return await _finalize_booking(tenant, phone, session)
            ctx["mode"] = "ask_name"
            save_session(tenant, phone, session)
            return WMSG.MSG_PERFECT_MAY_HAVE_NAME
        if yn is False:
            if tree:
                reset_session_to_root(tenant, phone, tree)
            return WMSG.MSG_OKAY_BOOKING_CANCELLED
        if ctx.get("reschedule_id"):
            return _reprompt_reschedule_confirm(tenant, ctx)
        return get_confirmation_msg(tenant, ctx) or WMSG.MSG_PLEASE_CONFIRM_BOOKING

    if mode == "ask_name":
        name = (
            input_text
            if (input_text and input_text.lower() != WMSG.BOOKING_NAME_INPUT_SKIP)
            else WMSG.MSG_DEFAULT_CUSTOMER_NAME
        )
        ctx["customer_name"] = name
        ctx["customer_phone"] = phone
        return await _finalize_booking(tenant, phone, session)

    if mode == "wait_reminder":
        if norm_input in WMSG.FSM_WAIT_REMINDER_KEYWORDS:
            if tree:
                reset_session_to_root(tenant, phone, tree)
            return None
        settings = get_tenant_service().get_tenant_settings(tenant) or {}
        tenant_name = str(settings.get("business_name") or settings.get("tenant") or tenant)
        return msg_tpl.get_message(
            tenant, "goodbye",
            tenant_name=tenant_name,
        ) or WMSG.MSG_SEE_YOU_THEN

    return None
