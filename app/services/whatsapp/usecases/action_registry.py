"""
Single catalog for WhatsApp: menu builder and Workflow Manager share `_DISPATCHER_ACTIONS`.

When adding a step type:
1. Add a constant in `app.helpers.constants_action`.
2. Append a `DispatcherActionDef` here.
3. Implement `try_*_run` and register it in `action_executor.execute_run` (see `ADDING_WORKFLOW_ACTIONS.md`).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from app.core.container import get_tenant_service
from app.helpers.constants_action import (OPEN_TICKET, SUBMIT_FEEDBACK, OPEN_URL,
                                          BROWSE_CATALOG, CHECK_PRICE, CHECK_PRODUCT, TRACK_ORDER, VIEW_OFFERS,
                                          VIEW_PRODUCTS,
                                          BOOK_APPOINTMENT,
                                          CANCEL_APPOINTMENT, SHOW_SERVICES, SHOW_SERVICE_PRICES, SHOW_PROFESSIONALS, LIST_DOCTORS,
                                          CHECK_DOCTOR, SELECT_TIME, SELECT_DATE,
                                          ASK_NAME, RESCHEDULE_APPOINTMENT, CONFIRM_PROMPT, FINALIZE_BOOKING,
                                          AI_FREE_TEXT)
from app.helpers.constants_capabilities import (
    CAP_SALON_APPOINTMENTS,
    CAP_STORE_CATALOG,
    CAP_STORE_ORDERS,
)
from app.helpers.constants_modules import AI_MODULE, CORE_MODULE, CLINIC_MODULE, SALON_MODULE, STORE_MODULE
from app.models.workflows import WorkflowActionMeta


@dataclass(frozen=True)
class DispatcherActionDef:
    id: str
    label: str
    modules: tuple[str, ...]
    requires_caps: tuple[str, ...] = ()


_DISPATCHER_ACTIONS: tuple[DispatcherActionDef, ...] = (
    DispatcherActionDef(AI_FREE_TEXT, "AI free-text (capture reply)", (AI_MODULE,), ()),

    DispatcherActionDef(OPEN_TICKET, "Open support ticket", (CORE_MODULE,), ()),
    DispatcherActionDef(SUBMIT_FEEDBACK, "Submit feedback", (CORE_MODULE, SALON_MODULE, CLINIC_MODULE, STORE_MODULE),
                        ()),
    DispatcherActionDef(OPEN_URL, "Open URL", (CORE_MODULE,), ()),

    DispatcherActionDef(BOOK_APPOINTMENT, "Book appointment", (SALON_MODULE, CLINIC_MODULE), (CAP_SALON_APPOINTMENTS,)),

    DispatcherActionDef(SHOW_SERVICES, "Show services", (SALON_MODULE, CLINIC_MODULE), (CAP_SALON_APPOINTMENTS,)),
    DispatcherActionDef(SHOW_SERVICE_PRICES, "Show service price list", (SALON_MODULE, CLINIC_MODULE), (CAP_SALON_APPOINTMENTS,)),
    DispatcherActionDef(SHOW_PROFESSIONALS, "Show professionals", (SALON_MODULE,), (CAP_SALON_APPOINTMENTS,)),
    DispatcherActionDef(SELECT_DATE, "Select Date", (SALON_MODULE,), (CAP_SALON_APPOINTMENTS,)),
    DispatcherActionDef(SELECT_TIME, "Select Time", (SALON_MODULE,), (CAP_SALON_APPOINTMENTS,)),
    DispatcherActionDef(ASK_NAME, "Ask Name", (SALON_MODULE,), (CAP_SALON_APPOINTMENTS,)),
    DispatcherActionDef(CONFIRM_PROMPT, "Ask Confirmation", (SALON_MODULE,), (CAP_SALON_APPOINTMENTS,)),
    DispatcherActionDef(FINALIZE_BOOKING, "Finalize Booking", (SALON_MODULE,), (CAP_SALON_APPOINTMENTS,)),

    DispatcherActionDef(LIST_DOCTORS, "List doctors", (CLINIC_MODULE,), (CAP_SALON_APPOINTMENTS,)),
    DispatcherActionDef(CHECK_DOCTOR, "Check doctors", (CLINIC_MODULE,), (CAP_SALON_APPOINTMENTS,)),

    DispatcherActionDef(CANCEL_APPOINTMENT, "Cancel appointment", (SALON_MODULE, CLINIC_MODULE),
                        (CAP_SALON_APPOINTMENTS,)),
    DispatcherActionDef(RESCHEDULE_APPOINTMENT, "Reschedule appointment", (SALON_MODULE, CLINIC_MODULE),
                        (CAP_SALON_APPOINTMENTS,)),

    DispatcherActionDef(BROWSE_CATALOG, "Browse catalog", (STORE_MODULE,), (CAP_STORE_CATALOG,)),
    DispatcherActionDef(CHECK_PRICE, "Check price", (STORE_MODULE,), (CAP_STORE_CATALOG,)),
    DispatcherActionDef(CHECK_PRODUCT, "Check product", (STORE_MODULE,), (CAP_STORE_CATALOG,)),
    DispatcherActionDef(TRACK_ORDER, "Track order", (STORE_MODULE,), (CAP_STORE_ORDERS,)),
    DispatcherActionDef(VIEW_OFFERS, "View offers", (STORE_MODULE,), (CAP_STORE_CATALOG,)),
    DispatcherActionDef(VIEW_PRODUCTS, "View products", (STORE_MODULE,), (CAP_STORE_CATALOG,)),
    DispatcherActionDef(VIEW_OFFERS, "Show offers", (CORE_MODULE, STORE_MODULE), ()),
    # Workflow UI + engine expect uppercase END for the close-workflow step
    DispatcherActionDef("END", "End (close workflow)", (CORE_MODULE, SALON_MODULE, CLINIC_MODULE, STORE_MODULE), ()),
)

_DISPATCHER_BY_ID: Dict[str, DispatcherActionDef] = {d.id.lower(): d for d in _DISPATCHER_ACTIONS}

# Legacy menu / NL aliases → canonical dispatcher id (for ``get_action_meta``).
_ACTION_ALIASES: Dict[str, str] = {
    "select_timeslot": BOOK_APPOINTMENT,
    "salon.select_timeslot": BOOK_APPOINTMENT,
    "salon.book_appointment": BOOK_APPOINTMENT,
    "book_doctor": "book_doctor",
    "clinic.book_doctor": "book_doctor",
}

# Store/menu actions that use a single text reply step in workflows
_TEXT_INPUT_ACTION_IDS = frozenset(
    {
        AI_FREE_TEXT.lower(),
        CHECK_PRODUCT.lower(),
        CHECK_PRICE.lower(),
        TRACK_ORDER.lower(),
        SUBMIT_FEEDBACK.lower(),
    }
)


def _tenant_modules_caps(tenant: str) -> tuple[Set[str], Set[str], Optional[Set[str]]]:
    t = get_tenant_service().get_tenant_settings(tenant) or {}
    mods = {str(m).lower() for m in (t.get("modules") or [])}
    caps = {str(c).lower() for c in (t.get("capabilities") or [])}
    raw_ids = t.get("enabled_action_ids") or []
    enabled: Optional[Set[str]] = None
    if isinstance(raw_ids, list) and raw_ids:
        enabled = {str(a).strip().lower() for a in raw_ids if str(a).strip()}
    return mods, caps, enabled


def _visible(mods: Set[str], caps: Set[str], *, step_modules: tuple[str, ...], step_caps: tuple[str, ...]) -> bool:
    if step_modules and not any(m.lower() in mods for m in step_modules):
        return False
    if step_caps and not all(capability_satisfied(caps, c) for c in step_caps):
        return False
    return True


def capability_satisfied(tenant_caps: Set[str], required_cap: str) -> bool:
    """Match tenant capabilities to a required cap (supports short aliases like ``appointments``)."""
    req = (required_cap or "").strip().lower()
    if not req:
        return True
    if req in tenant_caps:
        return True
    return any(req in cap or cap.endswith(f".{req}") for cap in tenant_caps)


def _enabled_action_ids_allow(enabled: Optional[Set[str]], action_id: str) -> bool:
    """When tenant has enabled_action_ids, restrict to that set (END always allowed)."""
    if not enabled:
        return True
    aid = (action_id or "").strip().lower()
    if aid in ("end",):
        return True
    if aid in enabled:
        return True
    canonical = _ACTION_ALIASES.get(aid, aid)
    return canonical.lower() in enabled


def _primary_module(d: DispatcherActionDef) -> str:
    return d.modules[0] if d.modules else CORE_MODULE


def _dispatcher_to_workflow_meta(d: DispatcherActionDef) -> WorkflowActionMeta:
    """Map a dispatcher row to workflow-step metadata for the admin dropdown."""
    aid = d.id
    aid_l = aid.lower()
    is_end = aid_l == "end" or aid.upper() == "END"
    input_required = (not is_end) and aid_l in _TEXT_INPUT_ACTION_IDS
    if is_end:
        ui_type = "none"
        code = "END"
    elif input_required:
        ui_type = "text"
        code = d.id
    else:
        ui_type = "list"
        code = d.id
    mod = _primary_module(d)
    return WorkflowActionMeta(
        action_code=code,
        label=d.label,
        input_required=input_required,
        output_key=None,
        ui_type=ui_type,
        description=None,
        module=mod,
        group=mod,
        requires_caps=list(d.requires_caps),
    )


def _deduped_dispatcher_rows() -> List[DispatcherActionDef]:
    """First row wins per id (case-insensitive) so duplicate BOOK_APPOINTMENT labels don't duplicate dropdown codes."""
    seen: Set[str] = set()
    out: List[DispatcherActionDef] = []
    for d in _DISPATCHER_ACTIONS:
        k = d.id.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(d)
    return out


def get_all_workflow_actions() -> List[WorkflowActionMeta]:
    return [_dispatcher_to_workflow_meta(d) for d in _deduped_dispatcher_rows()]


def action_allowed_for_tenant(tenant: str, action_id: str) -> bool:
    """True when action is visible for tenant modules/caps and enabled_action_ids."""
    raw = (action_id or "").strip()
    if not raw:
        return False
    canonical = _ACTION_ALIASES.get(raw.lower(), raw.lower())
    d = _DISPATCHER_BY_ID.get(canonical)
    if not d:
        # Registered handlers (e.g. confirm_booking) may not be in dispatcher catalog.
        from app.services.whatsapp.action_handler_registry import is_registered
        if not is_registered(raw):
            return False
        mods, caps, enabled = _tenant_modules_caps(tenant)
        return _enabled_action_ids_allow(enabled, raw)
    mods, caps, enabled = _tenant_modules_caps(tenant)
    if not _visible(mods, caps, step_modules=d.modules, step_caps=d.requires_caps):
        return False
    return _enabled_action_ids_allow(enabled, d.id)


def get_available_actions_for_tenant(tenant: str) -> List[WorkflowActionMeta]:
    mods, caps, enabled = _tenant_modules_caps(tenant)
    seen: Set[str] = set()
    out: List[WorkflowActionMeta] = []
    for d in _DISPATCHER_ACTIONS:
        if not _visible(mods, caps, step_modules=d.modules, step_caps=d.requires_caps):
            continue
        if not _enabled_action_ids_allow(enabled, d.id):
            continue
        k = d.id.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(_dispatcher_to_workflow_meta(d))
    return out


def list_dispatcher_actions_for_tenant(tenant: str) -> List[Dict[str, Any]]:
    mods, caps, enabled = _tenant_modules_caps(tenant)
    items: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for d in _DISPATCHER_ACTIONS:
        if not _visible(mods, caps, step_modules=d.modules, step_caps=d.requires_caps):
            continue
        if not _enabled_action_ids_allow(enabled, d.id):
            continue
        k = d.id.lower()
        if k in seen:
            continue
        seen.add(k)
        items.append(
            {
                "id": d.id,
                "label": d.label,
                "module": _primary_module(d),
                "requires_caps": list(d.requires_caps),
            }
        )
    return items


def get_action_meta(action_id: str) -> Optional[Dict[str, Any]]:
    """Resolve a menu/NL action id to dispatcher metadata (``id``, ``label``, ``module``)."""
    raw = (action_id or "").strip().lower()
    if not raw:
        return None
    canonical = _ACTION_ALIASES.get(raw, raw)
    d = _DISPATCHER_BY_ID.get(canonical)
    if not d:
        return None
    return {
        "id": d.id,
        "label": d.label,
        "module": _primary_module(d),
        "requires_caps": list(d.requires_caps),
    }
