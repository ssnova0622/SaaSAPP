from __future__ import annotations

import datetime as dt
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.container import get_professional_service, get_tenant_service
from app.helpers.constants_action import (
    AUTO_ASSIGN_TIME,
    CANCEL_APPOINTMENT,
    CONFIRM_BOOKING,
    CONFIRM_PROMPT,
    FINALIZE_BOOKING,
    PROFESSIONAL_DETAILS,
    RESCHEDULE_APPOINTMENT,
    SELECT_DATE,
    SELECT_TIME,
    SHOW_PROFESSIONALS,
    SHOW_SERVICES,
    SUGGEST_PROFESSIONAL,
)
from app.helpers.date_utils import (
    format_date_for_display,
    get_display_date_format,
    get_tenant_timezone_zoneinfo,
    parse_user_date_input,
)
from app.models.workflow import WorkflowStep
from app.services.storage_mongo import Storage
from app.services.whatsapp.action_support import get_action_logger, run_handler_and_await
from app.services.whatsapp.usecases.core.core_actions import CoreActions
from app.services.whatsapp.usecases.utils import choice_to_index
from app.services.whatsapp.wa_templates import wa
from app.services.whatsapp.helpers import constants as WMSG

logger = get_action_logger("usecases.salon")

try:
    from app.services.ai import AIPredictor  # type: ignore
except Exception:
    AIPredictor = None  # type: ignore


class SalonActions(CoreActions):
    """
    Salon/clinic booking workflow: services, staff, date/time slots, confirmation, finalize.

    Reuses :class:`CoreActions` for ``flow_data``, pending user replies, and shared validators.
    """

    @staticmethod
    async def get_available_slots(
            tenant: str,
            professional_name: Optional[str] = None,
            limit: int = 6,
            date_str: Optional[str] = None,
    ) -> List[str]:
        from app.services.whatsapp.usecases.salon.booking_flow import get_available_slots as _booking_slots

        return await _booking_slots(tenant, professional_name, limit, date_str)

    @staticmethod
    async def _auto_assign_first_slot(tenant: str, service: Optional[str], date: str) -> Tuple[
        Optional[str], Optional[str]]:
        from app.services.whatsapp.usecases.salon.booking_flow import list_professionals

        for p in list_professionals(tenant, date_str=date, service=service):
            slots = await SalonActions.get_available_slots(tenant, professional_name=p, date_str=date)
            if slots:
                return p, slots[0]
        return None, None

    @staticmethod
    def _professional_menu_choice(tenant: str, raw: str, pros: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """Return (professional_or_auto, None) on success, (None, error_message) on invalid input."""
        idx = choice_to_index(str(raw))
        if idx and 1 <= idx <= len(pros):
            return pros[idx - 1], None
        if idx == len(pros) + 1:
            return "Auto-assigned", None
        if not pros:
            return None, wa(tenant, "wa_salon_no_staff_options")
        return None, wa(tenant, "wa_salon_pick_staff_range", max_n=len(pros) + 1)

    @staticmethod
    def _ai_professional_matches(tenant: str, query: str) -> List[Any]:
        if not (AIPredictor and CoreActions._is_ai_enabled(tenant)):
            return []
        try:
            return AIPredictor().search_professionals(tenant, query)
        except Exception:
            return []

    @staticmethod
    def _workflow_step_menu_params(step: WorkflowStep, session: Dict[str, Any]) -> Dict[str, Any]:
        return CoreActions.workflow_step_menu_params(step, session)

    @staticmethod
    def _workflow_text_input(step: WorkflowStep, session: Dict[str, Any]) -> str:
        """Free-text hint for AI-style salon steps: step param, then common flow_data keys."""
        p = step.params or {}
        raw = (p.get("input") or p.get("query") or "").strip()
        if raw:
            return str(raw)
        flow = (session.get("ctx") or {}).get("flow_data")
        if not isinstance(flow, dict):
            return ""
        for k in (
                "input",
                "query",
                "user_input",
                "ai_free_text_user_input",
        ):
            v = flow.get(k)
            if v is not None and str(v).strip():
                return str(v).strip()
        return ""

    @staticmethod
    async def _run_show_services(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> Optional[str]:
        _, flow = CoreActions._ctx_and_flow(session)
        view = CoreActions._session_booking_view(session)
        pend, persist = CoreActions._workflow_pending_persist_keys(step)
        raw = flow.get(pend)
        if raw is not None:
            services = view.get("available_services") or []
            picked = CoreActions._pick_from_list(str(raw), services)
            if picked:
                CoreActions._set_flow_fields(session, service=picked, service_name=picked, service_id=picked)
                CoreActions._flow_commit_user_reply(flow, pend, persist, str(picked))
                return None
            if not services:
                return wa(tenant, "wa_salon_no_services")
            return wa(tenant, "wa_salon_pick_service_number", max_n=len(services))
        db_services = Storage.list_services(tenant)
        services = [s["name"] for s in db_services if s.get("active", True)]
        if not services:
            return None
        lines = [step.label or wa(tenant, "wa_salon_pick_service")]
        for i, s in enumerate(services, start=1):
            lines.append(f"{i}) {s}")
        flow["available_services"] = services
        return "\n".join(lines)

    @staticmethod
    async def run_show_professionals(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> Optional[
        str]:
        from app.services.salon.professional_service import ProfessionalService

        _, flow = CoreActions._ctx_and_flow(session)
        view = CoreActions._session_booking_view(session)
        pend, persist = CoreActions._workflow_pending_persist_keys(step)
        raw = flow.get(pend)
        if raw is not None:
            pros = view.get("professionals") or []
            prof, err = SalonActions._professional_menu_choice(tenant, str(raw), pros)
            if err:
                return err
            CoreActions._set_flow_fields(session, professional=prof)
            CoreActions._flow_commit_user_reply(flow, pend, persist, str(prof))
            return None
        service, date = view.get("service"), view.get("date")
        pros = ProfessionalService.filter_professionals(tenant, date_str=date, service=service)
        if not pros:
            return wa(tenant, "wa_salon_no_staff", service=service or WMSG.MSG_REQUESTED_SERVICE_FALLBACK)
        lines = [step.label or wa(tenant, "wa_salon_pick_staff")]
        for i, name in enumerate(pros, start=1):
            lines.append(f"{i}) {name}")
        lines.append(f"{len(pros) + 1}) {wa(tenant, 'wa_salon_auto_assign_option')}")
        flow["professionals"] = pros
        return "\n".join(lines)

    @staticmethod
    async def _run_select_date(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> Optional[str]:
        _, flow = CoreActions._ctx_and_flow(session)
        pend, persist = CoreActions._workflow_pending_persist_keys(step)
        raw = flow.get(pend)
        if raw is not None:
            today, settings = CoreActions._get_today_settings(tenant)
            idx = choice_to_index(str(raw))
            if idx == 1:
                d = today.isoformat()
                CoreActions._set_flow_fields(session, date=d, appointment_date=d)
                CoreActions._flow_commit_user_reply(flow, pend, persist, d)
                return None
            if idx == 2:
                d = (today + dt.timedelta(days=1)).isoformat()
                CoreActions._set_flow_fields(session, date=d, appointment_date=d)
                CoreActions._flow_commit_user_reply(flow, pend, persist, d)
                return None
            parsed = parse_user_date_input(str(raw).strip(), settings)
            if not parsed:
                return wa(tenant, "wa_salon_invalid_date", date_format=get_display_date_format(settings))
            if parsed < today:
                return wa(tenant, "wa_salon_date_past")
            d = parsed.isoformat()
            CoreActions._set_flow_fields(session, date=d, appointment_date=d)
            CoreActions._flow_commit_user_reply(flow, pend, persist, d)
            return None
        today, settings = CoreActions._get_today_settings(tenant)
        tomorrow = today + dt.timedelta(days=1)
        df = get_display_date_format(settings)
        lines = [step.label or wa(tenant, "wa_salon_choose_date")]
        lines.append(f"1) Today ({format_date_for_display(today, settings)})")
        lines.append(f"2) Tomorrow ({format_date_for_display(tomorrow, settings)})")
        lines.append(f"3) {wa(tenant, 'wa_salon_date_option_other', date_format=df)}")
        return "\n".join(lines)

    @staticmethod
    async def _run_select_time(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> Optional[str]:
        _, flow = CoreActions._ctx_and_flow(session)
        view = CoreActions._session_booking_view(session)
        pend, persist = CoreActions._workflow_pending_persist_keys(step)
        raw = flow.get(pend)
        if raw is not None:
            slots = view.get("available_slots") or []
            picked = CoreActions._pick_from_list(str(raw), slots)
            if picked:
                CoreActions._set_flow_fields(session, selected_slot=picked, time=picked, appointment_time=picked)
                CoreActions._flow_commit_user_reply(flow, pend, persist, str(picked))
                return None
            if not slots:
                return wa(tenant, "wa_salon_no_slots_list")
            return wa(tenant, "wa_salon_pick_time_range", max_n=len(slots))
        prof, date = view.get("professional"), view.get("date")
        if not prof or not date:
            return wa(tenant, "wa_salon_missing_prof_date")
        if prof == "Auto-assigned":
            prof_name, _ = await SalonActions._auto_assign_first_slot(tenant, view.get("service"), date)
            if not prof_name:
                return wa(tenant, "wa_salon_no_slots_any_pro")
            CoreActions._set_flow_fields(session, professional=prof_name)
            prof = prof_name
        slots = await SalonActions.get_available_slots(tenant, professional_name=prof, date_str=date)
        if not slots:
            return wa(tenant, "wa_salon_no_slots", professional=prof, date=date)
        flow["available_slots"] = slots
        lines = [step.label or wa(tenant, "wa_salon_time_slots_header", professional=prof, date=date)]
        for i, time in enumerate(slots, start=1):
            lines.append(f"{i}) {time}")
        lines.append(wa(tenant, "wa_salon_pick_time_hint"))
        return "\n".join(lines)

    @staticmethod
    async def _run_auto_assign_time(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> Optional[
        str]:
        view = CoreActions._session_booking_view(session)
        date = view.get("date")
        if not date:
            today, _ = CoreActions._get_today_settings(tenant)
            date = today.isoformat()
            CoreActions._set_flow_fields(session, date=date)
        prof, slot = await SalonActions._auto_assign_first_slot(tenant, view.get("service"), date)
        if not prof or not slot:
            return wa(tenant, "wa_salon_auto_no_slots")
        CoreActions._set_flow_fields(session, professional=prof, selected_slot=slot, time=slot, appointment_time=slot)
        return None

    @staticmethod
    async def _run_confirm_booking_prompt(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> \
            Optional[str]:
        from app.services.whatsapp.workflow_message_helper import get_confirmation_msg

        _, flow = CoreActions._ctx_and_flow(session)
        pend, persist = CoreActions._workflow_pending_persist_keys(step)
        raw = flow.get(pend)
        if raw is not None:
            ok, detail = CoreActions.validate_confirm_yes_no(tenant, str(raw))
            raw_s = str(raw).strip()
            if ok:
                CoreActions._flow_commit_user_reply(flow, pend, persist, raw_s)
                return None
            if detail == "cancelled":
                CoreActions._flow_commit_user_reply(flow, pend, persist, raw_s)
                return wa(tenant, "wa_salon_booking_cancelled")
            return wa(tenant, "wa_salon_confirm_yes_no")
        return get_confirmation_msg(tenant, CoreActions._session_booking_view(session))

    @staticmethod
    async def _run_finalize_booking(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> Optional[
        str]:
        from app.services.whatsapp.usecases.salon.booking_flow import _finalize_booking

        booking_msg = (await _finalize_booking(tenant, phone, session) or "").strip()
        custom = (step.label or "").strip()
        if custom:
            return (
                WMSG.MSG_SALON_BOOKING_WITH_CUSTOM_SUFFIX.format(booking_msg=booking_msg, custom=custom)
                if booking_msg
                else custom
            )
        return booking_msg or None

    @staticmethod
    async def _run_cancel_appointment(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> str:
        from app.services.whatsapp.usecases.salon.cancel_flow import (
            handle_cancel_appointment_legacy_fsm,
            handle_cancel_appointment_workflow,
        )

        ctx = session.get("ctx") or {}
        if ctx.get("workflow_id"):
            return await handle_cancel_appointment_workflow(tenant, phone, session, step)
        params = SalonActions._workflow_step_menu_params(step, session)
        cc = get_tenant_service()._get_tenant_country_code(tenant)
        return await handle_cancel_appointment_legacy_fsm(tenant, params, phone, phone, cc)

    @staticmethod
    async def _run_reschedule_appointment(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> str:
        from app.services.whatsapp.usecases.salon.reschedule_flow import (
            handle_reschedule_appointment_legacy_fsm,
            handle_reschedule_appointment_workflow,
        )

        ctx = session.get("ctx") or {}
        if ctx.get("workflow_id"):
            return await handle_reschedule_appointment_workflow(tenant, phone, session, step)
        params = SalonActions._workflow_step_menu_params(step, session)
        cc = get_tenant_service()._get_tenant_country_code(tenant)
        return await handle_reschedule_appointment_legacy_fsm(tenant, params, phone, phone, cc)

    @staticmethod
    async def _run_suggest_professional(
            tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep
    ) -> str:
        params = dict(step.params or {})
        query = (params.get("input") or params.get("query") or "").strip() or SalonActions._workflow_text_input(
            step, session
        )
        matches = SalonActions._ai_professional_matches(tenant, query)
        if not matches:
            return WMSG.MSG_SALON_NO_PRO_MATCH
        lines = [WMSG.MSG_SALON_PRO_RECOMMEND_HEADER]
        for p in matches:
            lines.append(
                WMSG.MSG_SALON_SUGGEST_PRO_BULLET.format(name=p.get("name"), price=p.get("price")),
            )
        lines.append(WMSG.MSG_SALON_BOOK_WITH_NAME_HINT)
        return "\n".join(lines)

    @staticmethod
    async def _run_professional_details(
            tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep
    ) -> str:
        params = dict(step.params or {})
        query = (params.get("input") or params.get("query") or "").strip() or SalonActions._workflow_text_input(
            step, session
        )
        matches = SalonActions._ai_professional_matches(tenant, query)
        if not matches:
            return WMSG.MSG_SALON_NO_PRO_DETAILS
        p = matches[0]
        slots = await SalonActions.get_available_slots(tenant, professional_name=p.get("name"), limit=3)
        slot_text = (
            WMSG.MSG_SALON_PRO_SLOTS_TODAY.format(slots=", ".join(slots))
            if slots
            else WMSG.MSG_SALON_PRO_NO_SLOTS_TODAY
        )
        return (
            WMSG.MSG_SALON_PRO_DETAIL_BLOCK.format(
                name=p.get("name"),
                price=p.get("price"),
                slots=slot_text,
            )
            + "\n\n"
            + WMSG.MSG_SALON_BOOK_APPOINTMENT_PROMPT
        )

    # ------------------------------------------------------------------ workflow dispatch
    @staticmethod
    def _norm_workflow_code(action_code: str) -> str:
        c = (action_code or "").strip().lower()
        if c.startswith("salon."):
            c = c[6:]
        return c

    @staticmethod
    async def try_run(
            action_code: str,
            tenant: str,
            phone: str,
            session: Dict[str, Any],
            step: WorkflowStep,
    ) -> Tuple[bool, Optional[str]]:
        """Dispatch normalized ``action_code`` via ``_SALON_RUN_HANDLERS`` (workflow vs menu shapes differ per handler)."""
        c = SalonActions._norm_workflow_code(action_code)
        handler = _SALON_RUN_HANDLERS.get(c)
        if not handler:
            return False, None
        return True, await run_handler_and_await(
            handler, tenant=tenant, phone=phone, session=session, step=step
        )

    @staticmethod
    def try_input(
            action_code: str,
            tenant: str,
            phone: str,
            session: Dict[str, Any],
            step: WorkflowStep,
            user_input: str,
    ) -> Tuple[bool, bool, Optional[str]]:
        return False, True, None


# Handler maps (after class; use .lower() keys)
_SALON_RUN_HANDLERS: Dict[str, Callable[..., Any]] = {
    SHOW_SERVICES: SalonActions._run_show_services,
    SHOW_PROFESSIONALS: SalonActions.run_show_professionals,
    SELECT_DATE: SalonActions._run_select_date,
    SELECT_TIME: SalonActions._run_select_time,
    CONFIRM_PROMPT: SalonActions._run_confirm_booking_prompt,
    CONFIRM_BOOKING: SalonActions._run_confirm_booking_prompt,
    FINALIZE_BOOKING: SalonActions._run_finalize_booking,
    AUTO_ASSIGN_TIME: SalonActions._run_auto_assign_time,
    CANCEL_APPOINTMENT: SalonActions._run_cancel_appointment,
    RESCHEDULE_APPOINTMENT: SalonActions._run_reschedule_appointment,
    SUGGEST_PROFESSIONAL: SalonActions._run_suggest_professional,
    PROFESSIONAL_DETAILS: SalonActions._run_professional_details,
}


# Module API (action_executor + clinic adapter)
async def try_salon_run(
        action_code: str,
        tenant: str,
        phone: str,
        session: Dict[str, Any],
        step: WorkflowStep,
) -> Tuple[bool, Optional[str]]:
    """Registered in :mod:`app.services.whatsapp.action_executor` (after clinic, before store)."""
    return await SalonActions.try_run(action_code, tenant, phone, session, step)


# Backward compatibility for external imports
_run_show_professionals = SalonActions.run_show_professionals
get_available_slots = SalonActions.get_available_slots
