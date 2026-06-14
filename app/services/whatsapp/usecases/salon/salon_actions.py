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
    SHOW_SERVICE_PRICES,
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
    def _first_configured_slot(tenant: str, prof: str) -> str:
        """Return the first available HH:MM from the professional's configured slots, or '09:00'."""
        try:
            pros = get_professional_service().get_professionals(tenant)
            for p in pros:
                pname = getattr(p, "name", p.get("name") if isinstance(p, dict) else None)
                if str(pname) == prof:
                    pslots = getattr(p, "slots", p.get("slots") if isinstance(p, dict) else []) or []
                    for ps in pslots:
                        t = ps.get("time") if isinstance(ps, dict) else getattr(ps, "time", None)
                        st = (ps.get("status") if isinstance(ps, dict) else getattr(ps, "status", "available")) or "available"
                        if t and str(st).lower() == "available":
                            return str(t)
        except Exception:
            pass
        return "09:00"

    @staticmethod
    async def _ensure_booking_defaults(tenant: str, session: Dict[str, Any]) -> None:
        """Auto-fill missing booking fields so any workflow step order works.

        Fills: date (today), professional (first available), selected_slot (first available).
        Safe to call multiple times — only populates if a field is absent.
        """
        view = CoreActions._session_booking_view(session)

        # 1. Date → today when not set (walk-in / date-flexible booking)
        if not view.get("date"):
            today, _ = CoreActions._get_today_settings(tenant)
            CoreActions._set_flow_fields(session, date=today.isoformat(), appointment_date=today.isoformat())
            view = CoreActions._session_booking_view(session)

        date = view["date"]

        # 2. Professional → auto-assign when missing or placeholder
        prof = view.get("professional")
        if not prof or prof == WMSG.LABEL_AUTO_ASSIGNED:
            auto_prof, auto_slot = await SalonActions._auto_assign_first_slot(
                tenant, view.get("service"), date
            )
            if auto_prof:
                CoreActions._set_flow_fields(session, professional=auto_prof)
                if auto_slot and not view.get("selected_slot"):
                    CoreActions._set_flow_fields(
                        session,
                        selected_slot=auto_slot,
                        time=auto_slot,
                        appointment_time=auto_slot,
                    )
                view = CoreActions._session_booking_view(session)

        # 3. Slot → first available for the assigned professional/date
        if not view.get("selected_slot"):
            prof = view.get("professional")
            if prof and prof != WMSG.LABEL_AUTO_ASSIGNED:
                slots = await SalonActions.get_available_slots(tenant, professional_name=prof, date_str=date)
                chosen = slots[0] if slots else SalonActions._first_configured_slot(tenant, prof)
                CoreActions._set_flow_fields(
                    session,
                    selected_slot=chosen,
                    time=chosen,
                    appointment_time=chosen,
                )

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
            return wa(tenant, "wa_salon_no_services")
        lines = [step.label or wa(tenant, "wa_salon_pick_service")]
        for i, s in enumerate(services, start=1):
            lines.append(f"{i}) {s}")
        flow["available_services"] = services
        return "\n".join(lines)

    @staticmethod
    def _currency_symbol(tenant: str) -> str:
        settings = get_tenant_service().get_tenant_settings(tenant) or {}
        currency = str(settings.get("currency") or "INR").strip().upper()
        if currency == "INR":
            return "₹"
        if currency == "USD":
            return "$"
        if currency == "EUR":
            return "€"
        if currency == "GBP":
            return "£"
        return f"{currency} "

    @staticmethod
    async def _run_show_service_prices(
            tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep
    ) -> Optional[str]:
        """List active salon services with price and duration (read-only, no booking input)."""
        db_services = Storage.list_services(tenant, active=True)
        if not db_services:
            return wa(tenant, "wa_salon_no_services")
        sym = SalonActions._currency_symbol(tenant)
        header = (step.label or "").strip() or wa(tenant, "wa_salon_service_prices_header")
        lines = [header, ""]
        for i, svc in enumerate(db_services, start=1):
            name = (svc.get("name") or "Service").strip()
            price = float(svc.get("price") or 0)
            duration = int(svc.get("duration") or 0)
            if price > 0:
                price_part = f"{sym}{price:,.0f}"
            else:
                price_part = wa(tenant, "wa_salon_service_price_on_request")
            dur_part = f" ({duration} min)" if duration > 0 else ""
            lines.append(f"{i}) {name} – {price_part}{dur_part}")
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
    async def _handle_select_time_pending(
            tenant: str,
            phone: str,
            session: Dict[str, Any],
            step: WorkflowStep,
            raw: str,
            view: Dict[str, Any],
            flow: Dict[str, Any],
            pend: str,
            persist: str,
    ) -> Optional[str]:
        """Resolve SELECT_TIME user reply (numeric index or natural-language clock time)."""
        from app.services.whatsapp.usecases.salon.booking_ai_gate import is_ai_enabled_in_flow
        from app.services.whatsapp.usecases.salon.booking_time_utils import (
            format_time_12h,
            parse_time_input,
            slots_near_time,
        )

        slots = view.get("available_slots") or []
        raw_s = str(raw).strip()
        parsed_time = parse_time_input(raw_s)
        if parsed_time is None and AIPredictor and is_ai_enabled_in_flow(tenant):
            try:
                parsed_time = AIPredictor().parse_preferred_time(raw_s)
            except Exception:
                parsed_time = None

        if parsed_time:
            hour_24, minute = parsed_time
            prof = view.get("professional")
            date = view.get("date")
            pool = slots
            if prof and date:
                pool = await SalonActions.get_available_slots(
                    tenant, professional_name=prof, limit=96, date_str=date
                ) or slots
            nearby = slots_near_time(pool, hour_24, minute, window_minutes=90, max_slots=8)
            display_time = format_time_12h(hour_24, minute)
            if nearby:
                flow["available_slots"] = nearby
                lines = [WMSG.MSG_SLOTS_NEAR.format(time=display_time)]
                for i, time in enumerate(nearby, start=1):
                    lines.append(f"{i}) {time}")
                lines.append(wa(tenant, "wa_salon_pick_time_hint"))
                return "\n".join(lines)
            lines = [WMSG.MSG_NO_SLOTS_NEAR_TIME.format(time=display_time)]
            for i, time in enumerate(slots, start=1):
                lines.append(f"{i}) {time}")
            lines.append(wa(tenant, "wa_salon_pick_time_hint"))
            return "\n".join(lines)

        picked = CoreActions._pick_from_list(raw_s, slots)
        if picked:
            CoreActions._set_flow_fields(session, selected_slot=picked, time=picked, appointment_time=picked)
            CoreActions._flow_commit_user_reply(flow, pend, persist, str(picked))
            return None
        if not slots:
            prof = view.get("professional")
            date = view.get("date")
            if prof and date:
                slots = await SalonActions.get_available_slots(
                    tenant, professional_name=prof, date_str=date
                )
                if slots:
                    flow["available_slots"] = slots
                    picked = CoreActions._pick_from_list(raw_s, slots)
                    if picked:
                        CoreActions._set_flow_fields(
                            session, selected_slot=picked, time=picked, appointment_time=picked
                        )
                        CoreActions._flow_commit_user_reply(flow, pend, persist, str(picked))
                        return None
                    return wa(tenant, "wa_salon_pick_time_range", max_n=len(slots))
            return wa(tenant, "wa_salon_no_slots_list")
        return wa(tenant, "wa_salon_pick_time_range", max_n=len(slots))

    @staticmethod
    async def _run_select_time(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> Optional[str]:
        _, flow = CoreActions._ctx_and_flow(session)
        view = CoreActions._session_booking_view(session)
        pend, persist = CoreActions._workflow_pending_persist_keys(step)
        raw = flow.get(pend)
        if raw is not None:
            return await SalonActions._handle_select_time_pending(
                tenant, phone, session, step, str(raw), view, flow, pend, persist
            )
        prof, date = view.get("professional"), view.get("date")
        # Auto-fill missing date (walk-in = today) so SELECT_TIME works even without a prior SELECT_DATE step
        if not date:
            today, _ = CoreActions._get_today_settings(tenant)
            date = today.isoformat()
            CoreActions._set_flow_fields(session, date=date, appointment_date=date)
            view = CoreActions._session_booking_view(session)
        # Auto-assign professional if missing or placeholder so SELECT_TIME works without SHOW_PROFESSIONALS
        if not prof or prof == WMSG.LABEL_AUTO_ASSIGNED:
            auto_prof, _ = await SalonActions._auto_assign_first_slot(tenant, view.get("service"), date)
            if not auto_prof:
                return wa(tenant, "wa_salon_no_slots_any_pro")
            CoreActions._set_flow_fields(session, professional=auto_prof)
            prof = auto_prof
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
                ctx_ref = session.setdefault("ctx", {})
                booking_msg = None
                if not ctx_ref.get("booking_finalized"):
                    await SalonActions._ensure_booking_defaults(tenant, session)
                    booking_msg = await SalonActions._run_finalize_booking(tenant, phone, session, step)
                # Always advance to trailing END (and optional FINALIZE) in the same turn.
                ctx_ref["_wa_skip_input_wait_once"] = True
                if (booking_msg or "").strip():
                    return booking_msg
                return None
            if detail == "cancelled":
                CoreActions._flow_commit_user_reply(flow, pend, persist, raw_s)
                return wa(tenant, "wa_salon_booking_cancelled")
            return wa(tenant, "wa_salon_confirm_yes_no")
        # Auto-fill missing booking fields before displaying the summary so that the
        # confirmation message shows real values even when early steps were skipped.
        await SalonActions._ensure_booking_defaults(tenant, session)
        return get_confirmation_msg(tenant, CoreActions._session_booking_view(session))

    @staticmethod
    async def _run_finalize_booking(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> Optional[
        str]:
        from app.services.whatsapp.usecases.salon.booking_flow import _finalize_booking

        # Guard: if CONFIRM_BOOKING already created the appointment, skip silently.
        ctx_ref = session.setdefault("ctx", {})
        if ctx_ref.get("booking_finalized"):
            custom = (step.label or "").strip()
            return custom or None

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
    SHOW_SERVICE_PRICES: SalonActions._run_show_service_prices,
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

# ---------------------------------------------------------------------------
# Self-registration in the central action handler registry.
# ---------------------------------------------------------------------------
def _register_salon_handlers() -> None:
    from app.services.whatsapp.action_handler_registry import register_many
    from app.services.whatsapp.workflow.workflow_step_policy import WORKFLOW_RUN_ONLY_VIA_FLOW_DATA_INPUT
    # Actions that start or continue a stateful booking conversation when invoked
    # directly from a menu node (not inside a workflow).
    _keeps = frozenset({
        SHOW_SERVICES,
        SHOW_PROFESSIONALS,
        CANCEL_APPOINTMENT,
        RESCHEDULE_APPOINTMENT,
    })
    register_many(
        _SALON_RUN_HANDLERS,
        needs_input_codes=WORKFLOW_RUN_ONLY_VIA_FLOW_DATA_INPUT,
        keeps_session_codes=_keeps,
    )


_register_salon_handlers()
