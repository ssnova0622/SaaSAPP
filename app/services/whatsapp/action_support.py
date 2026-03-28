"""
Shared utilities for WhatsApp workflow actions (logging, async dispatch).

Use this module from use case packages instead of duplicating inspect/await logic.
Keeps `usecases/*` loosely coupled to each other — they only depend on this thin layer + models.
"""
from __future__ import annotations

import inspect
import logging
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple, TypeVar, Union

from app.models.workflow import WorkflowStep

# ---------------------------------------------------------------------------
# Logging — single namespace for grep-friendly WhatsApp logs
# ---------------------------------------------------------------------------

_LOG_PREFIX = "app.services.whatsapp"


def get_action_logger(name: str) -> logging.Logger:
    """
    Return a logger for a WhatsApp subcomponent (e.g. ``executor``, ``workflow_engine``).

    Child loggers inherit the host app's logging config; filter on ``app.services.whatsapp``.
    """
    suffix = (name or "").strip().strip(".")
    return logging.getLogger(f"{_LOG_PREFIX}.{suffix}" if suffix else _LOG_PREFIX)


# ---------------------------------------------------------------------------
# Async/sync handler bridge (workflow step handlers may be sync or async)
# ---------------------------------------------------------------------------

T = TypeVar("T")


async def await_if_needed(value: Union[T, Awaitable[T]]) -> T:
    """
    If ``value`` is awaitable, await it; otherwise return it.

    Used by ``try_*_run`` helpers so one code path supports sync and ``async def`` handlers.
    """
    if inspect.isawaitable(value):
        return await value  # type: ignore[no-any-return]
    return value  # type: ignore[no-any-return]


async def run_handler_and_await(
        handler: Callable[..., Any],
        *,
        tenant: str,
        phone: str,
        session: Dict[str, Any],
        step: WorkflowStep,
) -> Any:
    """
    Call ``handler(tenant, phone, session, step)`` and await the return value when it is a coroutine.
    """
    return await await_if_needed(handler(tenant, phone, session, step))


# Async try_run: (action_code, tenant, phone, session, step) -> (handled, message)
TryRunFn = Callable[..., Any]


async def try_run_chain(
        action_code: str,
        tenant: str,
        phone: str,
        session: Dict[str, Any],
        step: WorkflowStep,
        *,
        runners: Tuple[TryRunFn, ...],
        logger: Optional[logging.Logger] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Try each ``runners`` entry in order; stop at the first ``(True, message)``.

    Raises
    ------
    Exception
        Re-raised after logging if a runner fails (fail-fast; workflow layer may catch).
    """
    for run_fn in runners:
        try:
            handled, msg = await run_fn(action_code, tenant, phone, session, step)
        except Exception:
            if logger:
                logger.exception(
                    "try_run failed tenant=%s action_code=%s runner=%s.%s",
                    tenant,
                    action_code,
                    getattr(run_fn, "__module__", "?"),
                    getattr(run_fn, "__name__", "?"),
                )
            raise
        if handled:
            if logger:
                logger.debug(
                    "workflow action handled tenant=%s action_code=%s handler=%s",
                    tenant,
                    action_code,
                    getattr(run_fn, "__name__", "?"),
                )
            return True, msg
    if logger:
        logger.debug("workflow action not handled tenant=%s action_code=%s", tenant, action_code)
    return False, None
