"""
Audit and repair saved workflow definitions in MongoDB.

Used by the admin CLI ``scripts/super_admin/validate_and_fix_workflows.py`` and the
workflows audit API.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.helpers.constants_action import END
from app.helpers.date_utils import utcnow
from app.models.workflows import WorkflowDefinition, WorkflowStep
from app.services.db import workflows_collection
from app.services.whatsapp.workflow.workflow_step_policy import normalize_workflow_action_code
from app.services.whatsapp.workflow.workflow_validator import validate_workflow_definition

# Legacy / placeholder step codes from early seeds → registered handlers.
LEGACY_ACTION_REPLACEMENTS: Dict[str, str] = {
    "show_categories": "browse_catalog",
    "show_products": "browse_catalog",
    "view_cart": "browse_catalog",
    "checkout": "END",
    "collect_order_id": "track_order",
    "show_order_detail": "track_order",
}

_DEFAULT_END_LABEL = "Reply *hi* anytime to return to the main menu."


def _norm(code: str) -> str:
    return normalize_workflow_action_code(code or "")


def _step_dict(step: WorkflowStep | Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(step, WorkflowStep):
        return step.model_dump()
    return dict(step or {})


def _steps_have_end(steps: List[Dict[str, Any]]) -> bool:
    return any(_norm(s.get("action_code", "")) == END for s in steps)


def repair_workflow_steps(steps: List[WorkflowStep | Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Return repaired step list and human-readable change notes.

    - Rewrites known legacy action codes
    - Drops redundant checkout-only placeholders when END follows
    - Appends END when missing
    """
    changes: List[str] = []
    out: List[Dict[str, Any]] = []

    for raw in steps or []:
        doc = _step_dict(raw)
        code = (doc.get("action_code") or "").strip()
        norm = _norm(code)
        replacement = LEGACY_ACTION_REPLACEMENTS.get(norm)
        if replacement:
            if replacement.upper() == "END":
                changes.append(f"Dropped legacy step '{code}' (use END step instead)")
                continue
            doc["action_code"] = replacement.upper()
            changes.append(f"Replaced '{code}' → '{doc['action_code']}'")
        out.append(doc)

    # Remove duplicate browse/track steps back-to-back after replacement
    deduped: List[Dict[str, Any]] = []
    for doc in out:
        if deduped:
            prev = _norm(deduped[-1].get("action_code", ""))
            cur = _norm(doc.get("action_code", ""))
            if prev == cur and prev in {"browse_catalog", "track_order"}:
                changes.append(f"Dropped duplicate consecutive '{doc.get('action_code')}' step")
                continue
        deduped.append(doc)
    out = deduped

    if not _steps_have_end(out):
        out.append(
            {
                "action_code": "END",
                "label": _DEFAULT_END_LABEL,
                "input_required": False,
                "ui_type": "list",
                "params": {},
            }
        )
        changes.append("Appended missing END step")

    return out, changes


def audit_workflow(tenant: str, workflow: WorkflowDefinition) -> Dict[str, Any]:
    """Validate one workflow; return audit record with errors and optional repair preview."""
    errors = validate_workflow_definition(tenant, workflow)
    repaired_steps, repair_notes = repair_workflow_steps(workflow.steps or [])
    preview = WorkflowDefinition(
        tenant=workflow.tenant,
        workflow_id=workflow.workflow_id,
        name=workflow.name,
        steps=[WorkflowStep(**s) for s in repaired_steps],
        active=workflow.active,
        requires_caps=list(getattr(workflow, "requires_caps", None) or []),
    )
    post_repair_errors = validate_workflow_definition(tenant, preview) if repair_notes else errors
    return {
        "tenant": tenant,
        "workflow_id": workflow.workflow_id,
        "name": workflow.name,
        "valid": not errors,
        "errors": errors,
        "repair_available": bool(repair_notes) and not post_repair_errors,
        "repair_notes": repair_notes,
        "errors_after_repair": post_repair_errors if repair_notes else [],
    }


def audit_tenant_workflows(tenant: str) -> List[Dict[str, Any]]:
    col = workflows_collection()
    items: List[Dict[str, Any]] = []
    for doc in col.find({"tenant": tenant}):
        wf = WorkflowDefinition(**doc)
        items.append(audit_workflow(tenant, wf))
    return items


def audit_all_workflows() -> List[Dict[str, Any]]:
    col = workflows_collection()
    items: List[Dict[str, Any]] = []
    for doc in col.find({}):
        tenant = str(doc.get("tenant") or "")
        if not tenant:
            continue
        wf = WorkflowDefinition(**doc)
        items.append(audit_workflow(tenant, wf))
    return items


def fix_workflow(tenant: str, workflow_id: str, *, dry_run: bool = False) -> Dict[str, Any]:
    """Repair one workflow in MongoDB when possible."""
    col = workflows_collection()
    doc = col.find_one({"tenant": tenant, "workflow_id": workflow_id})
    if not doc:
        return {"ok": False, "error": "Workflow not found", "workflow_id": workflow_id}

    wf = WorkflowDefinition(**doc)
    audit = audit_workflow(tenant, wf)
    if audit["valid"]:
        return {"ok": True, "workflow_id": workflow_id, "changed": False, "notes": []}

    if not audit["repair_available"]:
        return {
            "ok": False,
            "workflow_id": workflow_id,
            "changed": False,
            "errors": audit["errors"],
            "errors_after_repair": audit.get("errors_after_repair") or audit["errors"],
        }

    repaired_steps, notes = repair_workflow_steps(wf.steps or [])
    if dry_run:
        return {"ok": True, "workflow_id": workflow_id, "changed": True, "dry_run": True, "notes": notes}

    col.update_one(
        {"tenant": tenant, "workflow_id": workflow_id},
        {"$set": {"steps": repaired_steps, "updated_at": utcnow()}},
    )
    return {"ok": True, "workflow_id": workflow_id, "changed": True, "notes": notes}


def fix_tenant_workflows(tenant: str, *, dry_run: bool = False) -> Dict[str, Any]:
    col = workflows_collection()
    results: List[Dict[str, Any]] = []
    for doc in col.find({"tenant": tenant}):
        wf_id = doc.get("workflow_id")
        if wf_id:
            results.append(fix_workflow(tenant, str(wf_id), dry_run=dry_run))
    fixed = sum(1 for r in results if r.get("changed"))
    failed = [r for r in results if not r.get("ok")]
    return {"tenant": tenant, "total": len(results), "fixed": fixed, "failed": len(failed), "results": results}


def fix_all_workflows(*, dry_run: bool = False) -> Dict[str, Any]:
    col = workflows_collection()
    tenants = sorted({str(d.get("tenant")) for d in col.find({}, {"tenant": 1}) if d.get("tenant")})
    summaries = [fix_tenant_workflows(t, dry_run=dry_run) for t in tenants]
    return {
        "tenants": len(tenants),
        "fixed": sum(s["fixed"] for s in summaries),
        "failed": sum(s["failed"] for s in summaries),
        "summaries": summaries,
    }
