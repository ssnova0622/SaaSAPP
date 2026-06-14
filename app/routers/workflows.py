from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.workflows import WorkflowDefinition
from app.routers.deps import get_current_user, ensure_tenant_active, ensure_tenant_scope
from app.services.whatsapp.usecases.action_registry import get_available_actions_for_tenant
from app.services.whatsapp.workflow.workflow_engine import WorkflowEngine
from app.services.whatsapp.workflow.workflow_validator import WorkflowValidationError

router = APIRouter()


@router.get("/tenants/{tenant}/workflows", tags=["Admin"])
def list_workflows(
        tenant: str,
        user: dict = Depends(get_current_user),
        _ok=Depends(ensure_tenant_active),
        _scope=Depends(ensure_tenant_scope()),
):
    return {"items": WorkflowEngine.list_workflows(tenant)}


@router.get("/tenants/{tenant}/workflows/audit", tags=["Admin"])
def audit_workflows(
        tenant: str,
        user: dict = Depends(get_current_user),
        _ok=Depends(ensure_tenant_active),
        _scope=Depends(ensure_tenant_scope()),
):
    """List validation results for all workflows (includes repair preview for legacy steps)."""
    from app.services.whatsapp.workflow.workflow_migrator import audit_tenant_workflows

    return {"items": audit_tenant_workflows(tenant)}


@router.post("/tenants/{tenant}/workflows/repair", tags=["Admin"])
def repair_workflows(
        tenant: str,
        user: dict = Depends(get_current_user),
        _ok=Depends(ensure_tenant_active),
        _scope=Depends(ensure_tenant_scope()),
):
    """Auto-repair legacy/invalid workflow step codes where possible."""
    from app.services.whatsapp.workflow.workflow_migrator import fix_tenant_workflows

    return fix_tenant_workflows(tenant, dry_run=False)


@router.get("/tenants/{tenant}/workflows/{workflow_id}", tags=["Admin"])
def get_workflow(
        tenant: str,
        workflow_id: str,
        user: dict = Depends(get_current_user),
        _ok=Depends(ensure_tenant_active),
        _scope=Depends(ensure_tenant_scope()),
):
    wf = WorkflowEngine.get_workflow(tenant, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.post("/tenants/{tenant}/workflows", tags=["Admin"])
def upsert_workflow(
        tenant: str,
        body: WorkflowDefinition,
        user: dict = Depends(get_current_user),
        _ok=Depends(ensure_tenant_active),
        _scope=Depends(ensure_tenant_scope()),
):
    if body.tenant != tenant:
        raise HTTPException(status_code=400, detail="Tenant mismatch")
    try:
        WorkflowEngine.upsert_workflow(tenant, body)
    except WorkflowValidationError as exc:
        raise HTTPException(status_code=400, detail={"errors": list(exc.errors)})
    return {"ok": True}


@router.delete("/tenants/{tenant}/workflows/{workflow_id}", tags=["Admin"])
def delete_workflow(
        tenant: str,
        workflow_id: str,
        user: dict = Depends(get_current_user),
        _ok=Depends(ensure_tenant_active),
        _scope=Depends(ensure_tenant_scope()),
):
    if not WorkflowEngine.get_workflow(tenant, workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found")
    if not WorkflowEngine.delete_workflow(tenant, workflow_id):
        raise HTTPException(status_code=500, detail="Failed to delete workflow")
    return {"ok": True}


@router.get("/workflows/available-actions", tags=["Admin"])
def list_available_workflow_actions(
        tenant: Optional[str] = Query(None,
                                      description="Filter actions by tenant's enabled actions or modules/capabilities"),
        user: dict = Depends(get_current_user),
):
    """Return workflow step types from code registry, filtered by tenant modules/caps when tenant is set."""
    if tenant:
        return {"items": get_available_actions_for_tenant(tenant)}
    return {"items": WorkflowEngine.get_available_actions()}
