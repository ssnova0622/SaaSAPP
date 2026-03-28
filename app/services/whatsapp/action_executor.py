"""
Dispatch a single workflow step to the first use-case module that handles ``action_code``.

**Order (first match wins):** core → clinic → salon → store → ai.

To add a new integration, implement ``try_*_run`` in a module and append it to
``RUNNERS`` below. See ``ADDING_WORKFLOW_ACTIONS.md`` in this package.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.models.workflow import WorkflowStep
from app.services.whatsapp.action_support import get_action_logger, try_run_chain

_LOG = get_action_logger("action_executor")


async def execute_run(
        action_code: str,
        tenant: str,
        phone: str,
        session: Dict[str, Any],
        step: WorkflowStep,
) -> Optional[str]:
    """
    Run one workflow step: find a handler for ``action_code`` and return its user-facing string (or ``None``).

    Parameters
    ----------
    action_code
        Raw step code from workflow JSON (may include ``module.`` prefix).
    tenant, phone
        Tenant id and normalized customer phone.
    session
        Mutable session dict (``ctx``, ``flow_data``, etc.).
    step
        Current :class:`~app.models.workflow.WorkflowStep` instance.
    """
    # Lazy imports keep startup light and avoid cycles.
    from app.services.whatsapp.usecases.ai import ai_actions
    from app.services.whatsapp.usecases.clinic import clinic_actions
    from app.services.whatsapp.usecases.core import core_actions
    from app.services.whatsapp.usecases.salon import salon_actions
    from app.services.whatsapp.usecases.store import store_actions

    runners = (
        core_actions.try_core_run,
        clinic_actions.try_clinic_run,
        salon_actions.try_salon_run,
        store_actions.try_store_run,
        ai_actions.try_ai_run,
    )
    handled, msg = await try_run_chain(
        action_code,
        tenant,
        phone,
        session,
        step,
        runners=runners,
        logger=_LOG,
    )
    return msg if handled else None
