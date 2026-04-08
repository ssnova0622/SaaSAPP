"""
Execute WhatsApp menu / trigger actions (dispatcher entry from routes or NL).

Workflow start: ``action_id`` like ``workflow.<workflow_id>`` loads session and calls
:class:`~app.services.whatsapp.workflow.workflow_engine.WorkflowEngine`.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.container import get_tenant_service
from app.helpers.phone_util import PhoneUtil
from app.services.whatsapp.action_support import get_action_logger
from app.services.whatsapp.session_flow_service import get_session, save_session
from app.services.whatsapp.workflow.workflow_engine import WorkflowEngine
from app.services.whatsapp.wa_templates import wa
from app.services.whatsapp.workflow_message_helper import workflow_reply_or_welcome
from app.services.whatsapp.helpers import constants as WMSG

logger = get_action_logger("action_executor_service")


async def run_action(
        tenant: str,
        action_id: str,
        params: Optional[Dict[str, Any]],
) -> str:
    """
    Run one dispatcher action and return user-visible text.

    Parameters
    ----------
    tenant
        Tenant id.
    action_id
        Lowercase action id (e.g. ``workflow.my_flow``).
    params
        Must include ``phone`` when starting a workflow; other keys are action-specific.
    """
    aid = str(action_id or "").strip().lower()
    params = params or {}
    raw_phone = params.get("phone") or ""
    cc = get_tenant_service()._get_tenant_country_code(tenant)
    phone = PhoneUtil.normalize_e164_input(raw_phone, cc)
    if not phone and raw_phone:
        phone = str(raw_phone).replace("whatsapp:", "").strip()

    logger.debug("run_action aid=%s phone=%s", aid, phone)

    if aid.startswith("workflow."):
        workflow_id = aid.replace("workflow.", "")
        session = get_session(tenant, phone)
        session["ctx"] = {"workflow_id": workflow_id, "step_idx": 0, "waiting_for_input": False}
        save_session(tenant, phone, session)
        try:
            reply = await WorkflowEngine.execute_next_step(tenant, phone, session)
        except Exception:
            logger.exception(
                "WorkflowEngine.execute_next_step failed tenant=%s workflow_id=%s phone=%s",
                tenant,
                workflow_id,
                phone,
            )
            return wa(tenant, "wa_workflow_step_error")
        save_session(tenant, phone, session)
        return workflow_reply_or_welcome(tenant, reply)

    return WMSG.MSG_ACTION_EXECUTOR_NONE
