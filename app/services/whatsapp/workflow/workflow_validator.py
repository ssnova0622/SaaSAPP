"""
Validate tenant workflow definitions before save.

Ensures every step resolves to a registered handler and is allowed for the tenant
(modules, capabilities, optional enabled_action_ids).
"""
from __future__ import annotations

from typing import List, Set

from app.core.container import get_tenant_service
from app.helpers.constants_action import END
from app.models.workflows import WorkflowDefinition
from app.services.whatsapp.action_handler_registry import is_registered
from app.services.whatsapp.usecases.action_registry import action_allowed_for_tenant, capability_satisfied
from app.services.whatsapp.workflow.workflow_step_policy import normalize_workflow_action_code


def _ensure_handler_registry_loaded() -> None:
    """Import handler modules so self-registration runs before ``is_registered`` checks."""
    try:
        from app.services.whatsapp.usecases.ai import ai_actions  # noqa: F401
        from app.services.whatsapp.usecases.clinic import clinic_actions  # noqa: F401
        from app.services.whatsapp.usecases.core import core_actions  # noqa: F401
        from app.services.whatsapp.usecases.salon import salon_actions  # noqa: F401
        from app.services.whatsapp.usecases.store import store_actions  # noqa: F401
    except Exception:
        pass


class WorkflowValidationError(Exception):
    """Raised when a workflow definition fails validation."""

    def __init__(self, errors: tuple[str, ...] | list[str]):
        self.errors = tuple(errors)
        super().__init__("; ".join(self.errors))


def _tenant_caps(tenant: str) -> Set[str]:
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    return {str(c).lower() for c in (settings.get("capabilities") or [])}


def validate_workflow_definition(tenant: str, workflow: WorkflowDefinition) -> List[str]:
    """
    Return a list of validation error messages (empty when valid).

    Does not raise — callers decide whether to reject or warn.
    """
    errors: List[str] = []
    _ensure_handler_registry_loaded()
    wf_id = (workflow.workflow_id or "").strip()
    if not wf_id:
        errors.append("workflow_id is required")

    steps = workflow.steps or []
    if not steps:
        errors.append("At least one step is required")
        return errors

    caps = _tenant_caps(tenant)
    req = [str(x).lower() for x in (getattr(workflow, "requires_caps", None) or [])]
    if req and caps and not all(capability_satisfied(caps, r) for r in req):
        missing = [r for r in req if not capability_satisfied(caps, r)]
        errors.append(f"Tenant missing required capabilities: {', '.join(missing)}")

    has_end = False
    for idx, step in enumerate(steps, start=1):
        raw_code = (getattr(step, "action_code", None) or "").strip()
        if not raw_code:
            errors.append(f"Step {idx}: action_code is required")
            continue
        code = normalize_workflow_action_code(raw_code)
        if code == END:
            has_end = True
            continue
        if not is_registered(raw_code):
            errors.append(f"Step {idx}: unknown action '{raw_code}' (no handler registered)")
            continue
        if not action_allowed_for_tenant(tenant, raw_code):
            errors.append(f"Step {idx}: action '{raw_code}' is not enabled for this tenant")

    if not has_end:
        errors.append("Workflow must include an END step as the closing step")

    return errors


def assert_workflow_valid(tenant: str, workflow: WorkflowDefinition) -> None:
    """Raise :class:`WorkflowValidationError` when validation fails."""
    errors = validate_workflow_definition(tenant, workflow)
    if errors:
        raise WorkflowValidationError(errors=tuple(errors))
