from __future__ import annotations

import datetime as dt
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.container import get_tenant_service
from app.helpers.constants_action import (API_CALL, ASK_NAME, COLLECT_DETAILS, COLLECT_PATIENT_INFO_ALIAS, END,
                                          OPEN_TICKET, OPEN_URL, SUBMIT_FEEDBACK, BOOKING_SUMMARY)
from app.helpers.date_utils import get_tenant_timezone_zoneinfo
from app.services.whatsapp.usecases.core.feedback_messaging import persist_customer_feedback
from app.services.whatsapp.workflow.workflow_step_policy import (
    workflow_user_reply_flow_key,
    workflow_user_reply_pending_key,
)
from app.services.whatsapp.action_support import run_handler_and_await
from app.services.whatsapp.usecases.utils import choice_to_index

try:
    from app.services.ai import AIPredictor  # type: ignore
except Exception:
    AIPredictor = None  # type: ignore
from app.models.workflow import WorkflowStep
from app.services.whatsapp.wa_templates import wa
from app.services.whatsapp.helpers import constants as WMSG


class CoreActions:
    """
    Core workflow steps (name, feedback, END, HTTP helpers) and shared session/flow_data utilities.

    Other packages (salon, store) subclass or call static helpers here to avoid duplicating
    ``flow_data`` and pending-reply patterns.
    """

    @staticmethod
    def _ctx(session: Dict[str, Any]) -> Dict[str, Any]:
        return session.setdefault("ctx", {})

    @staticmethod
    def _set_ctx(session: Dict[str, Any], **kwargs: Any) -> None:
        """Set top-level ctx keys and mirror the same keys into ctx.flow_data (legacy / FSM paths)."""
        ctx = CoreActions._ctx(session)
        for k, v in kwargs.items():
            if v is not None:
                ctx[k] = v
        CoreActions._flow_patch(session, **kwargs)

    @staticmethod
    def _flow_patch(session: Dict[str, Any], **kwargs: Any) -> None:
        ctx = session.setdefault("ctx", {})
        fd = ctx.setdefault("flow_data", {})
        for k, v in kwargs.items():
            if v is not None:
                fd[k] = v

    @staticmethod
    def _set_flow_fields(session: Dict[str, Any], **kwargs: Any) -> None:
        """Persist workflow/booking fields only under ctx.flow_data (no duplicate top-level ctx)."""
        CoreActions._flow_patch(session, **kwargs)

    @staticmethod
    def _session_booking_view(session: Dict[str, Any]) -> Dict[str, Any]:
        """Merged view: flow_data overrides top-level ctx (single source for booking reads)."""
        ctx = session.get("ctx") or {}
        flow = ctx.get("flow_data")
        if not isinstance(flow, dict):
            flow = {}
        return {**ctx, **flow}

    @staticmethod
    def _ctx_and_flow(session: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        ctx = session.setdefault("ctx", {})
        flow = ctx.setdefault("flow_data", {})
        if not isinstance(flow, dict):
            flow = {}
            ctx["flow_data"] = flow
        return ctx, flow

    @staticmethod
    def get_flow_data(session: Dict[str, Any]) -> Dict[str, Any]:
        """Return the accumulating flow payload (same dict mutates across steps)."""
        _, flow = CoreActions._ctx_and_flow(session)
        return flow

    @staticmethod
    def clear_flow_data(session: Dict[str, Any]) -> None:
        ctx = session.get("ctx") or {}
        ctx["flow_data"] = {}
        session["ctx"] = ctx

    @staticmethod
    def _is_ai_enabled(tenant: str) -> bool:
        from app.services.whatsapp.tier_services import get_tier_service

        return get_tier_service(tenant).should_use_ai_in_flow()

    @staticmethod
    def _get_today_settings(tenant: str) -> Tuple[dt.date, Dict[str, Any]]:
        settings = get_tenant_service().get_tenant_settings(tenant) or {}
        tz = get_tenant_timezone_zoneinfo(settings)
        today = dt.datetime.now(tz).date()
        return today, settings

    @staticmethod
    def _pick_from_list(user_input: str, items: List[Any]) -> Optional[Any]:
        """Return the list item at the user's 1-based numeric choice, or ``None``."""
        idx = choice_to_index(user_input)
        if idx and 1 <= idx <= len(items):
            return items[idx - 1]
        return None

    @staticmethod
    def _workflow_pending_persist_keys(step: WorkflowStep) -> Tuple[str, str]:
        """``(pending_key, persisted_key)`` for the current step's action code."""
        return workflow_user_reply_pending_key(step.action_code), workflow_user_reply_flow_key(step.action_code)

    @staticmethod
    def _flow_commit_user_reply(flow: Dict[str, Any], pend: str, persist: str, persisted_value: str) -> None:
        """Write the user's answer under ``persist`` and clear the pending key."""
        flow[persist] = persisted_value
        flow.pop(pend, None)

    @staticmethod
    def workflow_step_menu_params(step: WorkflowStep, session: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build menu/dispatcher-style ``params`` (``entities``, ``appointment_id``) from
        ``step.params`` and ``session.ctx.flow_data`` for cancel/reschedule and similar steps.
        """
        p = dict(step.params or {})
        entities: Dict[str, Any] = {}
        if isinstance(p.get("entities"), dict):
            entities.update(p["entities"])
        aid = p.pop("appointment_id", None)
        if aid is not None:
            entities.setdefault("appointment_id", aid)
        ctx = session.get("ctx") or {}
        flow = ctx.get("flow_data")
        if isinstance(flow, dict) and flow.get("appointment_id") and "appointment_id" not in entities:
            entities["appointment_id"] = flow["appointment_id"]
        if entities:
            p["entities"] = entities
        return p

    @staticmethod
    def _norm_workflow_code(action_code: str) -> str:
        c = (action_code or "").strip().lower()
        if c.startswith("core."):
            c = c[6:]
        return c

    @staticmethod
    def validate_customer_name(tenant: str, name: str) -> Tuple[bool, Optional[str]]:
        t = (name or "").strip()
        if not t or t.lower() == "skip":
            return True, None
        if len(t) < 2:
            return False, wa(tenant, "wa_core_name_short")
        if len(t) > 120:
            return False, wa(tenant, "wa_core_name_long")
        return True, None

    @staticmethod
    def validate_confirm_yes_no(tenant: str, user_input: str) -> Tuple[bool, Optional[str]]:
        low = (user_input or "").strip().lower()
        if low.startswith("1") or low in ("yes", "y", "confirm"):
            return True, None
        if low.startswith("2") or low in ("no", "n", "cancel"):
            return False, "cancelled"
        return False, wa(tenant, "wa_core_confirm_yes_no")

    @staticmethod
    async def _run_customer_name_step(
            tenant: str,
            phone: str,
            session: Dict[str, Any],
            step: WorkflowStep,
            *,
            default_prompt_wa_key: str,
    ) -> Optional[str]:
        ctx, flow = CoreActions._ctx_and_flow(session)
        if flow.get("customer_name") and not ctx.get("force_ask_name"):
            return None
        pend, persist = CoreActions._workflow_pending_persist_keys(step)
        raw = flow.get(pend)
        if raw is not None:
            input_text = str(raw).strip()
            if input_text.lower() == WMSG.BOOKING_NAME_INPUT_SKIP:
                flow["customer_name"] = WMSG.MSG_DEFAULT_CUSTOMER_NAME
            else:
                ok, err = CoreActions.validate_customer_name(tenant, input_text)
                if not ok:
                    return err
                flow["customer_name"] = input_text
            flow["customer_phone"] = phone
            flow["step_ask_name_done"] = True
            CoreActions._flow_commit_user_reply(flow, pend, persist, flow["customer_name"])
            return None
        return step.label or wa(tenant, default_prompt_wa_key)

    @staticmethod
    async def _run_ask_name(
            tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep
    ) -> Optional[str]:
        return await CoreActions._run_customer_name_step(
            tenant, phone, session, step, default_prompt_wa_key="wa_core_ask_name"
        )

    @staticmethod
    async def _run_collect_details(
            tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep
    ) -> Optional[str]:
        return await CoreActions._run_customer_name_step(
            tenant, phone, session, step, default_prompt_wa_key="wa_core_ask_details"
        )

    @staticmethod
    async def _run_booking_summary(
            tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep
    ) -> Optional[str]:
        _, flow = CoreActions._ctx_and_flow(session)
        pend, persist = CoreActions._workflow_pending_persist_keys(step)
        raw = flow.get(pend)
        if raw is not None:
            ok, detail = CoreActions.validate_confirm_yes_no(tenant, str(raw))
            raw_s = str(raw).strip()
            if detail == "cancelled":
                flow["booking_confirmed"] = False
                CoreActions._flow_commit_user_reply(flow, pend, persist, raw_s)
                return wa(tenant, "wa_core_cancelled")
            if not ok:
                return detail
            missing = []
            if not flow.get("customer_name"):
                missing.append("name")
            if not flow.get("customer_phone") and not phone:
                missing.append("phone")
            if missing:
                return wa(tenant, "wa_core_missing_fields", fields=", ".join(missing))
            flow["booking_confirmed"] = True
            flow["step_confirm_done"] = True
            CoreActions._flow_commit_user_reply(flow, pend, persist, raw_s)
            return None
        tn = tenant
        parts = []
        if flow.get("service_name") or flow.get("service_id"):
            parts.append(wa(tn, "wa_workflow_label_service", value=flow.get("service_name") or flow.get("service_id")))
        if flow.get("customer_name"):
            parts.append(wa(tn, "wa_workflow_label_name", value=flow["customer_name"]))
        if flow.get("date") or flow.get("appointment_date"):
            parts.append(wa(tn, "wa_workflow_label_date", value=flow.get("date") or flow.get("appointment_date")))
        if flow.get("time") or flow.get("appointment_time"):
            parts.append(wa(tn, "wa_workflow_label_time", value=flow.get("time") or flow.get("appointment_time")))
        if flow.get("professional"):
            parts.append(wa(tn, "wa_workflow_label_professional", value=flow["professional"]))
        summary = "\n".join(parts) if parts else wa(tn, "wa_core_no_details_yet")
        custom = (step.label or "").strip()
        intro = custom if custom else wa(tn, "wa_core_confirm_intro")
        return f"{intro}\n\n{summary}\n\n{wa(tn, 'wa_core_confirm_footer')}"

    @staticmethod
    async def _run_submit_feedback(
            tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep
    ) -> Optional[str]:
        ctx, flow = CoreActions._ctx_and_flow(session)
        pend, persist = CoreActions._workflow_pending_persist_keys(step)
        raw = flow.get(pend)
        if raw is not None:
            text = str(raw).strip()
            if not text:
                return wa(tenant, "wa_invalid_input_retry")
            persist_customer_feedback(tenant, phone or "", text)
            flow["feedback_submitted"] = True
            CoreActions._flow_commit_user_reply(flow, pend, persist, text)
            ctx["_wa_skip_input_wait_once"] = True
            return wa(tenant, "wa_core_feedback_thanks")
        custom = (step.label or "").strip()
        return custom or wa(tenant, "wa_core_feedback_prompt")

    @staticmethod
    async def _run_end(
            tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep
    ) -> Optional[str]:
        """
        END closes the workflow successfully. Shows step label only, or tenant template.
        Not the same as FINALIZE_BOOKING (that creates the appointment in salon flow).
        """
        custom = (step.label or "").strip()
        if custom:
            return custom
        return wa(tenant, "wa_workflow_end_success")

    @staticmethod
    async def run_open_ticket(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> Optional[str]:
        ticket_id = f"TCK-{int(dt.datetime.now(dt.timezone.utc).timestamp())}"
        return WMSG.MSG_TICKET_CREATED.format(ticket_id=ticket_id)

    @staticmethod
    async def run_open_url(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> Optional[str]:
        p = step.params or {}
        return str(p.get("url") or WMSG.MSG_CORE_API_EXAMPLE_URL)

    @staticmethod
    async def run_api_call(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> Optional[str]:
        p = step.params or {}
        url = p.get("url")
        method = str(p.get("method") or "GET").upper()
        if not url:
            return WMSG.MSG_API_CALL_CONFIG_MISSING
        try:
            import requests

            headers = p.get("headers") or {}
            body = p.get("body")
            if method == "POST":
                res = requests.post(url, json=body, headers=headers, timeout=5)
            else:
                res = requests.get(url, params=body, headers=headers, timeout=5)
            data = res.json() if "application/json" in res.headers.get("Content-Type", "") else res.text
            mapping = p.get("response_mapping")
            if mapping and isinstance(data, dict):
                return str(data.get(mapping, data))
            return str(data)[:200]
        except Exception as e:
            return WMSG.MSG_API_ERROR.format(err=str(e))

    # RUN ACTION LOGIC ENDS HERE

    @staticmethod
    async def try_run(
            action_code: str,
            tenant: str,
            phone: str,
            session: Dict[str, Any],
            step: WorkflowStep,
    ) -> Tuple[bool, Optional[str]]:
        """
        Dispatch ``action_code`` to a core handler map entry.

        Returns ``(False, None)`` when this package does not own the code.
        """
        code = CoreActions._norm_workflow_code(action_code)
        handler = _CORE_RUN_HANDLERS.get(code)
        if not handler:
            return False, None
        return True, await run_handler_and_await(
            handler, tenant=tenant, phone=phone, session=session, step=step
        )


_CORE_RUN_HANDLERS: Dict[str, Callable[..., Any]] = {
    ASK_NAME: CoreActions._run_ask_name,
    COLLECT_PATIENT_INFO_ALIAS: CoreActions._run_ask_name,
    COLLECT_DETAILS: CoreActions._run_collect_details,
    BOOKING_SUMMARY: CoreActions._run_booking_summary,
    SUBMIT_FEEDBACK: CoreActions._run_submit_feedback,
    OPEN_TICKET: CoreActions.run_open_ticket,
    OPEN_URL: CoreActions.run_open_url,
    API_CALL: CoreActions.run_api_call,
    END: CoreActions._run_end,
}


async def try_core_run(
        action_code: str,
        tenant: str,
        phone: str,
        session: Dict[str, Any],
        step: WorkflowStep,
) -> Tuple[bool, Optional[str]]:
    """Registered first in :func:`~app.services.whatsapp.action_executor.execute_run`."""
    return await CoreActions.try_run(action_code, tenant, phone, session, step)
