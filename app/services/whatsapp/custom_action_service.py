"""Tenant-scoped reusable WhatsApp custom actions (static, predefined, workflow)."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.services.whatsapp.message_render_service import (
    sanitize_message_text,
    validate_placeholders,
)
from app.services.whatsapp.usecases.action_registry import action_allowed_for_tenant

_ACTION_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_VALID_TYPES = frozenset({"static_text", "predefined", "workflow"})


def validate_action_id(action_id: str) -> None:
    aid = (action_id or "").strip().lower()
    if not aid or not _ACTION_ID_RE.match(aid):
        raise HTTPException(
            status_code=400,
            detail="action_id must be lowercase slug (a-z, 0-9, _, -), 1–64 chars",
        )


def validate_custom_action_payload(tenant: str, body: Dict[str, Any], *, is_update: bool = False) -> Dict[str, Any]:
    """Validate and normalize a tenant custom action document."""
    action_id = str(body.get("action_id") or "").strip().lower()
    if not is_update:
        validate_action_id(action_id)
    name = str(body.get("name") or action_id or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    action_type = str(body.get("action_type") or "static_text").strip().lower()
    if action_type not in _VALID_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"action_type must be one of: {', '.join(sorted(_VALID_TYPES))}",
        )

    text = str(body.get("text") or body.get("message") or "").strip()
    system_action_id = str(body.get("system_action_id") or body.get("action") or "").strip()
    workflow_id = str(body.get("workflow_id") or "").strip()
    params = body.get("params") if isinstance(body.get("params"), dict) else {}

    if action_type == "static_text":
        if not text:
            raise HTTPException(status_code=400, detail="text is required for static_text actions")
        ph_err = validate_placeholders(text)
        if ph_err:
            raise HTTPException(status_code=400, detail=ph_err)
    elif action_type == "predefined":
        if not system_action_id:
            raise HTTPException(status_code=400, detail="system_action_id is required for predefined actions")
        if not action_allowed_for_tenant(tenant, system_action_id):
            raise HTTPException(status_code=400, detail=f"Action '{system_action_id}' is not allowed for this tenant")
        if text:
            ph_err = validate_placeholders(text)
            if ph_err:
                raise HTTPException(status_code=400, detail=ph_err)
    elif action_type == "workflow":
        if not workflow_id:
            raise HTTPException(status_code=400, detail="workflow_id is required for workflow actions")

    try:
        text_safe = sanitize_message_text(text) if text else ""
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "action_id": action_id,
        "name": name,
        "action_type": action_type,
        "text": text_safe,
        "system_action_id": system_action_id,
        "workflow_id": workflow_id,
        "params": params,
        "enabled": bool(body.get("enabled", True)),
    }


def custom_action_runtime_id(action_id: str) -> str:
    """Canonical runtime reference for menu nodes and triggers."""
    return f"custom.{str(action_id).strip().lower()}"


def list_custom_actions_for_registry(actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Shape tenant custom actions for menu / workflow action pickers."""
    items: List[Dict[str, Any]] = []
    for a in actions:
        if not a.get("enabled", True):
            continue
        aid = str(a.get("action_id") or "").strip()
        if not aid:
            continue
        atype = str(a.get("action_type") or "static_text")
        label = str(a.get("name") or aid)
        items.append(
            {
                "id": custom_action_runtime_id(aid),
                "label": f"{label} (custom)",
                "module": "custom",
                "requires_caps": [],
                "action_type": atype,
                "custom_action_id": aid,
            }
        )
    return items
