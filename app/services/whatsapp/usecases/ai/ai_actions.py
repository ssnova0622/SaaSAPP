"""
AI-related WhatsApp workflow steps (free-text capture + optional intent hint).

Uses the same ``flow_data`` pending/persist pattern as :class:`~app.services.whatsapp.usecases.core.core_actions.CoreActions`.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from app.helpers.constants_action import AI_FREE_TEXT
from app.models.workflow import WorkflowStep
from app.services.whatsapp.usecases.core.core_actions import CoreActions
from app.services.whatsapp.wa_templates import wa
from app.services.whatsapp.workflow.workflow_step_policy import normalize_workflow_action_code

try:
    from app.services.ai import AIPredictor  # type: ignore
except Exception:
    AIPredictor = None  # type: ignore


class AIActions(CoreActions):
    """Extends :class:`CoreActions` only for shared ``flow_data`` helpers."""

    @staticmethod
    async def _run_ai_free_text(
            tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep
    ) -> Optional[str]:
        _, flow = CoreActions._ctx_and_flow(session)
        pend, persist = CoreActions._workflow_pending_persist_keys(step)
        raw = flow.get(pend)
        if raw is not None:
            text = str(raw).strip()
            if not text:
                return wa(tenant, "wa_invalid_input_retry")
            CoreActions._flow_commit_user_reply(flow, pend, persist, text)
            if AIPredictor and CoreActions._is_ai_enabled(tenant):
                try:
                    pred = AIPredictor()
                    intent, _score = pred.detect_intent(text, tenant=tenant)
                    if intent:
                        return (
                            f"[{intent}] Thanks — we received your message. "
                            "Our team can assist further if you need more detail."
                        )
                except Exception:
                    pass
            return f"Thanks — noted:\n{text[:800]}"
        return (step.label or "").strip() or "Send your question or message in one reply."

    @staticmethod
    async def try_run(
            action_code: str,
            tenant: str,
            phone: str,
            session: Dict[str, Any],
            step: WorkflowStep,
    ) -> Tuple[bool, Optional[str]]:
        """Return ``(True, text)`` only for ``ai_free_text``; otherwise ``(False, None)``."""
        code = normalize_workflow_action_code(action_code)
        if code == AI_FREE_TEXT:
            return True, await AIActions._run_ai_free_text(tenant, phone, session, step)
        return False, None

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


async def try_ai_run(
        action_code: str,
        tenant: str,
        phone: str,
        session: Dict[str, Any],
        step: WorkflowStep,
) -> Tuple[bool, Optional[str]]:
    """Module entrypoint registered in :mod:`app.services.whatsapp.action_executor`."""
    return await AIActions.try_run(action_code, tenant, phone, session, step)


def try_ai_input(
        action_code: str,
        tenant: str,
        phone: str,
        session: Dict[str, Any],
        step: WorkflowStep,
        user_input: str,
) -> Tuple[bool, bool, Optional[str]]:
    return AIActions.try_input(action_code, tenant, phone, session, step, user_input)
