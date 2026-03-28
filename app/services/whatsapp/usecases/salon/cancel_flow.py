"""
WhatsApp cancel-appointment flow: session FSM (menu / NL path) + workflow phases (pick → confirm).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.core.container import get_appointment_service, get_tenant_service
from app.helpers.phone_utils import normalize_phone
from app.models.workflow import WorkflowStep
from app.services.whatsapp.session_flow_service import get_session, save_session
from app.services.whatsapp.usecases.core.core_actions import CoreActions
from app.services.whatsapp.usecases.utils import choice_to_index, parse_yes_no
from app.services.whatsapp.wa_templates import wa
from app.services.whatsapp.helpers import constants as WMSG


def _compact_appt_line(appt: Dict[str, Any], appt_date_str: str) -> str:
    return WMSG.MSG_APPOINTMENT_COMPACT_DETAIL.format(
        prof=appt.get("professional") or "",
        time=appt.get("time") or "",
        date=appt_date_str,
    )


def _sure_cancel_prompt(appt: Dict[str, Any], appt_date_str: str) -> str:
    return WMSG.MSG_ARE_YOU_SURE_CANCEL.format(
        prof=appt.get("professional") or WMSG.LABEL_NA,
        time=appt.get("time") or WMSG.LABEL_NA,
        date=appt_date_str,
    )


async def handle_cancel_fsm(
        tenant: str,
        phone: str,
        user_input: str,
        tree: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Handle ``cancel_selection`` / ``confirm_cancel`` when present; else ``None``."""
    if not phone:
        return None
    session = get_session(tenant, phone)
    ctx = session.get("ctx", {})
    mode = str(ctx.get("mode") or "").lower()
    if mode not in ("cancel_selection", "confirm_cancel"):
        return None

    from app.services.whatsapp.session_flow_service import reset_session_to_root

    input_text = (user_input or "").strip()
    norm_input = input_text.lower()

    if mode == "cancel_selection":
        ids = ctx.get("appointments") or []
        if norm_input == WMSG.FSM_CANCEL_ALL_KEYWORD:
            results = []
            for appt_id in ids:
                try:
                    await get_appointment_service().cancel_appointment(
                        tenant, appt_id, reason="canceled", user_id=WMSG.APPOINTMENT_CANCEL_USER_ID_FSM,
                    )
                    results.append(WMSG.MSG_CANCEL_OK_EMOJI.format(id=appt_id))
                except Exception:
                    results.append(WMSG.MSG_CANCEL_FAIL_EMOJI.format(id=appt_id))
            session["ctx"] = {}
            save_session(tenant, phone, session)
            return WMSG.MSG_CANCELLATION_RESULTS_HEADER + "\n".join(results)
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
                    "mode": "confirm_cancel",
                    "appointment_id": chosen_id,
                    "appointment_date": appt.get("date"),
                    "appt_details": _compact_appt_line(appt, appt_date_str),
                    "professional": appt.get("professional"),
                    "time": appt.get("time"),
                    "customer_name": appt.get("customer_name"),
                }
            )
            save_session(tenant, phone, session)
            return _sure_cancel_prompt(appt, appt_date_str)
        if idx is not None:
            return WMSG.MSG_INVALID_SELECTION_NUMBER.format(max=len(ids))
        return WMSG.MSG_REPLY_CANCEL_LIST_OR_ALL

    if mode == "confirm_cancel":
        yn = parse_yes_no(input_text)
        appt_id = ctx.get("appointment_id")
        if yn is True:
            try:
                await get_appointment_service().cancel_appointment(
                    tenant, appt_id, reason="canceled", user_id=WMSG.APPOINTMENT_CANCEL_USER_ID_FSM,
                )
                prof = ctx.get("professional") or WMSG.LABEL_NA
                time_s = ctx.get("time") or WMSG.LABEL_NA
                cust_name = ctx.get("customer_name") or WMSG.LABEL_CUSTOMER_DEFAULT
                appt_details = ctx.get("appt_details")
                details = (
                    WMSG.MSG_APPOINTMENT_DETAIL_WITH.format(appt_details=appt_details, cust_name=cust_name)
                    if appt_details
                    else WMSG.MSG_APPOINTMENT_DETAIL_FALLBACK.format(
                        prof=prof,
                        time_s=time_s,
                        date_str=ctx.get("appointment_date") or WMSG.LABEL_NA,
                        cust_name=cust_name,
                    )
                )
                session["ctx"] = {}
                save_session(tenant, phone, session)
                return WMSG.MSG_APPOINTMENT_CANCELED.format(id=appt_id, details=details)
            except Exception as e:
                return WMSG.MSG_ERROR_CANCELING.format(id=appt_id, err=str(e))
        if yn is False:
            if tree:
                reset_session_to_root(tenant, phone, tree)
            else:
                session["ctx"] = {}
                save_session(tenant, phone, session)
            return WMSG.MSG_OKAY_NOT_CANCELED
        return WMSG.MSG_PLEASE_CONFIRM_CANCEL

    return None


async def handle_cancel_appointment_workflow(
        tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep
) -> str:
    ctx, flow = CoreActions._ctx_and_flow(session)
    pend, persist = CoreActions._workflow_pending_persist_keys(step)
    cc = get_tenant_service()._get_tenant_country_code(tenant)
    params = CoreActions.workflow_step_menu_params(step, session)
    entities = params.get("entities") or {}
    entity_appt_id = entities.get("appointment_id")
    raw = flow.get(pend)
    phase = flow.get("cancel_appointment_phase")

    async def _load_appt_for_confirm(appt_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            rows = await get_appointment_service().list_appointments(
                tenant, search_type="token", search_value=appt_id
            )
            norm_target = normalize_phone(phone, cc)
            rows = [
                a
                for a in rows
                if normalize_phone(a.get("customer_phone") or "", cc) == norm_target
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

    if phase == "confirm" and raw is not None:
        appt_id = flow.get("cancel_appointment_confirm_id")
        if not appt_id:
            flow.pop(pend, None)
            flow.pop("cancel_appointment_phase", None)
            ctx["_wa_skip_input_wait_once"] = True
            CoreActions._flow_commit_user_reply(flow, pend, persist, "")
            return WMSG.MSG_COULD_NOT_RESUME_CANCELLATION

        idx = choice_to_index(str(raw))
        if idx == 1:
            try:
                await get_appointment_service().cancel_appointment(
                    tenant, appt_id, reason="canceled", user_id=WMSG.APPOINTMENT_CANCEL_USER_ID_WORKFLOW,
                )
            except Exception as e:
                return WMSG.MSG_ERROR_CANCELING.format(id=appt_id, err=str(e))
            for k in (
                    "cancel_appointment_phase",
                    "cancel_appointment_confirm_id",
                    "cancel_appointment_candidate_ids",
            ):
                flow.pop(k, None)
            CoreActions._flow_commit_user_reply(flow, pend, persist, "yes")
            ctx["_wa_skip_input_wait_once"] = True
            return wa(tenant, "wa_salon_booking_cancelled")
        if idx == 2:
            for k in (
                    "cancel_appointment_phase",
                    "cancel_appointment_confirm_id",
                    "cancel_appointment_candidate_ids",
            ):
                flow.pop(k, None)
            CoreActions._flow_commit_user_reply(flow, pend, persist, "no")
            ctx["_wa_skip_input_wait_once"] = True
            return WMSG.MSG_OKAY_NOT_CANCELED
        return wa(tenant, "wa_salon_confirm_yes_no")

    if phase == "pick" and raw is not None:
        ids = flow.get("cancel_appointment_candidate_ids") or []
        text = str(raw).strip()
        if text.lower() == WMSG.FSM_CANCEL_ALL_KEYWORD:
            lines_out: List[str] = []
            for oid in ids:
                try:
                    await get_appointment_service().cancel_appointment(
                        tenant, oid, reason="canceled", user_id=WMSG.APPOINTMENT_CANCEL_USER_ID_WORKFLOW,
                    )
                    lines_out.append(WMSG.MSG_CANCEL_OK_PLAIN.format(id=oid))
                except Exception:
                    lines_out.append(WMSG.MSG_CANCEL_FAIL_PLAIN.format(id=oid))
            flow.pop("cancel_appointment_phase", None)
            flow.pop("cancel_appointment_candidate_ids", None)
            CoreActions._flow_commit_user_reply(flow, pend, persist, "all")
            ctx["_wa_skip_input_wait_once"] = True
            return WMSG.MSG_CANCELLATION_RESULTS_HEADER + "\n".join(lines_out)
        idx = choice_to_index(text)
        if idx and 1 <= idx <= len(ids):
            chosen_id = ids[idx - 1]
            appt, err = await _load_appt_for_confirm(chosen_id)
            if err or not appt:
                return err or WMSG.MSG_APPOINTMENT_NOT_FOUND_SHORT
            appt_date_str = appt.get("date") or WMSG.LABEL_NA
            flow["cancel_appointment_phase"] = "confirm"
            flow["cancel_appointment_confirm_id"] = chosen_id
            flow.pop("cancel_appointment_candidate_ids", None)
            flow.pop(pend, None)
            return _sure_cancel_prompt(appt, appt_date_str)
        flow.pop(pend, None)
        return WMSG.MSG_INVALID_SELECTION_STAR_ALL_RANGE.format(max=len(ids))

    if not phone:
        ctx["_wa_skip_input_wait_once"] = True
        return WMSG.MSG_PHONE_NUMBER_REQUIRED

    appt_id = entity_appt_id
    if appt_id:
        appt, err = await _load_appt_for_confirm(str(appt_id))
        if err or not appt:
            ctx["_wa_skip_input_wait_once"] = True
            return err or WMSG.MSG_APPOINTMENT_NOT_FOUND_SHORT
        appt_date_str = appt.get("date") or WMSG.LABEL_NA
        flow["cancel_appointment_phase"] = "confirm"
        flow["cancel_appointment_confirm_id"] = appt["id"]
        return _sure_cancel_prompt(appt, appt_date_str)

    appts = await get_appointment_service().list_appointments(
        tenant, search_type="phone", search_value=phone, status="booked"
    )
    if not appts:
        ctx["_wa_skip_input_wait_once"] = True
        return WMSG.MSG_NO_ACTIVE_BOOKINGS_CANCEL
    if len(appts) > 1:
        flow["cancel_appointment_phase"] = "pick"
        flow["cancel_appointment_candidate_ids"] = [a["id"] for a in appts]
        lines = [WMSG.MSG_MULTIPLE_APPOINTMENTS_CANCEL]
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
        lines.append(WMSG.MSG_SUFFIX_REPLY_NUMBER_OR_ALL)
        return "\n".join(lines)

    appt = appts[0]
    appt_id = appt["id"]
    if appt.get("status") != "booked":
        ctx["_wa_skip_input_wait_once"] = True
        return WMSG.MSG_APPOINTMENT_ALREADY_STATUS.format(id=appt_id, status=appt.get("status"))
    appt_date_str = appt.get("date") or WMSG.LABEL_NA
    flow["cancel_appointment_phase"] = "confirm"
    flow["cancel_appointment_confirm_id"] = appt_id
    return _sure_cancel_prompt(appt, appt_date_str)


async def handle_cancel_appointment_legacy_fsm(
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
            return WMSG.MSG_NO_ACTIVE_BOOKINGS_CANCEL
        if len(appts) > 1:
            session = get_session(tenant, phone)
            session["ctx"] = {"mode": "cancel_selection", "appointments": [a["id"] for a in appts]}
            save_session(tenant, phone, session)
            lines = [WMSG.MSG_MULTIPLE_APPOINTMENTS_CANCEL]
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
            lines.append(WMSG.MSG_SUFFIX_REPLY_NUMBER_OR_ALL_QUOTE)
            return "\n".join(lines)
        appt = appts[0]
        appt_id = appt["id"]
    else:
        try:
            appts = await get_appointment_service().list_appointments(
                tenant, search_type="token", search_value=appt_id
            )
            norm_target = normalize_phone(phone, cc)
            appts = [
                a
                for a in appts
                if normalize_phone(a.get("customer_phone") or "", cc) == norm_target
                   or a.get("customer_phone") in (phone, raw_phone)
            ]
            if not appts:
                return WMSG.MSG_APPOINTMENT_NOT_FOUND.format(id=appt_id)
            appt = appts[0]
            appt_id = appt["id"]
        except Exception:
            return WMSG.MSG_ERROR_FINDING_APPOINTMENT.format(id=appt_id)
    if appt.get("status") != "booked":
        return WMSG.MSG_APPOINTMENT_ALREADY_STATUS.format(id=appt_id, status=appt.get("status"))
    session = get_session(tenant, phone)
    appt_date_str = appt.get("date") or WMSG.LABEL_NA
    session["ctx"] = {
        "mode": "confirm_cancel",
        "appointment_id": appt_id,
        "appointment_date": appt.get("date"),
        "appt_details": _compact_appt_line(appt, appt_date_str),
        "professional": appt.get("professional"),
        "time": appt.get("time"),
        "customer_name": appt.get("customer_name"),
    }
    save_session(tenant, phone, session)
    return _sure_cancel_prompt(appt, appt_date_str)
