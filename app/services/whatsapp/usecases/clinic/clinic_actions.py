"""
Clinic WhatsApp workflow steps.

Doctor listing uses the same implementation as salon “show professionals” to avoid duplicate UX logic.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from app.helpers.constants_action import CHECK_DOCTOR, LIST_DOCTORS
from app.models.workflow import WorkflowStep
from app.services.whatsapp.usecases.salon.salon_actions import SalonActions


def _norm_code(action_code: str) -> str:
    c = (action_code or "").strip().lower()
    if c.startswith("clinic."):
        c = c[7:]
    return c


async def try_clinic_run(
    action_code: str,
    tenant: str,
    phone: str,
    session: Dict[str, Any],
    step: WorkflowStep,
) -> Tuple[bool, Optional[str]]:
    """
    Handle ``list_doctors`` / ``check_doctor``; otherwise return ``(False, None)``.

    Parameters follow the shared workflow contract (see ``ADDING_WORKFLOW_ACTIONS.md``).
    Registered in :mod:`app.services.whatsapp.action_executor`.
    """
    code = _norm_code(action_code)
    if code not in (LIST_DOCTORS, CHECK_DOCTOR):
        return False, None
    return True, await SalonActions.run_show_professionals(tenant, phone, session, step)


def try_clinic_input(
    action_code: str,
    tenant: str,
    phone: str,
    session: Dict[str, Any],
    step: WorkflowStep,
    user_input: str,
) -> Tuple[bool, bool, Optional[str]]:
    """Unused for workflows (run-only path). Kept for a stable executor API shape."""
    return False, True, None


def _register_clinic_handlers() -> None:
    from app.services.whatsapp.action_handler_registry import register
    from app.services.whatsapp.workflow.workflow_step_policy import WORKFLOW_RUN_ONLY_VIA_FLOW_DATA_INPUT
    from app.services.whatsapp.workflow.workflow_step_policy import normalize_workflow_action_code

    async def _list_doctors_handler(tenant, phone, session, step):
        return (await try_clinic_run(LIST_DOCTORS, tenant, phone, session, step))[1]

    async def _check_doctor_handler(tenant, phone, session, step):
        return (await try_clinic_run(CHECK_DOCTOR, tenant, phone, session, step))[1]

    ni_norm = {normalize_workflow_action_code(c) for c in WORKFLOW_RUN_ONLY_VIA_FLOW_DATA_INPUT}
    register(LIST_DOCTORS, _list_doctors_handler, needs_user_input=(LIST_DOCTORS in ni_norm), keeps_session=True)
    register(CHECK_DOCTOR, _check_doctor_handler, needs_user_input=(CHECK_DOCTOR in ni_norm), keeps_session=True)


_register_clinic_handlers()
