"""
Dispatch a single workflow step to the handler registered for ``action_code``.

Dispatch order
--------------
1. **Central registry** – O(1) dict lookup; any module that calls
   :func:`~app.services.whatsapp.action_handler_registry.register` at import
   time is found here without modifying this file.  Modules register
   themselves the first time they are imported (lazy, via the fallback chain
   below).

2. **Legacy fallback chain** (core → clinic → salon → store → ai) – runs the
   same ``try_*_run`` functions that existed before the registry.  This keeps
   100 % backward-compatibility: handlers that have not yet called
   ``register()`` still work.

Adding a new integration
------------------------
1. Implement an async handler ``my_handler(tenant, phone, session, step) → str | None``.
2. In your module add at the bottom::

       from app.services.whatsapp.action_handler_registry import register
       register("my_action_code", my_handler, needs_user_input=False)

   That is all — no edits to this file are required.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.models.workflow import WorkflowStep
from app.services.whatsapp.action_support import get_action_logger, run_handler_and_await, try_run_chain

_LOG = get_action_logger("action_executor")


async def execute_run(
        action_code: str,
        tenant: str,
        phone: str,
        session: Dict[str, Any],
        step: WorkflowStep,
) -> Optional[str]:
    """
    Run one workflow step: find a handler for ``action_code`` and return its
    user-facing string (or ``None`` if no handler matched).

    Parameters
    ----------
    action_code
        Raw step code from workflow JSON (may include ``module.`` prefix).
    tenant, phone
        Tenant id and normalised customer phone.
    session
        Mutable session dict (``ctx``, ``flow_data``, etc.).
    step
        Current :class:`~app.models.workflow.WorkflowStep` instance.
    """
    # 1. Registry path — fast, O(1), no hardcoded ordering.
    #    Modules register themselves when they are first imported (triggered by
    #    the fallback chain below or by any other import in the request path).
    try:
        from app.services.whatsapp.action_handler_registry import get_entry
        entry = get_entry(action_code)
        if entry is not None:
            _LOG.debug("registry dispatch action_code=%s tenant=%s", action_code, tenant)
            return await run_handler_and_await(
                entry.handler,
                tenant=tenant,
                phone=phone,
                session=session,
                step=step,
            )
    except Exception as exc:  # pragma: no cover – should never fail
        _LOG.warning("Registry lookup failed for %s: %s", action_code, exc)

    # 2. Legacy fallback chain – imports also trigger self-registration so
    #    subsequent calls hit the registry path above.
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
