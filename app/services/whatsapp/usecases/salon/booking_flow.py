"""
WhatsApp appointment booking FSM (salon/clinic): service/date/professional/slot/confirm.

- :func:`start_timeslot_flow` lives in :mod:`booking_timeslot_start` (re-exported here for stable imports).
- Per-message mode logic lives in :mod:`booking_fsm_handlers` (:func:`dispatch_booking_fsm_mode`).
- Cancel / reschedule session modes: :mod:`cancel_flow`, :mod:`reschedule_flow` (invoked from :func:`handle_timeslot_fsm`).

Used by :mod:`inbound_pipeline` and :class:`SalonActions` workflow handoffs.
"""
from __future__ import annotations
import datetime as dt
from typing import Any, Dict, List, Optional

from app.core.container import (
    get_tenant_service,
    get_professional_service,
    get_appointment_service,
    get_customer_service,
    get_slot_service,
)
from app.helpers.constants import SLOT_STATUS_AVAILABLE
from app.services.whatsapp.session_flow_service import get_session, save_session, reset_session_to_root
from app.services.core import message_templates as msg_tpl
from app.helpers.date_utils import (
    format_date_for_display,
    get_tenant_timezone_zoneinfo,
)

from app.services.whatsapp.action_support import get_action_logger
from app.services.whatsapp.usecases.salon.booking_ctx_utils import sync_booking_ctx_from_flow_data
from app.services.whatsapp.usecases.salon.booking_fsm_handlers import (
    dispatch_booking_fsm_mode,
    handle_fsm_back,
)
from app.services.whatsapp.usecases.salon.booking_timeslot_start import start_timeslot_flow
from app.services.whatsapp.helpers import constants as WMSG

logger = get_action_logger("usecases.salon.booking_flow")

def _reprompt_reschedule_confirm(tenant: str, ctx: Dict[str, Any]) -> str:
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    date_fmt = ctx.get("date") or ""
    try:
        if date_fmt:
            date_fmt = format_date_for_display(dt.date.fromisoformat(date_fmt), settings)
    except Exception:
        pass
    chosen_time = ctx.get("selected_slot") or ""
    prof_fb = ctx.get("professional") or WMSG.MSG_YOUR_SPECIALIST_FALLBACK
    return msg_tpl.get_message(
        tenant,
        "reschedule_confirm_prompt",
        date=date_fmt or "",
        time=chosen_time,
        professional=prof_fb,
    ) or WMSG.MSG_RESCHEDULE_CONFIRM_FALLBACK.format(
        date=date_fmt or "", time=chosen_time, professional=prof_fb,
    )


async def get_available_slots(
        tenant: str,
        professional_name: Optional[str] = None,
        limit: int = 6,
        date_str: Optional[str] = None,
) -> List[str]:
    """Fetch available slots for one or all professionals."""
    if date_str:
        try:
            if not professional_name:
                return []
            slots_data = await get_slot_service().get_availability(
                tenant=tenant,
                professional=professional_name,
                from_date=date_str,
                to_date=date_str,
                channel="whatsapp",
            )
            times: List[str] = []
            for item in slots_data:
                bookable = getattr(item, "bookable", item.get("bookable") if isinstance(item, dict) else False)
                if not bookable:
                    continue
                start = getattr(item, "start", item.get("start") if isinstance(item, dict) else None)
                try:
                    t = dt.datetime.fromisoformat(str(start)).strftime("%H:%M") if start else ""
                    if t:
                        times.append(t)
                except Exception:
                    continue
            return times[:limit]
        except Exception as e:
            logger.error("Error fetching date-specific slots: %s", e)
            return []
    try:
        professionals = get_professional_service().get_professionals(tenant)
    except Exception:
        professionals = []
    slots: List[str] = []
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    tz = get_tenant_timezone_zoneinfo(settings)
    today_str = dt.datetime.now(tz).date().isoformat()
    for pro in professionals:
        name = getattr(pro, "name", pro.get("name") if isinstance(pro, dict) else None)
        if professional_name and str(name) != professional_name:
            continue
        overrides = getattr(pro, "date_overrides", {}) or {}
        day_overrides = overrides.get(today_str) or []
        blocked_times = {s["time"] for s in day_overrides if isinstance(s, dict) and s.get("status") == "blocked"}
        pro_slots = getattr(pro, "slots", pro.get("slots") if isinstance(pro, dict) else []) or []
        for slot in pro_slots:
            status = getattr(slot, "status", slot.get("status") if isinstance(slot, dict) else "available")
            time = getattr(slot, "time", slot.get("time") if isinstance(slot, dict) else "")
            if str(status).lower() == SLOT_STATUS_AVAILABLE and time and time not in blocked_times:
                slots.append(str(time))
            if len(slots) >= limit:
                break
        if slots and not professional_name:
            break
    return slots


def list_professionals(
        tenant: str,
        date_str: Optional[str] = None,
        service: Optional[str] = None,
) -> List[str]:
    """List unique professional names, optionally filtered by date and service."""
    try:
        pros = get_professional_service().get_professionals(tenant)
    except Exception:
        pros = []
    names: List[str] = []
    for pro in pros:
        name = getattr(pro, "name", pro.get("name") if isinstance(pro, dict) else None)
        if not name:
            continue
        if service:
            pro_services = getattr(pro, "services", []) or []
            normalized = [str(s).lower() for s in pro_services]
            if str(service).lower() not in normalized:
                continue
        if date_str:
            try:
                day = dt.date.fromisoformat(date_str)
                crit = getattr(pro, "availability_criteria", "daily") or "daily"
                days_cfg = getattr(pro, "available_days", []) or []
                is_avail = True
                if crit == "weekly" and days_cfg and day.weekday() not in days_cfg:
                    is_avail = False
                elif crit == "monthly" and days_cfg and day.day not in days_cfg:
                    is_avail = False
                if not is_avail:
                    continue
            except Exception:
                pass
        if str(name) not in names:
            names.append(str(name))
    return names


async def _finalize_booking(tenant: str, phone: str, session: Dict[str, Any]) -> Optional[str]:
    """Create or reschedule appointment and return confirmation message."""
    ctx = session.get("ctx", {}) or {}
    flow = ctx.get("flow_data")
    if not isinstance(flow, dict):
        flow = {}
    merged = {**ctx, **flow}
    slot = merged.get("selected_slot")
    prof = merged.get("professional")
    name = str(merged.get("customer_name") or "").strip()
    cust_phone = merged.get("customer_phone", phone)
    service = merged.get("service")
    final_prof = prof if prof and prof != WMSG.LABEL_AUTO_ASSIGNED else ""
    if not slot:
        return WMSG.MSG_SESSION_ERROR
    try:
        res_id = merged.get("reschedule_id")
        if res_id and not name:
            try:
                rows = await get_appointment_service().list_appointments(
                    tenant, search_type="token", search_value=str(res_id)
                )
                if rows:
                    name = str(rows[0].get("customer_name") or "").strip()
            except Exception:
                pass
        if not name:
            name = WMSG.MSG_DEFAULT_CUSTOMER_NAME
        if res_id:
            appt = await get_appointment_service().reschedule_appointment(
                tenant=tenant,
                appointment_id=str(res_id),
                new_time=slot,
                new_date=merged.get("date"),
                user_id=WMSG.BOOKING_API_USER_ID,
                new_professional=final_prof or None,
            )
        else:
            payload = {
                "customer_name": name,
                "customer_phone": cust_phone,
                "professional": final_prof,
                "service": service,
                "time": slot,
                "date": merged.get("date"),
            }
            appt = await get_appointment_service().create_appointment(
                tenant=tenant,
                payload=payload,
                user_id=WMSG.BOOKING_API_USER_ID,
            )
        get_customer_service().ensure_customer_if_absent(tenant, name, cust_phone)
        settings = get_tenant_service().get_tenant_settings(tenant) or {}
        date_val = merged.get("date")
        date_info = ""
        if date_val:
            try:
                date_info = format_date_for_display(dt.date.fromisoformat(date_val), settings)
            except Exception:
                date_info = date_val
        loc = str(settings.get("address") or WMSG.MSG_BUSINESS_ADDRESS_FALLBACK)
        specialist_line = WMSG.MSG_SPECIALIST_LINE.format(prof=final_prof) if final_prof else ""
        ctx.pop("reschedule_id", None)
        ctx.pop("reschedule_old_date", None)
        ctx["mode"] = "wait_reminder"
        save_session(tenant, phone, session)
        tenant_name = str(settings.get("business_name") or settings.get("tenant") or tenant)
        msg = msg_tpl.get_message(
            tenant, "booking_confirmation",
            customer_name=name, date=date_info, time=slot, location=loc,
            specialist_line=specialist_line, tenant_name=tenant_name,
        )
        spec_line = WMSG.MSG_SPECIALIST_LINE.format(prof=final_prof) if final_prof else ""
        return msg or WMSG.MSG_BOOKING_CONFIRM_FALLBACK.format(
            customer_name=name,
            date=date_info,
            time=slot,
            location=loc,
            specialist_line=spec_line,
        )
    except ValueError as e:
        ctx["mode"] = "select_date"
        save_session(tenant, phone, session)
        err_msg = str(e)
        if WMSG.MSG_BOOKING_ERR_BLOCKED_SUBSTR in err_msg or WMSG.MSG_BOOKING_ERR_NO_SHOW_SUBSTR in err_msg:
            return WMSG.MSG_BOOKING_BLOCKED_NO_SHOWS
        return WMSG.MSG_BOOKING_FAILED_TRY_DATE.format(err_msg=err_msg)
    return None


async def handle_timeslot_fsm(
        tenant: str,
        phone: str,
        user_input: str,
        tree: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Handle one user message for the booking FSM (by ctx.mode). Returns text reply or None if not in FSM."""
    if not phone:
        return None
    session = get_session(tenant, phone)
    _top = session.get("ctx")
    if isinstance(_top, dict):
        sync_booking_ctx_from_flow_data(_top)
    ctx = session.get("ctx", {})
    mode = str(ctx.get("mode") or "").lower()
    logger.info("handle_timeslot_fsm phone=%s mode=%s input=%s", phone, mode, user_input)

    input_text = (user_input or "").strip()
    norm_input = input_text.lower()

    from app.services.whatsapp.usecases.salon.cancel_flow import handle_cancel_fsm
    from app.services.whatsapp.usecases.salon.reschedule_flow import handle_reschedule_fsm

    _cancel_out = await handle_cancel_fsm(tenant, phone, user_input, tree)
    if _cancel_out is not None:
        return _cancel_out
    _reschedule_out = await handle_reschedule_fsm(tenant, phone, user_input, tree)
    if _reschedule_out is not None:
        return _reschedule_out

    if norm_input in WMSG.FSM_EXIT_KEYWORDS:
        if tree:
            reset_session_to_root(tenant, phone, tree)
        else:
            session["ctx"] = {}
            save_session(tenant, phone, session)
        return None

    if norm_input == WMSG.FSM_BACK_KEYWORD:
        back_reply = await handle_fsm_back(tenant, phone, session, ctx, mode, tree)
        if back_reply is not None:
            return back_reply

    return await dispatch_booking_fsm_mode(
        tenant, phone, session, ctx, mode, input_text, norm_input, tree,
    )
