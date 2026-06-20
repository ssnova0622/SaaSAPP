from __future__ import annotations

import datetime as dt
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.container import get_professional_service, get_tenant_service
from app.helpers.constants_action import (
    ASK_NUM_SLOTS,
    AUTO_ASSIGN_TIME,
    CANCEL_APPOINTMENT,
    CONFIRM_BOOKING,
    CONFIRM_PROMPT,
    FINALIZE_BOOKING,
    PRESET_PROFESSIONAL,
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
        """Auto-assign the least-busy professional who has slots on *date*.

        Uses load balancing: among all professionals with available slots, prefer the one
        with the fewest bookings for that date (so no one trainer gets overloaded while
        others sit idle).
        """
        from app.services.whatsapp.usecases.salon.booking_flow import list_professionals
        from app.services.db import collections as db_collections
        import datetime as _dt

        professionals = list_professionals(tenant, date_str=date, service=service)
        if not professionals:
            return None, None

        # Gather available slots and booking counts per professional
        candidates: List[Tuple[int, str, str]] = []   # (booking_count, prof_name, first_slot)
        _tenants, _pros, appts_col = db_collections()

        for p in professionals:
            slots = await SalonActions.get_available_slots(tenant, professional_name=p, date_str=date)
            if not slots:
                continue
            # Count existing bookings for this professional on this date
            try:
                d = _dt.date.fromisoformat(date)
                day_start = _dt.datetime(d.year, d.month, d.day, 0, 0, 0)
                day_end   = day_start + _dt.timedelta(days=1)
                booking_count = appts_col.count_documents({
                    "tenant": tenant,
                    "professional": p,
                    "start": {"$gte": day_start, "$lt": day_end},
                    "status": {"$in": ["booked", "completed"]},
                })
            except Exception:
                booking_count = 0
            candidates.append((booking_count, p, slots[0]))

        if not candidates:
            return None, None

        # Pick the trainer with the fewest bookings (least-loaded)
        candidates.sort(key=lambda x: x[0])
        _, best_prof, first_slot = candidates[0]
        return best_prof, first_slot

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

        # 2. Professional → auto-assign when missing or placeholder.
        # Skip if sentinel is already set (no-professional booking mode).
        prof = view.get("professional")
        _sentinels = {WMSG.LABEL_AUTO_ASSIGNED, WMSG.PROF_SENTINEL_NO_PROF}
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
            else:
                # No professionals in DB — mark as no-professional mode if not already set
                if not prof:
                    CoreActions._set_flow_fields(session, professional=WMSG.PROF_SENTINEL_NO_PROF)

        # 3. Slot → first available for the assigned professional/date
        if not view.get("selected_slot"):
            prof = view.get("professional")
            if prof and prof not in _sentinels:
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
        params = dict(step.params or {})

        # ── Service filtering via step params ─────────────────────────────────
        # params.services : list of exact service names to show (whitelist)
        #   e.g. ["PT Session – 20 Min", "PT Session – 30 Min", "PT Session – 1 Hr"]
        # params.category : show only services matching this category string
        #   e.g. "court" or "pt"  (case-insensitive substring match on name OR category field)
        # params.exclude  : list of service names to hide from this workflow
        whitelist  = [str(n).strip() for n in (params.get("services") or []) if str(n).strip()]
        category   = str(params.get("category") or "").strip().lower()
        exclude    = {str(n).strip().lower() for n in (params.get("exclude") or [])}

        all_active = [s for s in db_services if s.get("active", True)]

        if whitelist:
            wl_lower = [w.lower() for w in whitelist]
            filtered = [s for s in all_active if str(s.get("name") or "").strip().lower() in wl_lower]
            # Preserve whitelist order
            name_map = {str(s.get("name") or "").strip().lower(): s for s in filtered}
            filtered = [name_map[w] for w in wl_lower if w in name_map]
        elif category:
            filtered = [
                s for s in all_active
                if category in str(s.get("name") or "").lower()
                or category in str(s.get("category") or "").lower()
            ]
        else:
            filtered = all_active

        if exclude:
            filtered = [s for s in filtered if str(s.get("name") or "").strip().lower() not in exclude]

        services = [str(s["name"]).strip() for s in filtered if s.get("name")]
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
            # Don't try fetching professional slots when no-professional sentinel is set
            _is_sentinel = prof in (WMSG.PROF_SENTINEL_NO_PROF, WMSG.LABEL_AUTO_ASSIGNED)
            if prof and date and not _is_sentinel:
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
            # Read resolved values from flow_data (set by _run_select_time via _resolve_slot_duration)
            view_now = CoreActions._session_booking_view(session)
            num_slots = int(view_now.get("num_slots") or
                            (step.params or {}).get("max_slots") or
                            (step.params or {}).get("num_slots") or 1)
            # slot_duration_minutes comes from flow_data (resolved via service → tenant → default)
            slot_minutes = int(view_now.get("slot_duration_minutes") or
                               (step.params or {}).get("slot_duration_minutes") or 60)
            try:
                hh, mm = [int(x) for x in picked.split(":", 1)]
                total_minutes = num_slots * slot_minutes
                end_dt = dt.datetime(2000, 1, 1, hh, mm) + dt.timedelta(minutes=total_minutes)
                end_time = end_dt.strftime("%H:%M")
                CoreActions._set_flow_fields(session, selected_slot=picked, time=picked,
                                             appointment_time=picked, end_time=end_time,
                                             num_slots=num_slots,
                                             slot_duration_minutes=slot_minutes)
            except Exception:
                CoreActions._set_flow_fields(session, selected_slot=picked, time=picked,
                                             appointment_time=picked)
            CoreActions._flow_commit_user_reply(flow, pend, persist, str(picked))
            return None
        if not slots:
            prof = view.get("professional")
            date = view.get("date")
            _is_sentinel = prof in (WMSG.PROF_SENTINEL_NO_PROF, WMSG.LABEL_AUTO_ASSIGNED)
            if prof and date and not _is_sentinel:
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
    def _resolve_slot_duration(tenant: str, step: WorkflowStep, service_name: Optional[str] = None) -> int:
        """Return the slot duration in minutes for a booking step.

        Priority (highest → lowest):
        1. ``step.params["slot_duration_minutes"]``  — explicit workflow-level override
        2. Selected service ``duration`` field from the Services catalogue
        3. Tenant setting ``appointments.slot_duration_minutes``
        4. Hard default: 60 minutes

        This allows admins to configure durations once per service (e.g. "PT Session = 20 min",
        "Badminton Court = 60 min") without editing workflow step params for every workflow.
        """
        params = dict(step.params or {})

        # 1. Explicit step param — highest priority
        explicit = params.get("slot_duration_minutes") or params.get("slot_duration")
        if explicit:
            try:
                return max(1, int(explicit))
            except (ValueError, TypeError):
                pass

        # 2. Service duration from the Services catalogue
        if service_name:
            try:
                from app.services.storage_mongo import Storage
                services = Storage.list_services(tenant)
                for svc in services:
                    if str(svc.get("name") or "").strip().lower() == service_name.strip().lower():
                        dur = int(svc.get("duration") or 0)
                        if dur > 0:
                            return dur
            except Exception:
                pass

        # 3. Tenant-level default
        try:
            settings = get_tenant_service().get_tenant_settings(tenant) or {}
            appt_settings = settings.get("appointments") or {}
            tenant_dur = int(appt_settings.get("slot_duration_minutes") or 0)
            if tenant_dur > 0:
                return tenant_dur
        except Exception:
            pass

        # 4. Hard default
        return 60

    @staticmethod
    def _multi_slot_header(step: WorkflowStep, base_header: str, slot_minutes: int = 60) -> str:
        """Prefix slot list with total-duration hint when max_slots > 1 (e.g. court bookings)."""
        params = dict(step.params or {})
        max_slots = int(params.get("max_slots") or params.get("num_slots") or 1)
        if max_slots <= 1:
            return base_header
        total_minutes = max_slots * slot_minutes
        if total_minutes % 60 == 0:
            duration_label = f"{total_minutes // 60}h"
        else:
            duration_label = f"{total_minutes}min"
        return f"{base_header}\n(Select your *start time* — we'll reserve {duration_label} from that slot)"

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

        # Resolve slot duration (step params → service duration → tenant default → 60 min)
        # and store in flow_data so _handle_select_time_pending can use it.
        params = dict(step.params or {})
        num_slots = int(params.get("max_slots") or params.get("num_slots") or 1)
        slot_duration_min = SalonActions._resolve_slot_duration(tenant, step, view.get("service"))
        CoreActions._set_flow_fields(session, slot_duration_minutes=slot_duration_min)
        if num_slots > 1:
            CoreActions._set_flow_fields(session, num_slots=num_slots)

        # Honour a step-level professional override (e.g. from step.params set by the workflow designer
        # for tenants where a specific staff member should be pre-selected).
        step_prof = params.get("professional") or params.get("staff")
        if step_prof and str(step_prof).strip() and str(step_prof).strip().lower() not in ("auto-assigned", ""):
            preset_name = str(step_prof).strip()
            if preset_name != prof:
                CoreActions._set_flow_fields(session, professional=preset_name)
                prof = preset_name

        # Auto-fill missing date (walk-in = today) so SELECT_TIME works even without a prior SELECT_DATE step
        if not date:
            today, _ = CoreActions._get_today_settings(tenant)
            date = today.isoformat()
            CoreActions._set_flow_fields(session, date=date, appointment_date=date)
            view = CoreActions._session_booking_view(session)

        # ── Smart no-professional detection ────────────────────────────────────────
        # Force sentinel if:
        #   (a) PRESET_PROFESSIONAL already set it, OR
        #   (b) The workflow has no SHOW_PROFESSIONALS step (auto-inferred from workflow definition)
        # This removes the need to add PRESET_PROFESSIONAL to every court/resource workflow.
        workflow_has_prof_step = CoreActions._workflow_needs_professional(tenant, session)
        if not workflow_has_prof_step and prof not in (WMSG.PROF_SENTINEL_NO_PROF,) and not prof:
            # No professional step in workflow AND no professional set → resource-based booking
            CoreActions._set_flow_fields(session, professional=WMSG.PROF_SENTINEL_NO_PROF)
            prof = WMSG.PROF_SENTINEL_NO_PROF

        # ── No-professional sentinel path ──────────────────────────────────────────
        # Triggered by: PRESET_PROFESSIONAL(no_professional=true), auto-detection above,
        # or no professionals in the DB.  Shows fallback time slots filtered by booked slots.
        if prof == WMSG.PROF_SENTINEL_NO_PROF:
            raw_slots = SalonActions._filter_slots_by_duration(
                SalonActions._fallback_time_slots(tenant, step), slot_duration_min
            )
            slots = SalonActions._remove_booked_service_slots(
                raw_slots, tenant, view.get("service") or "", date, slot_duration_min
            )
            if not slots:
                svc = view.get("service") or "this service"
                return f"No available slots for {svc} on {date}. Please choose another date."
            flow["available_slots"] = slots
            base_header = step.label or "Choose a time slot:"
            header = SalonActions._multi_slot_header(step, base_header, slot_duration_min)
            lines = [header]
            for i, t in enumerate(slots, start=1):
                lines.append(f"{i}) {t}")
            lines.append(wa(tenant, "wa_salon_pick_time_hint"))
            return "\n".join(lines)

        # ── Normal path — auto-assign professional if missing ──────────────────────
        if not prof or prof in (WMSG.LABEL_AUTO_ASSIGNED, "Auto-assigned"):
            auto_prof, _ = await SalonActions._auto_assign_first_slot(tenant, view.get("service"), date)
            if not auto_prof:
                # No professionals configured at all — fall back to business-hours slots
                CoreActions._set_flow_fields(session, professional=WMSG.PROF_SENTINEL_NO_PROF)
                raw_slots = SalonActions._filter_slots_by_duration(
                    SalonActions._fallback_time_slots(tenant, step), slot_duration_min
                )
                slots = SalonActions._remove_booked_service_slots(
                    raw_slots, tenant, view.get("service") or "", date, slot_duration_min
                )
                if not slots:
                    return f"No available slots for {view.get('service', 'this service')} on {date}. Please choose another date."
                flow["available_slots"] = slots
                base_header = step.label or "Choose a time slot:"
                header = SalonActions._multi_slot_header(step, base_header, slot_duration_min)
                lines = [header]
                for i, t in enumerate(slots, start=1):
                    lines.append(f"{i}) {t}")
                lines.append(wa(tenant, "wa_salon_pick_time_hint"))
                return "\n".join(lines)
            CoreActions._set_flow_fields(session, professional=auto_prof)
            prof = auto_prof

        slots = await SalonActions.get_available_slots(tenant, professional_name=prof, date_str=date)
        if not slots:
            # Professional configured but no slots for this date — try business-hours fallback
            slots = SalonActions._fallback_time_slots(tenant, step)
            if not slots:
                return wa(tenant, "wa_salon_no_slots", professional=prof, date=date)
        # ── Filter slots so intervals match the service/step duration ──────────
        # E.g. if the service is 60 min (Badminton Court), only show slots that are
        # 60 minutes apart (06:00, 07:00, 08:00…) — not 30-min intervals.
        slots = SalonActions._filter_slots_by_duration(slots, slot_duration_min)
        flow["available_slots"] = slots
        base_header = step.label or wa(tenant, "wa_salon_time_slots_header", professional=prof, date=date)
        header = SalonActions._multi_slot_header(step, base_header, slot_duration_min)
        lines = [header]
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
    def _remove_booked_service_slots(
        slots: List[str],
        tenant: str,
        service: str,
        date_str: str,
        slot_duration_min: int,
    ) -> List[str]:
        """Remove time slots that are already booked for a given service (court/room).

        Used for no-professional bookings where the service itself is the resource.
        Queries appointments by service name + date and excludes any slot whose
        time window [start, start+duration) overlaps an existing booking.

        IMPORTANT: Uses the stored `time` field (local time string like "06:00") for
        overlap arithmetic rather than the `start` datetime field, which is stored in
        UTC. Comparing a naive local-time slot datetime against a UTC-stored datetime
        causes incorrect results (e.g. local 06:00 vs UTC 00:30 → no overlap detected).
        All comparisons are done in integer minutes-from-midnight to avoid this.
        """
        if not service or not date_str or not slots:
            return slots
        try:
            import datetime as _dt
            from app.services.db import collections as _cols
            from app.helpers.constants import APPOINTMENT_STATUS_BOOKED, APPOINTMENT_STATUS_NEEDS_RESCHEDULE
            _tenants, _pros, appts_col = _cols()
            d = _dt.date.fromisoformat(date_str)
            # Use naive UTC boundaries — PyMongo treats naive datetimes as UTC.
            # Appointments are stored with UTC start values so this query is correct.
            day_start = _dt.datetime(d.year, d.month, d.day, 0, 0, 0)
            day_end   = day_start + _dt.timedelta(days=1)
            # Fetch ALL bookings for this service on this date — regardless of professional.
            # For courts/shared resources the service name IS the resource identifier.
            booked_docs = list(appts_col.find({
                "tenant": tenant,
                "service": service,
                "status": {"$in": [APPOINTMENT_STATUS_BOOKED, APPOINTMENT_STATUS_NEEDS_RESCHEDULE]},
                "start": {"$gte": day_start, "$lt": day_end},
            }, {"start": 1, "end": 1, "time": 1}))

            if not booked_docs:
                return slots

            # Build booked intervals in minutes-from-midnight using the stored local
            # `time` string (e.g. "06:00") to avoid UTC/local-time mismatch.
            booked_intervals_min: List[tuple] = []
            for doc in booked_docs:
                time_str = str(doc.get("time") or "").strip()
                a_start_dt = doc.get("start")
                a_end_dt   = doc.get("end")

                # Derive start_min from the local time string stored at booking time.
                if time_str and ":" in time_str:
                    try:
                        th, tm = int(time_str.split(":")[0]), int(time_str.split(":")[1])
                        start_min = th * 60 + tm
                    except Exception:
                        continue
                else:
                    # Fallback: no time string — skip this doc to avoid wrong comparison.
                    continue

                # Derive duration from the UTC start/end datetimes.
                # total_seconds() is timezone-independent so subtraction is safe even
                # when both fields are naive-UTC.
                if isinstance(a_start_dt, _dt.datetime) and isinstance(a_end_dt, _dt.datetime):
                    try:
                        dur_min = int((a_end_dt - a_start_dt).total_seconds() / 60)
                    except Exception:
                        dur_min = slot_duration_min
                else:
                    dur_min = slot_duration_min

                if dur_min <= 0:
                    dur_min = slot_duration_min

                booked_intervals_min.append((start_min, start_min + dur_min))

            if not booked_intervals_min:
                return slots

            # Filter candidate slots using integer minute arithmetic (no datetime, no tz).
            available = []
            for t in slots:
                try:
                    parts = t.strip().split(":")
                    hh = int(parts[0])
                    mm = int(parts[1]) if len(parts) > 1 else 0
                    s_start_min = hh * 60 + mm
                    s_end_min   = s_start_min + max(slot_duration_min, 1)
                    # Interval overlap: [s_start, s_end) ∩ [b_start, b_end) ≠ ∅
                    overlaps = any(
                        s_start_min < b_end and b_start < s_end_min
                        for b_start, b_end in booked_intervals_min
                    )
                    if not overlaps:
                        available.append(t)
                except Exception:
                    available.append(t)

            return available if available else []
        except Exception:
            return slots  # On any error, return original list (don't break the flow)

    @staticmethod
    def _filter_slots_by_duration(slots: List[str], slot_duration_min: int) -> List[str]:
        """Thin out a slot list so consecutive entries are at least *slot_duration_min* apart.

        Rules:
        1. Parse all slot times into total-minutes-from-midnight.
        2. Detect the *minimum gap* between consecutive raw slots.
        3. If ``slot_duration_min <= min_gap`` the list is already coarse enough — return unchanged.
           (e.g. 20-min PT session with trainer slots every 30 min → show all trainer slots)
        4. Otherwise keep only slots whose minutes-from-midnight are divisible by slot_duration_min.
           (e.g. 60-min Badminton Court with 30-min professional slots → keep 06:00, 07:00, 08:00…)
        5. If filtering would remove *everything*, fall back to the original list.
        """
        if not slots or slot_duration_min <= 0:
            return slots

        # Parse times
        parsed: List[tuple] = []
        for t in slots:
            try:
                parts = t.strip().split(":")
                hh = int(parts[0])
                mm = int(parts[1]) if len(parts) > 1 else 0
                parsed.append((hh * 60 + mm, t))
            except Exception:
                parsed.append((-1, t))  # unparseable — keep as-is

        parseable = [(m, t) for m, t in parsed if m >= 0]
        if len(parseable) >= 2:
            parseable_sorted = sorted(parseable, key=lambda x: x[0])
            min_gap = min(
                parseable_sorted[i + 1][0] - parseable_sorted[i][0]
                for i in range(len(parseable_sorted) - 1)
            )
        else:
            min_gap = slot_duration_min  # single slot — no filtering needed

        # Only filter when the service is longer than the raw slot interval
        if slot_duration_min <= min_gap:
            return slots

        filtered = [t for m, t in parsed if m >= 0 and m % slot_duration_min == 0]
        # Keep unparseable entries
        filtered += [t for m, t in parsed if m < 0]
        return filtered if filtered else slots

    @staticmethod
    def _fallback_time_slots(tenant: str, step: WorkflowStep) -> List[str]:
        """Return time slots for tenants with no professionals configured.

        Priority:
        1. ``step.params["time_slots"]`` — admin-configured list e.g. ["09:00","10:00","11:00"]
        2. ``step.params["start_hour"]`` / ``step.params["end_hour"]`` — custom range
        3. Tenant settings ``business_start_hour`` / ``business_end_hour``
        4. Hard default: 9 AM – 5 PM every hour
        """
        params = dict(step.params or {})

        # 1. Admin provided explicit slot list
        explicit = params.get("time_slots") or []
        if isinstance(explicit, list) and explicit:
            return [str(t) for t in explicit if str(t).strip()]

        # 2. Derive from start/end hour in step params or tenant settings
        try:
            from app.core.container import get_tenant_service
            settings = get_tenant_service().get_tenant_settings(tenant) or {}
        except Exception:
            settings = {}

        start_h = int(params.get("start_hour") or settings.get("business_start_hour") or 9)
        end_h   = int(params.get("end_hour")   or settings.get("business_end_hour")   or 17)
        interval = int(params.get("slot_interval_minutes") or 60)  # default 1-hour slots

        slots: List[str] = []
        import datetime as _dt
        current = _dt.datetime(2000, 1, 1, start_h, 0)
        end_dt  = _dt.datetime(2000, 1, 1, end_h, 0)
        while current < end_dt:
            slots.append(current.strftime("%H:%M"))
            current += _dt.timedelta(minutes=interval)

        return slots or ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]

    @staticmethod
    async def _run_ask_num_slots(
        tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep
    ) -> Optional[str]:
        """Ask the user how many consecutive slots they want (e.g. 1 hr vs 2 hr for a court).

        step.params:
          max_slots             — maximum choice offered (default 2)
          slot_label            — unit label shown (default "hour")
          slot_duration_minutes — duration per slot; falls back to service/tenant default
        """
        _, flow = CoreActions._ctx_and_flow(session)
        pend, persist = CoreActions._workflow_pending_persist_keys(step)
        params = dict(step.params or {})
        max_slots  = int(params.get("max_slots") or 2)
        slot_label = str(params.get("slot_label") or "hour")

        # ── Handle returning user answer ───────────────────────────────────────
        raw = flow.get(pend)
        if raw is not None:
            try:
                chosen = int(str(raw).strip())
            except ValueError:
                # Try matching the label ("1 hour", "2 hours", "1", "2")
                raw_lower = str(raw).strip().lower()
                chosen = None
                for n in range(1, max_slots + 1):
                    lbl_singular = f"{n} {slot_label}"
                    lbl_plural   = f"{n} {slot_label}s"
                    if raw_lower in (str(n), lbl_singular, lbl_plural):
                        chosen = n
                        break

            if chosen and 1 <= chosen <= max_slots:
                # Resolve slot_duration_minutes now so SELECT_TIME can read it from flow_data
                view = CoreActions._session_booking_view(session)
                slot_dur = SalonActions._resolve_slot_duration(tenant, step, view.get("service"))
                CoreActions._set_flow_fields(session, num_slots=chosen, slot_duration_minutes=slot_dur)
                CoreActions._flow_commit_user_reply(flow, pend, persist, str(chosen))
                return None

            # Invalid input — re-prompt
            return (
                f"Please reply with a number between 1 and {max_slots}.\n"
                + "\n".join(
                    f"{n}) {n} {slot_label}" + ("s" if n > 1 else "")
                    for n in range(1, max_slots + 1)
                )
            )

        # ── First time — show options ──────────────────────────────────────────
        header = step.label or f"How many {slot_label}s would you like to book?"
        lines = [header]
        for n in range(1, max_slots + 1):
            unit = slot_label + ("s" if n > 1 else "")
            lines.append(f"{n}) {n} {unit}")
        lines.append("Reply with a number to choose.")
        return "\n".join(lines)

    @staticmethod
    async def _run_preset_professional(
        tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep
    ) -> Optional[str]:
        """Silently set a professional from workflow step params — no user interaction.

        Workflow designers use this step when:
        - The tenant does not expose professional selection (e.g. school parent-teacher meetings,
          gym classes, camps) — set params.professional = "Auto-assigned" for auto-pick.
        - A specific staff member should be pre-selected (e.g. a particular teacher or trainer)
          — set params.professional = "Mrs. Priya Kumar".
        - No professionals are configured at all — the system will use business-hours time slots.

        Step params
        -----------
        professional : str
            The exact professional name, "Auto-assigned" to auto-pick, or omit for no-professional mode.
        """
        params = dict(step.params or {})
        preset = (params.get("professional") or params.get("staff") or "").strip()

        # ── no_professional=true forces sentinel regardless of real professionals in DB ──
        # Use this for resource-based bookings (courts, rooms, lanes) where the service
        # name IS the resource and should be checked for overlaps — NOT a trainer.
        # Also triggered when params.professional = "no_professional" or "__no_professional__".
        force_no_prof = (
            str(params.get("no_professional") or "").strip().lower() in ("true", "1", "yes")
            or preset.lower() in (WMSG.PROF_SENTINEL_NO_PROF, "no_professional", "no professional")
        )

        if force_no_prof:
            CoreActions._set_flow_fields(session, professional=WMSG.PROF_SENTINEL_NO_PROF)
        elif preset and preset.lower() not in ("auto-assigned", ""):
            # Specific staff name provided — use it directly
            CoreActions._set_flow_fields(session, professional=preset)
        else:
            # Auto-assign: pick the least-busy professional for the session's date/service
            view = CoreActions._session_booking_view(session)
            date = view.get("date")
            if not date:
                today, _ = CoreActions._get_today_settings(tenant)
                date = today.isoformat()
                CoreActions._set_flow_fields(session, date=date)
            auto_prof, _ = await SalonActions._auto_assign_first_slot(tenant, view.get("service"), date)
            if auto_prof:
                CoreActions._set_flow_fields(session, professional=auto_prof)
            else:
                # No professionals registered — store the no-professional sentinel.
                # SELECT_TIME will detect this and show business-hours slots instead of erroring.
                CoreActions._set_flow_fields(session, professional=WMSG.PROF_SENTINEL_NO_PROF)

        # Silent configuration step — no reply, advance immediately to next step.
        ctx_ref = session.setdefault("ctx", {})
        ctx_ref["_wa_skip_input_wait_once"] = True
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
                ctx_ref = session.setdefault("ctx", {})
                booking_msg = None
                if not ctx_ref.get("booking_finalized"):
                    await SalonActions._ensure_booking_defaults(tenant, session)
                    booking_msg = await SalonActions._run_finalize_booking(tenant, phone, session, step)

                # ── Only commit the reply (advance past CONFIRM step) when booking succeeded.
                # If booking failed, leave the pending reply in place so the workflow stays on
                # CONFIRM_BOOKING and the user can choose again (e.g. try a different slot).
                if ctx_ref.get("booking_finalized"):
                    CoreActions._flow_commit_user_reply(flow, pend, persist, raw_s)
                    ctx_ref["_wa_skip_input_wait_once"] = True
                else:
                    # Booking failed — wipe the pending reply so CONFIRM step re-prompts
                    flow.pop(pend, None)

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
    PRESET_PROFESSIONAL: SalonActions._run_preset_professional,
    ASK_NUM_SLOTS: SalonActions._run_ask_num_slots,
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
