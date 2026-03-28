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
