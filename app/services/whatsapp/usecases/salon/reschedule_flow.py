"""
WhatsApp reschedule flow: session FSM + workflow phases, then handoff to booking FSM (``start_timeslot_flow``).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.core.container import get_appointment_service, get_tenant_service
from app.helpers.phone_util import PhoneUtil
from app.models.workflow import WorkflowStep
from app.services.whatsapp.session_flow_service import get_session, save_session
from app.services.whatsapp.usecases.core.core_actions import CoreActions
from app.services.whatsapp.usecases.salon.booking_ctx_utils import (
    clear_stale_booking_calendar_keys,
    exit_workflow_for_fsm_handoff,
)
from app.services.whatsapp.usecases.utils import choice_to_index, parse_yes_no
from app.services.whatsapp.wa_templates import wa
from app.services.whatsapp.helpers import constants as WMSG


def _compact_appt_line(appt: Dict[str, Any], appt_date_str: str) -> str:
    return WMSG.MSG_APPOINTMENT_COMPACT_DETAIL.format(
        prof=appt.get("professional") or "",
        time=appt.get("time") or "",
        date=appt_date_str,
    )


def _sure_reschedule_prompt(appt: Dict[str, Any], appt_date_str: str) -> str:
    return WMSG.MSG_ARE_YOU_SURE_RESCHEDULE.format(
        prof=appt.get("professional") or WMSG.LABEL_NA,
        time=appt.get("time") or WMSG.LABEL_NA,
        date=appt_date_str,
    )


async def handle_reschedule_fsm(
        tenant: str,
        phone: str,
        user_input: str,
        tree: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Handle ``reschedule_selection`` / ``confirm_reschedule``; else ``None``."""
    if not phone:
        return None
    session = get_session(tenant, phone)
    ctx = session.get("ctx", {})
    mode = str(ctx.get("mode") or "").lower()
    if mode not in ("reschedule_selection", "confirm_reschedule"):
        return None

    from app.services.whatsapp.session_flow_service import reset_session_to_root
    from app.services.whatsapp.usecases.salon.booking_flow import start_timeslot_flow

    input_text = (user_input or "").strip()

    if mode == "reschedule_selection":
        ids = ctx.get("appointments") or []
        idx = choice_to_index(input_text)
        if idx is not None and 1 <= idx <= len(ids):
            chosen_id = ids[idx - 1]
            appts = await get_appointment_service().list_appointments(
                tenant, search_type="token", search_value=chosen_id
            )
            if not appts:
                return WMSG.MSG_APPOINTMENT_NOT_FOUND.format(id=chosen_id)
            appt = appts[0]
            appt_date_str = appt.get("date") or WMSG.LABEL_NA
            ctx.update(
                {
                    "mode": "confirm_reschedule",
                    "appointment_id": chosen_id,
                    "appointment_date": appt.get("date"),
                    "appt_details": _compact_appt_line(appt, appt_date_str),
                    "professional": appt.get("professional"),
                    "service": appt.get("service"),
                    "customer_name": appt.get("customer_name"),
                    "customer_phone": appt.get("customer_phone") or phone,
                }
            )
            save_session(tenant, phone, session)
            return _sure_reschedule_prompt(appt, appt_date_str)
        if idx is not None:
            return WMSG.MSG_INVALID_SELECTION_RESCHEDULE.format(max=len(ids))
        return WMSG.MSG_REPLY_RESCHEDULE_LIST

    if mode == "confirm_reschedule":
        yn = parse_yes_no(input_text)
        if yn is True:
            appt_id = ctx.get("appointment_id")
            clear_stale_booking_calendar_keys(ctx)
            ctx.update(
                {
                    "mode": "select_date",
                    "reschedule_id": appt_id,
                    "reschedule_old_date": ctx.get("appointment_date"),
                    "service": ctx.get("service"),
                    "professional": ctx.get("professional"),
                    "customer_name": ctx.get("customer_name"),
                    "customer_phone": ctx.get("customer_phone") or phone,
                }
            )
            CoreActions._set_ctx(
                session,
                professional=ctx.get("professional"),
                service=ctx.get("service"),
                customer_name=ctx.get("customer_name"),
                customer_phone=ctx.get("customer_phone") or phone,
            )
            exit_workflow_for_fsm_handoff(session)
            save_session(tenant, phone, session)
            return await start_timeslot_flow(tenant, phone)
        if yn is False:
            if tree:
                reset_session_to_root(tenant, phone, tree)
            else:
                session["ctx"] = {}
                save_session(tenant, phone, session)
            return WMSG.MSG_OKAY_NOT_RESCHEDULED
        return WMSG.MSG_PLEASE_CONFIRM_RESCHEDULE

    return None


async def handle_reschedule_appointment_workflow(
        tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep
) -> str:
    from app.services.whatsapp.usecases.salon.booking_flow import start_timeslot_flow

    ctx, flow = CoreActions._ctx_and_flow(session)
    pend, persist = CoreActions._workflow_pending_persist_keys(step)
    cc = get_tenant_service()._get_tenant_country_code(tenant)
    params = CoreActions.workflow_step_menu_params(step, session)
    entities = params.get("entities") or {}
    entity_appt_id = entities.get("appointment_id")
    raw = flow.get(pend)
    phase = flow.get("reschedule_appointment_phase")

    def _clear_reschedule_flow_keys() -> None:
        for k in (
                "reschedule_appointment_phase",
                "reschedule_appointment_confirm_id",
                "reschedule_appointment_candidate_ids",
                "reschedule_appointment_professional",
                "reschedule_appointment_service",
                "reschedule_appointment_old_date",
                "reschedule_appointment_customer_name",
                "reschedule_appointment_customer_phone",
        ):
            flow.pop(k, None)

    async def _load_appt_for_reschedule(appt_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            rows = await get_appointment_service().list_appointments(
                tenant, search_type="token", search_value=appt_id
            )
            norm_target = PhoneUtil.normalize_e164_input(phone, cc or PhoneUtil.DEFAULT_DIAL_DIGITS)
            rows = [
                a
                for a in rows
                if PhoneUtil.normalize_e164_input(
                    PhoneUtil.appointment_customer_e164(a, cc or PhoneUtil.DEFAULT_DIAL_DIGITS),
                    cc or PhoneUtil.DEFAULT_DIAL_DIGITS,
                )
                == norm_target
                   or a.get("customer_phone") == phone
            ]
            if not rows:
                return None, WMSG.MSG_APPOINTMENT_NOT_FOUND.format(id=appt_id)
            a = rows[0]
            if a.get("status") != "booked":
                return None, WMSG.MSG_APPOINTMENT_ALREADY_STATUS.format(
                    id=appt_id, status=a.get("status"),
                )
            return a, None
        except Exception:
            return None, WMSG.MSG_ERROR_FINDING_APPOINTMENT.format(id=appt_id)

    def _set_confirm_from_appt(appt: Dict[str, Any]) -> str:
        appt_date_str = appt.get("date") or WMSG.LABEL_NA
        flow["reschedule_appointment_phase"] = "confirm"
        flow["reschedule_appointment_confirm_id"] = appt["id"]
        flow["reschedule_appointment_professional"] = appt.get("professional")
        flow["reschedule_appointment_service"] = appt.get("service")
        flow["reschedule_appointment_old_date"] = appt.get("date")
        flow["reschedule_appointment_customer_name"] = appt.get("customer_name")
        flow["reschedule_appointment_customer_phone"] = appt.get("customer_phone")
        return _sure_reschedule_prompt(appt, appt_date_str)

    if phase == "confirm" and raw is not None:
        appt_id = flow.get("reschedule_appointment_confirm_id")
        if not appt_id:
            flow.pop(pend, None)
            _clear_reschedule_flow_keys()
            ctx["_wa_skip_input_wait_once"] = True
            CoreActions._flow_commit_user_reply(flow, pend, persist, "")
            return WMSG.MSG_COULD_NOT_RESUME_RESCHEDULING

        idx = choice_to_index(str(raw))
        if idx == 1:
            prof = flow.get("reschedule_appointment_professional")
            service = flow.get("reschedule_appointment_service")
            old_date = flow.get("reschedule_appointment_old_date")
            cust_name = flow.get("reschedule_appointment_customer_name")
            cust_phone = flow.get("reschedule_appointment_customer_phone")
            _clear_reschedule_flow_keys()
            CoreActions._flow_commit_user_reply(flow, pend, persist, "yes")
            clear_stale_booking_calendar_keys(ctx)
            ctx["mode"] = "select_date"
            ctx["reschedule_id"] = appt_id
            ctx["reschedule_old_date"] = old_date
            CoreActions._set_ctx(
                session,
                professional=prof,
                service=service,
                customer_name=cust_name,
                customer_phone=cust_phone,
            )
            exit_workflow_for_fsm_handoff(session)
            ctx["_wa_skip_input_wait_once"] = True
            save_session(tenant, phone, session)
            return await start_timeslot_flow(tenant, phone)
        if idx == 2:
            _clear_reschedule_flow_keys()
            CoreActions._flow_commit_user_reply(flow, pend, persist, "no")
            ctx["_wa_skip_input_wait_once"] = True
            return WMSG.MSG_OKAY_NOT_RESCHEDULED
        return wa(tenant, "wa_salon_confirm_yes_no")

    if phase == "pick" and raw is not None:
        ids = flow.get("reschedule_appointment_candidate_ids") or []
        idx = choice_to_index(str(raw).strip())
        if idx and 1 <= idx <= len(ids):
            chosen_id = ids[idx - 1]
            appt, err = await _load_appt_for_reschedule(chosen_id)
            if err or not appt:
                return err or WMSG.MSG_APPOINTMENT_NOT_FOUND_SHORT
            flow.pop("reschedule_appointment_candidate_ids", None)
            flow.pop(pend, None)
            return _set_confirm_from_appt(appt)
        flow.pop(pend, None)
        return WMSG.MSG_INVALID_SELECTION_RESCHEDULE.format(max=len(ids))

    if not phone:
        ctx["_wa_skip_input_wait_once"] = True
        return WMSG.MSG_PHONE_NUMBER_REQUIRED

    appt_id = entity_appt_id
    if appt_id:
        appt, err = await _load_appt_for_reschedule(str(appt_id))
        if err or not appt:
            ctx["_wa_skip_input_wait_once"] = True
            return err or WMSG.MSG_APPOINTMENT_NOT_FOUND_SHORT
        return _set_confirm_from_appt(appt)

    appts = await get_appointment_service().list_appointments(
        tenant, search_type="phone", search_value=phone, status="booked"
    )
    if not appts:
        ctx["_wa_skip_input_wait_once"] = True
        return WMSG.MSG_NO_ACTIVE_BOOKINGS_RESCHEDULE
    if len(appts) > 1:
        flow["reschedule_appointment_phase"] = "pick"
        flow["reschedule_appointment_candidate_ids"] = [a["id"] for a in appts]
        lines = [WMSG.MSG_MULTIPLE_APPOINTMENTS_RESCHEDULE]
        for i, a in enumerate(appts, start=1):
            f_date = a.get("date") or WMSG.LABEL_NA
            lines.append(
                WMSG.MSG_APPOINTMENT_LIST_LINE.format(
                    i=i,
                    appt_id=a["id"],
                    prof=a.get("professional"),
                    time=a.get("time"),
                    date=f_date,
                )
            )
        lines.append(WMSG.MSG_SUFFIX_REPLY_NUMBER)
        return "\n".join(lines)

    appt = appts[0]
    aid = appt["id"]
    if appt.get("status") != "booked":
        ctx["_wa_skip_input_wait_once"] = True
        return WMSG.MSG_APPOINTMENT_ALREADY_STATUS.format(id=aid, status=appt.get("status"))
    return _set_confirm_from_appt(appt)


async def handle_reschedule_appointment_legacy_fsm(
        tenant: str, params: Dict[str, Any], phone: str, raw_phone: str, cc: str
) -> str:
    entities = params.get("entities") or {}
    appt_id = entities.get("appointment_id")
    if not phone:
        return WMSG.MSG_PHONE_NUMBER_REQUIRED
    if not appt_id:
        appts = await get_appointment_service().list_appointments(
            tenant, search_type="phone", search_value=phone, status="booked"
        )
        if not appts and raw_phone:
            appts = await get_appointment_service().list_appointments(
                tenant, search_type="phone", search_value=raw_phone, status="booked"
            )
        if not appts:
            return WMSG.MSG_NO_ACTIVE_BOOKINGS_RESCHEDULE
        if len(appts) > 1:
            session = get_session(tenant, phone)
            session["ctx"] = {"mode": "reschedule_selection", "appointments": [a["id"] for a in appts]}
            save_session(tenant, phone, session)
            lines = [WMSG.MSG_MULTIPLE_APPOINTMENTS_RESCHEDULE]
            for i, a in enumerate(appts, start=1):
                f_date = a.get("date") or WMSG.LABEL_NA
                lines.append(
                    WMSG.MSG_APPOINTMENT_LIST_LINE.format(
                        i=i,
                        appt_id=a["id"],
                        prof=a.get("professional"),
                        time=a.get("time"),
                        date=f_date,
                    )
                )
            lines.append(WMSG.MSG_SUFFIX_REPLY_NUMBER)
            return "\n".join(lines)
        appt = appts[0]
        appt_id = appt["id"]
    else:
        try:
            appts = await get_appointment_service().list_appointments(
                tenant, search_type="token", search_value=appt_id
            )
            norm_target = PhoneUtil.normalize_e164_input(phone, cc or PhoneUtil.DEFAULT_DIAL_DIGITS)
            appts = [
                a
                for a in appts
                if PhoneUtil.normalize_e164_input(
                    PhoneUtil.appointment_customer_e164(a, cc or PhoneUtil.DEFAULT_DIAL_DIGITS),
                    cc or PhoneUtil.DEFAULT_DIAL_DIGITS,
                )
                == norm_target
                   or a.get("customer_phone") in (phone, raw_phone)
            ]
            if not appts:
                return WMSG.MSG_APPOINTMENT_NOT_FOUND.format(id=appt_id)
            appt = appts[0]
        except Exception:
            return WMSG.MSG_ERROR_FINDING_APPOINTMENT.format(id=appt_id)
    session = get_session(tenant, phone)
    appt_date_str = appt.get("date") or WMSG.LABEL_NA
    session["ctx"] = {
        "mode": "confirm_reschedule",
        "appointment_id": appt_id,
        "appointment_date": appt.get("date") or appt_date_str,
        "appt_details": _compact_appt_line(appt, appt_date_str),
        "professional": appt.get("professional"),
        "service": appt.get("service"),
        "customer_name": appt.get("customer_name"),
        "customer_phone": appt.get("customer_phone") or phone,
    }
    save_session(tenant, phone, session)
    return _sure_reschedule_prompt(appt, appt_date_str)
