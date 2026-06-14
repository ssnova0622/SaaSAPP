"""
Central WhatsApp action handler registry.

Every domain module (core, salon, store, clinic, ai, …) registers its handlers
here at import time via :func:`register`.  This allows :mod:`action_executor`
to dispatch ``O(1)`` without a hardcoded runner chain, and lets the inbound
pipeline and workflow engine query action metadata without maintaining manual
frozensets in multiple files.

Usage (in a handler module, at module level after the class definitions)::

    from app.services.whatsapp.action_handler_registry import register
    from app.helpers.constants_action import SHOW_SERVICES, SELECT_DATE

    register(SHOW_SERVICES, SalonActions._run_show_services, needs_user_input=True)
    register(SELECT_DATE,   SalonActions._run_select_date,   needs_user_input=True)

Schema
------
``needs_user_input``
    True → the workflow engine stores the user's next reply in
    ``flow_data["{action}_user_input_pending"]`` and re-runs the step with
    that value (same semantics as ``WORKFLOW_RUN_ONLY_VIA_FLOW_DATA_INPUT``).

``keeps_session``
    True → after running this action from a menu node (not inside a workflow),
    do **not** reset the session cursor to the root menu.  Set this for any
    action that starts a stateful sub-conversation (FSM, multi-turn flow).
    Workflow actions (``workflow.*`` prefix) always keep session regardless of
    this flag.

Import-safety
-------------
This module imports only from :mod:`workflow_step_policy` (string helpers),
so it can be imported by any whatsapp sub-module without circular dependency.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, NamedTuple, Optional, Set

from app.services.whatsapp.workflow.workflow_step_policy import normalize_workflow_action_code


class _Entry(NamedTuple):
    handler: Callable
    needs_user_input: bool
    keeps_session: bool


# code (normalized) → entry
_REGISTRY: Dict[str, _Entry] = {}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register(
    code: str,
    handler: Callable,
    *,
    needs_user_input: bool = False,
    keeps_session: bool = False,
) -> None:
    """Register *handler* for *code* (and every normalised alias).

    Calling ``register`` twice for the same normalised code overwrites the
    previous entry — the last writer wins (useful in tests).
    """
    norm = normalize_workflow_action_code(code)
    _REGISTRY[norm] = _Entry(
        handler=handler,
        needs_user_input=needs_user_input,
        keeps_session=keeps_session,
    )


def register_many(
    entries: Dict[str, Callable],
    *,
    needs_input_codes: Set[str] | frozenset = frozenset(),
    keeps_session_codes: Set[str] | frozenset = frozenset(),
) -> None:
    """Bulk-register a dict of ``{code: handler}`` with optional metadata sets."""
    ni_norm = {normalize_workflow_action_code(c) for c in needs_input_codes}
    ks_norm = {normalize_workflow_action_code(c) for c in keeps_session_codes}
    for code, handler in entries.items():
        norm = normalize_workflow_action_code(code)
        register(
            code,
            handler,
            needs_user_input=(norm in ni_norm),
            keeps_session=(norm in ks_norm),
        )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def get_entry(action_code: str) -> Optional[_Entry]:
    """Return the registry entry for *action_code*, or ``None``."""
    return _REGISTRY.get(normalize_workflow_action_code(action_code))


def action_needs_user_input(action_code: str) -> bool:
    """True if this action step expects a user reply stored via flow_data."""
    entry = get_entry(action_code)
    return entry.needs_user_input if entry else False


def action_keeps_session(action_code: str) -> bool:
    """True if the action is session-stateful (do not reset to root menu after it runs).

    Workflow actions (``workflow.*`` prefix) are always session-stateful regardless of
    their registry entry.
    """
    if str(action_code or "").strip().lower().startswith("workflow."):
        return True
    entry = get_entry(action_code)
    return entry.keeps_session if entry else False


def registered_need_input_codes() -> frozenset:
    """Frozenset of all normalised codes that have ``needs_user_input=True``."""
    return frozenset(code for code, e in _REGISTRY.items() if e.needs_user_input)


def is_registered(action_code: str) -> bool:
    """True if *action_code* has a handler in the registry."""
    return normalize_workflow_action_code(action_code) in _REGISTRY
