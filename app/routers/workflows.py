from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.workflows import WorkflowDefinition
from app.routers.deps import get_current_user, ensure_tenant_active, ensure_tenant_scope
from app.services.whatsapp.usecases.action_registry import get_available_actions_for_tenant
from app.services.whatsapp.workflow.workflow_engine import WorkflowEngine

router = APIRouter()


@router.get("/tenants/{tenant}/workflows", tags=["Admin"])
def list_workflows(
        tenant: str,
        user: dict = Depends(get_current_user),
        _ok=Depends(ensure_tenant_active),
        _scope=Depends(ensure_tenant_scope()),
):
    return {"items": WorkflowEngine.list_workflows(tenant)}


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
    WorkflowEngine.upsert_workflow(tenant, body)
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
