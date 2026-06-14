"""
Multi-step WhatsApp workflows: load tenant JSON definitions, advance ``step_idx``, manage ``waiting_for_input``.

Execution of each step is delegated to :func:`~app.services.whatsapp.action_executor.execute_run`
(loose coupling — engine does not import salon/store/core handlers directly).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from app.core.container import get_tenant_service
from app.helpers.constants_action import END
from app.models.workflows import WorkflowActionMeta, WorkflowDefinition, WorkflowStep
from app.services.whatsapp.action_executor import execute_run
from app.services.whatsapp.action_support import get_action_logger
from app.services.whatsapp.usecases.action_registry import get_all_workflow_actions, capability_satisfied
from app.services.whatsapp.wa_templates import wa
from app.services.whatsapp.workflow.workflow_step_policy import (
    WORKFLOW_RUN_ONLY_VIA_FLOW_DATA_INPUT,  # kept for tests / direct access
    action_needs_user_input,
    can_merge_trailing_end_without_wait,
    normalize_workflow_action_code,
    workflow_user_reply_pending_key,
)
from app.services.whatsapp.workflow.workflow_service import (
    delete_workflow as _delete_workflow,
    get_workflow as _get_workflow,
    list_workflows as _list_workflows,
    upsert_workflow as _upsert_workflow,
)

_LOG = get_action_logger("workflow_engine")


def _remaining_steps_are_all_end(steps: Sequence[WorkflowStep], start_idx: int) -> bool:
    """True if every step from ``start_idx`` through the last is an END action (case/prefix normalized)."""
    n = len(steps)
    if start_idx >= n:
        return False
    for i in range(start_idx, n):
        code = normalize_workflow_action_code(getattr(steps[i], "action_code", None) or "")
        if code != END:
            return False
    return True


class WorkflowEngine:
    """
    Run saved workflows for a WhatsApp session.

    Session shape (under ``session["ctx"]``)::

        workflow_id, step_idx, waiting_for_input, flow_data (dict)
    """

    get_workflow = staticmethod(_get_workflow)
    list_workflows = staticmethod(_list_workflows)
    upsert_workflow = staticmethod(_upsert_workflow)
    delete_workflow = staticmethod(_delete_workflow)

    @staticmethod
    def get_available_actions() -> List[WorkflowActionMeta]:
        """Full workflow step catalog (no tenant filter)."""
        return get_all_workflow_actions()

    @classmethod
    def list_whatsapp_menu_items(cls, tenant: str) -> List[Dict[str, Any]]:
        """Dispatcher actions + saved workflows for menu builder / inbound exact match."""
        from app.services.whatsapp.usecases.action_registry import list_dispatcher_actions_for_tenant

        items = list_dispatcher_actions_for_tenant(tenant)
        caps = {
            str(c).lower()
            for c in (get_tenant_service().get_tenant_settings(tenant) or {}).get("capabilities") or []
        }
        for wf in cls.list_workflows(tenant) or []:
            req = [str(x).lower() for x in (getattr(wf, "requires_caps", None) or [])]
            if req and not all(capability_satisfied(caps, r) for r in req):
                continue
            items.append(
                {
                    "id": f"workflow.{wf.workflow_id}",
                    "label": wa(tenant, "wa_workflow_menu_item_label", name=wf.name),
                    "module": "workflow",
                    "requires_caps": list(getattr(wf, "requires_caps", None) or []),
                }
            )
        return items

    @classmethod
    def get_workflow_for_action(cls, tenant: str, action_id: str) -> Optional[WorkflowDefinition]:
        """Return first workflow that has a step with this action_id, or first workflow."""
        aid = (action_id or "").strip().lower()
        all_workflows = cls.list_workflows(tenant)
        if not all_workflows:
            return None
        for wf in all_workflows:
            for step in (wf.steps or []):
                step_code = (getattr(step, "action_code", None) or "").strip().lower()
                if step_code == aid or step_code.replace("action:", "") == aid:
                    return wf
        return all_workflows[0]

    @classmethod
    def _ensure_ctx_dict(cls, session: Dict[str, Any]) -> Dict[str, Any]:
        """Guarantee ``session["ctx"]`` is a mutable dict (normalizes ``None`` / missing)."""
        ctx = session.get("ctx")
        if not isinstance(ctx, dict):
            ctx = {}
            session["ctx"] = ctx
        return ctx

    @classmethod
    async def _merge_trailing_end_steps_into_reply(
            cls,
            tenant: str,
            phone: str,
            session: Dict[str, Any],
            steps: Sequence[WorkflowStep],
            prior_reply: str,
    ) -> str:
        """
        If every step from the current index onward is END, execute those END steps in the same
        turn and concatenate their user-visible text after ``prior_reply`` (one WhatsApp bubble).
        Otherwise return ``prior_reply`` unchanged and leave the cursor on the next non-END step.
        """
        ctx = cls._ensure_ctx_dict(session)
        idx = int(ctx.get("step_idx", 0))
        if idx >= len(steps):
            return prior_reply
        tail = steps[idx:]
        for st in tail:
            if normalize_workflow_action_code(getattr(st, "action_code", None) or "") != END:
                return prior_reply
        combined = prior_reply
        for st in tail:
            try:
                end_raw = await execute_run(st.action_code, tenant, phone, session, st)
            except Exception:
                _LOG.exception(
                    "execute_run failed while merging END steps tenant=%s phone=%s action_code=%s",
                    tenant,
                    phone,
                    getattr(st, "action_code", None),
                )
                end_raw = None
            end_msg = (end_raw or "").strip() if isinstance(end_raw, str) else ""
            if not end_msg:
                end_msg = wa(tenant, "wa_workflow_end_success")
            combined = f"{combined.rstrip()}\n\n{end_msg}" if (combined or "").strip() else end_msg
        ctx.pop("workflow_id", None)
        ctx.pop("step_idx", None)
        ctx.pop("waiting_for_input", None)
        ctx["flow_ended"] = True
        session["ctx"] = ctx
        return combined

    @classmethod
    async def _complete_turn_with_trailing_steps(
            cls,
            tenant: str,
            phone: str,
            session: Dict[str, Any],
            *,
            head: str = "",
    ) -> str:
        """
        After a commit step (confirm, track order, …), run following steps in the same turn
        until the workflow ends or must wait for user input. Ensures END closing text is sent.
        """
        parts = [head.strip()] if (head or "").strip() else []
        for _ in range(32):
            ctx = cls._ensure_ctx_dict(session)
            if not ctx.get("workflow_id"):
                break
            if ctx.get("waiting_for_input"):
                break
            chunk = await cls.execute_next_step(tenant, phone, session)
            if (chunk or "").strip():
                parts.append(chunk.strip())
            ctx = cls._ensure_ctx_dict(session)
            if not ctx.get("workflow_id") or ctx.get("waiting_for_input"):
                break
        return "\n\n".join(parts) if parts else wa(tenant, "wa_workflow_end_success")

    @classmethod
    async def _append_remaining_workflow_steps(
            cls,
            tenant: str,
            phone: str,
            session: Dict[str, Any],
            steps: Sequence[WorkflowStep],
            head_reply: str,
    ) -> str:
        """Merge trailing END steps when possible; otherwise auto-run until END or wait."""
        ctx = cls._ensure_ctx_dict(session)
        idx = int(ctx.get("step_idx", 0))
        if _remaining_steps_are_all_end(steps, idx):
            return await cls._merge_trailing_end_steps_into_reply(
                tenant, phone, session, steps, head_reply,
            )
        return await cls._complete_turn_with_trailing_steps(
            tenant, phone, session, head=head_reply,
        )

    @classmethod
    async def execute_next_step(
            cls,
            tenant: str,
            phone: str,
            session: Dict[str, Any],
            user_input: Optional[str] = None,
    ) -> str:
        """
        Advance the workflow by at most one logical step and return text for the user.

        When ``ctx["waiting_for_input"]`` and the user sent a message, run-only steps stash
        the text in ``flow_data`` (see ``workflow_step_policy``) and re-run the same step.

        If a step would wait for input but **every remaining step** is ``END``, the engine runs
        those ``END`` steps immediately and appends their text (e.g. custom closing message) to
        this turn's reply so the user is not prompted for a throwaway message.
        """
        ctx = cls._ensure_ctx_dict(session)
        workflow_id = ctx.get("workflow_id")
        if not workflow_id:
            return wa(tenant, "wa_no_active_workflow")

        workflow = cls.get_workflow(tenant, workflow_id)
        if not workflow:
            return wa(tenant, "wa_flow_not_available")

        steps = workflow.steps or []
        current_step_idx = ctx.get("step_idx", 0)

        if current_step_idx >= len(steps):
            ctx.pop("workflow_id", None)
            ctx.pop("step_idx", None)
            ctx.pop("waiting_for_input", None)
            ctx["flow_ended"] = True
            session["ctx"] = ctx
            return wa(tenant, "wa_workflow_complete_menu")

        step = steps[current_step_idx]
        action_code = getattr(step, "action_code", None) or ""

        # Handle user input for current step (only when explicitly waiting for a reply)
        if ctx.get("waiting_for_input") and user_input is not None and str(user_input).strip():
            code_norm = normalize_workflow_action_code(action_code)
            if action_needs_user_input(code_norm):
                flow = ctx.setdefault("flow_data", {})
                if not isinstance(flow, dict):
                    flow = {}
                    ctx["flow_data"] = flow
                flow[workflow_user_reply_pending_key(action_code)] = (user_input or "").strip()
                ctx["waiting_for_input"] = False
                session["ctx"] = ctx
                return await cls.execute_next_step(tenant, phone, session)

        # Execute current step
        try:
            result = await execute_run(action_code, tenant, phone, session, step)
        except Exception:
            _LOG.exception(
                "execute_run failed tenant=%s phone=%s workflow_id=%s step_idx=%s action_code=%s",
                tenant,
                phone,
                workflow_id,
                current_step_idx,
                action_code,
            )
            return wa(tenant, "wa_workflow_step_error")

        if normalize_workflow_action_code(action_code) == END:
            # END = successful workflow completion (display only). Not FINALIZE_BOOKING.
            # Normalize so ``core.end``, ``END``, etc. still run this branch and show ``step.label``.
            ctx.pop("workflow_id", None)
            ctx.pop("step_idx", None)
            ctx.pop("waiting_for_input", None)
            ctx["flow_ended"] = True
            session["ctx"] = ctx
            msg = (result or "").strip() if isinstance(result, str) else ""
            return msg or wa(tenant, "wa_workflow_end_success")

        # Commit step signalled auto-advance (confirm yes, store one-shot, …).
        if ctx.pop("_wa_skip_input_wait_once", None):
            if ctx.get("workflow_id"):
                ctx["step_idx"] = current_step_idx + 1
            ctx["waiting_for_input"] = False
            session["ctx"] = ctx
            head = (result or "").strip() if isinstance(result, str) else ""
            return await cls._append_remaining_workflow_steps(
                tenant, phone, session, steps, head,
            )

        input_required = bool(getattr(step, "input_required", False))
        code_norm_eff = normalize_workflow_action_code(action_code)
        # Core/salon run+flow_data steps usually omit input_required in JSON; still must wait for reply.
        # action_needs_user_input checks both the legacy frozenset and the registry, so new actions
        # registered with needs_user_input=True are picked up automatically.
        needs_user_reply = input_required or (
                action_needs_user_input(code_norm_eff) and bool(result)
        )
        if needs_user_reply and result:
            # e.g. SHOW_SERVICES → END only: show list and closing text in one message (no dummy reply).
            if (
                    _remaining_steps_are_all_end(steps, current_step_idx + 1)
                    and can_merge_trailing_end_without_wait(code_norm_eff)
            ):
                if ctx.get("workflow_id"):
                    ctx["step_idx"] = current_step_idx + 1
                    ctx["waiting_for_input"] = False
                session["ctx"] = ctx
                return await cls._merge_trailing_end_steps_into_reply(
                    tenant, phone, session, steps, result,
                )
            ctx["waiting_for_input"] = True
            session["ctx"] = ctx
            return result

        if result:
            if ctx.get("workflow_id"):
                ctx["step_idx"] = current_step_idx + 1
                ctx["waiting_for_input"] = False
            session["ctx"] = ctx
            return await cls._append_remaining_workflow_steps(
                tenant, phone, session, steps, result,
            )

        if ctx.get("workflow_id"):
            ctx["step_idx"] = current_step_idx + 1
        session["ctx"] = ctx
        return await cls.execute_next_step(tenant, phone, session)

    @classmethod
    async def _run_step_logic(
            cls,
            tenant: str,
            phone: str,
            session: Dict[str, Any],
            step_like: Any,
    ) -> str:
        """
        Ad-hoc single step (menu/dispatcher) without a full ``WorkflowStep`` from DB.

        Builds a minimal :class:`~app.models.workflow.WorkflowStep` from ``step_like.action_code``.
        """
        from app.models.workflow import WorkflowStep
        action_code = getattr(step_like, "action_code", None) or ""
        step = WorkflowStep(action_code=action_code, label=None, input_required=False, output_key=None, ui_type="list",
                            params={})
        result = await execute_run(action_code, tenant, phone, session, step)
        out = result if isinstance(result, str) else (result.get("reply") if isinstance(result, dict) else "") or ""
        return out or wa(tenant, "whatsapp_done")
