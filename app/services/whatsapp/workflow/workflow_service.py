"""
Workflow CRUD: list, get, upsert, delete. No action logic; workflow engine uses action_executor for steps.
"""
from __future__ import annotations
import re
from typing import List, Optional

from app.helpers.date_utils import utcnow
from app.models.workflows import WorkflowDefinition
from app.services.db import workflows_collection
from app.services.whatsapp.workflow.workflow_validator import assert_workflow_valid


def get_workflow(tenant: str, workflow_id: str) -> Optional[WorkflowDefinition]:
    """Load workflow by tenant and workflow_id (case-insensitive)."""
    col = workflows_collection()
    pattern = re.escape((workflow_id or "").strip())
    if not pattern:
        return None
    doc = col.find_one({"tenant": tenant, "workflow_id": {"$regex": f"^{pattern}$", "$options": "i"}})
    if not doc:
        return None
    return WorkflowDefinition(**doc)


def list_workflows(tenant: str) -> List[WorkflowDefinition]:
    """List all workflows for the tenant."""
    col = workflows_collection()
    return [WorkflowDefinition(**doc) for doc in col.find({"tenant": tenant})]


def upsert_workflow(tenant: str, workflow: WorkflowDefinition) -> bool:
    """Create or update a workflow for the tenant."""
    assert_workflow_valid(tenant, workflow)
    col = workflows_collection()
    doc = workflow.model_dump()
    doc["workflow_id"] = (workflow.workflow_id or "").strip().lower()
    doc["updated_at"] = utcnow()
    if not doc.get("created_at"):
        doc["created_at"] = utcnow()

    pattern = re.escape((workflow.workflow_id or "").strip())
    filter_query = {"tenant": tenant}
    if pattern:
        filter_query["workflow_id"] = {"$regex": f"^{pattern}$", "$options": "i"}
    else:
        filter_query["workflow_id"] = doc["workflow_id"]

    col.update_one(filter_query, {"$set": doc}, upsert=True)
    return True


def delete_workflow(tenant: str, workflow_id: str) -> bool:
    """Delete workflow by tenant and workflow_id. Returns True if deleted."""
    wf = get_workflow(tenant, workflow_id)
    if not wf:
        return False
    col = workflows_collection()
    res = col.delete_one({"tenant": tenant, "workflow_id": wf.workflow_id})
    return res.deleted_count > 0
