"""WhatsApp menus and config admin endpoints."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Body

from app.routers.deps import get_current_user, ensure_tenant_scope
from app.core.container import get_tenant_service, get_whatsapp_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Admin"])


def _validate_menu_tree(tree: Dict[str, Any]) -> None:
    """Validate the structure of a WhatsApp menu tree."""
    if not isinstance(tree, dict):
        raise HTTPException(status_code=400, detail="tree must be an object")
    root_id = tree.get("root")
    nodes = tree.get("nodes")
    if not root_id or not isinstance(root_id, str):
        raise HTTPException(status_code=400, detail="tree.root is required and must be a string")
    if not isinstance(nodes, list) or not nodes:
        raise HTTPException(status_code=400, detail="tree.nodes must be a non-empty array")
    node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
    if root_id not in node_ids:
        raise HTTPException(status_code=400, detail="tree.root must reference an existing node id in tree.nodes")
    if len(node_ids) != len(nodes):
        raise HTTPException(status_code=400, detail="Duplicate node ids in tree.nodes")
    for node in nodes:
        if not isinstance(node, dict):
            raise HTTPException(status_code=400, detail="Each node must be an object")
        node_id = node.get("id")
        node_type = node.get("type")
        if node_type not in ("submenu", "action"):
            raise HTTPException(status_code=400, detail=f"Unsupported node.type '{node_type}' for node '{node_id}'")
        if node_type == "submenu":
            options = node.get("options") or []
            option_keys = [str(opt.get("key")) for opt in options if
                           isinstance(opt, dict) and opt.get("key") is not None]
            if len(option_keys) != len(set(option_keys)):
                raise HTTPException(status_code=400, detail=f"Duplicate option keys in submenu '{node_id}'")
            for opt in options:
                next_node_id = opt.get("next")
                if next_node_id and next_node_id not in node_ids and not (
                        isinstance(next_node_id, str) and next_node_id.strip().startswith("workflow.")):
                    raise HTTPException(status_code=400,
                                        detail=f"Option in '{node_id}' points to missing node '{next_node_id}'")


@router.get("/tenants/{tenant}/whatsapp/menus")
def list_whatsapp_menus(
    tenant: str,
    _user: Dict[str, Any] = Depends(get_current_user),
    _scope: bool = Depends(ensure_tenant_scope),
):
    """List all WhatsApp menus for a tenant."""
    items = get_whatsapp_service().list_whatsapp_menus(tenant)
    return {"items": items, "total": len(items)}


@router.get("/tenants/{tenant}/whatsapp/menus/{menu_id}")
def get_whatsapp_menu(
    tenant: str,
    menu_id: str,
    status: Optional[str] = None,
    version: Optional[int] = None,
    _user: Dict[str, Any] = Depends(get_current_user),
    _scope: bool = Depends(ensure_tenant_scope),
):
    """Get a specific WhatsApp menu by ID, status, or version."""
    doc = get_whatsapp_service().get_whatsapp_menu(tenant, menu_id, status=status, version=version)
    if not doc:
        raise HTTPException(status_code=404, detail="Menu not found")
    return doc


@router.post("/tenants/{tenant}/whatsapp/menus")
def upsert_whatsapp_menu(
        tenant: str,
        body: Dict[str, Any] = Body(...),
        user: Dict[str, Any] = Depends(get_current_user),
):
    """Create or update a WhatsApp menu draft."""
    menu_id = str(body.get("menu_id") or "default").strip()
    _validate_menu_tree(body.get("tree") or {})
    doc = {
        "tenant": tenant,
        "menu_id": menu_id,
        "name": str(body.get("name") or menu_id).strip(),
        "tree": body.get("tree"),
        "locales": body.get("locales") or {},
        "updated_by": user.get("email") or user.get("sub"),
    }
    return get_whatsapp_service().upsert_whatsapp_menu_draft(tenant, doc)


@router.post("/tenants/{tenant}/whatsapp/menus/{menu_id}/publish")
def publish_whatsapp_menu(
    tenant: str,
    menu_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    _scope: bool = Depends(ensure_tenant_scope),
):
    """Publish a draft menu to make it active."""
    draft = get_whatsapp_service().get_whatsapp_menu(tenant, menu_id, status="draft")
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    _validate_menu_tree(draft.get("tree") or {})
    return get_whatsapp_service().publish_whatsapp_menu(tenant, menu_id, user_id=str(user.get("email") or "admin"))


@router.delete("/tenants/{tenant}/whatsapp/menus/{menu_id}")
def delete_whatsapp_menu(
    tenant: str,
    menu_id: str,
    _user: Dict[str, Any] = Depends(get_current_user),
    _scope: bool = Depends(ensure_tenant_scope),
):
    """Delete a WhatsApp menu (draft only usually)."""
    if not get_whatsapp_service().delete_whatsapp_menu(tenant, menu_id):
        raise HTTPException(status_code=404, detail="Menu not found or cannot be deleted")
    return {"ok": True}


@router.get("/tenants/{tenant}/whatsapp/config")
def get_whatsapp_config(
    tenant: str,
    _user: Dict[str, Any] = Depends(get_current_user),
    _scope: bool = Depends(ensure_tenant_scope),
):
    """Get tenant-specific WhatsApp configuration."""
    settings = get_tenant_service().get_tenant_settings(tenant)
    if not settings:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return settings.get("whatsapp_config") or {}


@router.put("/tenants/{tenant}/whatsapp/config")
def put_whatsapp_config(
        tenant: str,
        body: Dict[str, Any] = Body(...),
        user: Dict[str, Any] = Depends(get_current_user),
        _scope: bool = Depends(ensure_tenant_scope),
):
    """Update tenant-specific WhatsApp configuration."""
    user_id = user.get("sub") or user.get("email")
    cfg = dict(body or {})
    raw_nums = cfg.get("from_numbers") or ([cfg.get("from_number")] if cfg.get("from_number") else [])
    if not isinstance(raw_nums, list):
        raise HTTPException(status_code=400, detail="from_numbers must be a list")
    normalized = []
    for num in raw_nums:
        if not isinstance(num, str) or not num.strip():
            continue
        val = num.strip()
        if not val.lower().startswith("whatsapp:"):
            val = f"whatsapp:{val}"
        if val not in normalized:
            normalized.append(val)
    cfg["from_numbers"] = normalized
    if normalized:
        cfg["from_number"] = normalized[0]
    updated = get_tenant_service().update_tenant_settings(tenant, {"whatsapp_config": cfg}, user_id=user_id)
    return updated.get("whatsapp_config") or {}


# ---------- WhatsApp Triggers CRUD ----------

@router.get("/tenants/{tenant}/whatsapp/triggers")
def list_whatsapp_triggers(
        tenant: str,
        user: Dict[str, Any] = Depends(get_current_user),
        _scope: bool = Depends(ensure_tenant_scope()),
):
    """List all WhatsApp triggers for the tenant."""
    items = get_whatsapp_service().list_whatsapp_triggers(tenant)
    return {"items": items, "total": len(items)}


@router.post("/tenants/{tenant}/whatsapp/triggers")
def create_whatsapp_trigger(
        tenant: str,
        body: Dict[str, Any] = Body(...),
        user: Dict[str, Any] = Depends(get_current_user),
        _scope: bool = Depends(ensure_tenant_scope()),
):
    """Create or replace a WhatsApp trigger."""
    trigger_id = str(body.get("trigger_id") or "").strip()
    if not trigger_id:
        raise HTTPException(status_code=400, detail="trigger_id is required")
    payload = {
        "trigger_id": trigger_id,
        "match": body.get("match") or {},
        "action": body.get("action") or {},
        "enabled": bool(body.get("enabled", True)),
        "priority": int(body.get("priority") or 0),
        "updated_by": user.get("email") or user.get("sub"),
    }
    try:
        doc = get_whatsapp_service().upsert_whatsapp_trigger(tenant, payload)
        return doc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/tenants/{tenant}/whatsapp/triggers/{trigger_id}")
def update_whatsapp_trigger(
        tenant: str,
        trigger_id: str,
        body: Dict[str, Any] = Body(...),
        user: Dict[str, Any] = Depends(get_current_user),
        _scope: bool = Depends(ensure_tenant_scope()),
):
    """Partially update a WhatsApp trigger."""
    existing = get_whatsapp_service().get_whatsapp_trigger(tenant, trigger_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Trigger not found")
    payload = dict(existing)
    if "match" in body:
        payload["match"] = body["match"]
    if "action" in body:
        payload["action"] = body["action"]
    if "enabled" in body:
        payload["enabled"] = bool(body["enabled"])
    if "priority" in body:
        payload["priority"] = int(body["priority"])
    payload["updated_by"] = user.get("email") or user.get("sub")
    return get_whatsapp_service().upsert_whatsapp_trigger(tenant, payload)


@router.delete("/tenants/{tenant}/whatsapp/triggers/{trigger_id}")
def delete_whatsapp_trigger(
        tenant: str,
        trigger_id: str,
        user: Dict[str, Any] = Depends(get_current_user),
        _scope: bool = Depends(ensure_tenant_scope()),
):
    """Delete a WhatsApp trigger."""
    ok = get_whatsapp_service().delete_whatsapp_trigger(
        tenant, trigger_id, user_id=user.get("email") or user.get("sub")
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Trigger not found")
    return {"ok": True}
