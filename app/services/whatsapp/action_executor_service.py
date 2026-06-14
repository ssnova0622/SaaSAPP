"""
Execute WhatsApp menu / trigger actions (dispatcher entry from routes or NL).

- ``workflow.<id>`` → :class:`~app.services.whatsapp.workflow.workflow_engine.WorkflowEngine`
- Booking starters (``book_appointment``, ``select_timeslot``, …) → default tenant booking
  workflow when one exists; legacy FSM only as fallback
- Other registered step codes → :func:`~app.services.whatsapp.action_executor.execute_run`
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Set

from app.core.container import get_tenant_service
from app.helpers.constants_action import BOOK_APPOINTMENT, BOOK_DOCTOR, SELECT_TIMESLOT
from app.helpers.phone_util import PhoneUtil
from app.models.workflow import WorkflowStep
from app.services.whatsapp.action_executor import execute_run
from app.services.whatsapp.action_handler_registry import is_registered
from app.services.whatsapp.action_support import get_action_logger
from app.services.whatsapp.session_flow_service import get_session, save_session
from app.services.whatsapp.usecases.salon.booking_ctx_utils import new_workflow_session
from app.services.whatsapp.workflow.workflow_engine import WorkflowEngine
from app.services.whatsapp.workflow.workflow_resolver import resolve_default_booking_workflow
from app.services.whatsapp.wa_templates import wa
from app.services.whatsapp.workflow_message_helper import workflow_reply_or_welcome
from app.services.whatsapp.helpers import constants as WMSG

logger = get_action_logger("action_executor_service")

# Menu / NL aliases that start the legacy booking FSM (service → date → staff → slot).
_FSM_STARTER_IDS: Set[str] = {
    BOOK_APPOINTMENT.lower(),
    SELECT_TIMESLOT.lower(),
    BOOK_DOCTOR.lower(),
    "salon.book_appointment",
    "salon.select_timeslot",
    "clinic.book_doctor",
}


def _normalize_action_id(action_id: str) -> str:
    aid = (action_id or "").strip().lower()
    for prefix in ("salon.", "clinic."):
        if aid.startswith(prefix):
            return aid[len(prefix):]
    return aid


def _entities_from_params(params: Dict[str, Any]) -> Dict[str, Any]:
    entities = dict(params.get("entities") or {})
    for key in (
            "service",
            "professional_name",
            "date",
            "date_marker",
            "appointment_id",
    ):
        if params.get(key) is not None and key not in entities:
            entities[key] = params[key]
    return entities


async def _start_booking_fsm(
        tenant: str,
        phone: str,
        params: Optional[Dict[str, Any]],
) -> str:
    from app.services.whatsapp.usecases.salon.booking_flow import start_timeslot_flow

    session = get_session(tenant, phone)
    session["ctx"] = {}
    save_session(tenant, phone, session)
    entities = _entities_from_params(params or {})
    return await start_timeslot_flow(tenant, phone, entities=entities or None)


async def _run_registered_action(
        tenant: str,
        phone: str,
        action_id: str,
        params: Optional[Dict[str, Any]],
) -> str:
    session = get_session(tenant, phone)
    ctx = session.setdefault("ctx", {})
    if not ctx.get("workflow_id"):
        ctx.setdefault("flow_data", {})
    step = WorkflowStep(
        action_code=action_id,
        label=(params or {}).get("label"),
        params={k: v for k, v in (params or {}).items() if k not in ("phone", "input", "label")},
    )
    try:
        result = await execute_run(action_id, tenant, phone, session, step)
    except Exception:
        logger.exception(
            "execute_run failed tenant=%s action_id=%s phone=%s",
            tenant,
            action_id,
            phone,
        )
        return wa(tenant, "wa_workflow_step_error")
    save_session(tenant, phone, session)
    text = (result or "").strip() if isinstance(result, str) else ""
    return text or wa(tenant, "whatsapp_done")


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
        Lowercase action id (e.g. ``workflow.my_flow``, ``book_appointment``).
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
        workflow_id = aid.replace("workflow.", "", 1)
        session = get_session(tenant, phone)
        session["ctx"] = new_workflow_session(workflow_id)
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

    norm = _normalize_action_id(aid)
    if norm in _FSM_STARTER_IDS or aid in _FSM_STARTER_IDS:
        wf_id = resolve_default_booking_workflow(tenant)
        if wf_id:
            logger.debug("book_appointment → workflow.%s tenant=%s", wf_id, tenant)
            return await run_action(tenant, f"workflow.{wf_id}", params)
        return await _start_booking_fsm(tenant, phone, params)

    if is_registered(norm) or is_registered(aid):
        return await _run_registered_action(tenant, phone, norm if is_registered(norm) else aid, params)

    logger.warning("run_action: unhandled action_id=%s tenant=%s", aid, tenant)
    return WMSG.MSG_ACTION_EXECUTOR_NONE
