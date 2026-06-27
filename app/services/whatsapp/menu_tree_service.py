"""
WhatsApp menu tree: resolve node, render submenu, validate tree, send submenu reply.
All menu/navigation logic lives here; routes only call this service.
"""
from __future__ import annotations
import json
import re
from typing import Any, Dict, Optional, Set

from fastapi import HTTPException
from app.core.container import get_tenant_service, get_whatsapp_service
from app.services.whatsapp.action_support import get_action_logger
from app.services.whatsapp.helpers.constants import PROMPT_CHOOSE_OPTION, PROMPT_CHOOSE, LABEL_OPTION, REPLY_WITH_NUMBER
from app.services.whatsapp.message_render_service import validate_placeholders
from app.services.whatsapp.custom_action_executor import is_custom_action_id, parse_custom_action_id
from app.services.whatsapp.usecases.action_registry import action_allowed_for_tenant

logger = get_action_logger("menu_tree")


def find_node(tree: Dict[str, Any], node_id: str) -> Optional[Dict[str, Any]]:
    """Find a node by ID in the menu tree."""
    for node in (tree.get("nodes") or []):
        if node.get("id") == node_id:
            return node
    return None


def render_submenu(node: Dict[str, Any], locale: str = "en") -> str:
    """Render a submenu node as text for WhatsApp."""
    title = node.get("title") or ""
    prompt = node.get("prompt") or PROMPT_CHOOSE_OPTION
    lines = []
    if title:
        lines.append(str(title))
    lines.append(str(prompt))
    options = node.get("options") or []
    for opt in options:
        key = opt.get("key")
        label = opt.get("label") or opt.get("title") or LABEL_OPTION
        lines.append(f"{key}) {label}")
    lines.append(REPLY_WITH_NUMBER)
    return "\n".join(lines)


def _valid_next_target(next_node_id: Any, node_ids: Set[str]) -> bool:
    if not next_node_id:
        return True
    if next_node_id in node_ids:
        return True
    if isinstance(next_node_id, str):
        nxt = next_node_id.strip()
        if nxt.startswith("workflow."):
            return bool(nxt[9:].strip())
        if is_custom_action_id(nxt):
            return bool(parse_custom_action_id(nxt))
    return False


def _validate_action_node(node: Dict[str, Any], node_id: str, tenant: Optional[str]) -> None:
    action_type = str(node.get("action_type") or "").strip().lower()
    if action_type == "static_text":
        text = str(node.get("text") or "").strip()
        if not text:
            raise HTTPException(
                status_code=400,
                detail=f"Action node '{node_id}' (static_text) requires non-empty text",
            )
        ph_err = validate_placeholders(text)
        if ph_err:
            raise HTTPException(status_code=400, detail=f"Node '{node_id}': {ph_err}")
        return

    action_id = str(node.get("action") or node.get("action_id") or "").strip()
    custom_id = str(node.get("custom_action_id") or "").strip()

    if custom_id:
        if tenant:
            doc = get_whatsapp_service().get_tenant_whatsapp_action(tenant, custom_id)
            if not doc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Node '{node_id}' references unknown custom action '{custom_id}'",
                )
        return

    if not action_id:
        raise HTTPException(
            status_code=400,
            detail=f"Action node '{node_id}' must set action_id, custom_action_id, or action_type=static_text",
        )

    if action_id.startswith("workflow."):
        if not action_id[9:].strip():
            raise HTTPException(status_code=400, detail=f"Node '{node_id}' has invalid workflow reference")
        return

    if is_custom_action_id(action_id):
        slug = parse_custom_action_id(action_id)
        if tenant and slug:
            doc = get_whatsapp_service().get_tenant_whatsapp_action(tenant, slug)
            if not doc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Node '{node_id}' references unknown custom action '{slug}'",
                )
        return

    if tenant and not action_allowed_for_tenant(tenant, action_id):
        raise HTTPException(
            status_code=400,
            detail=f"Action '{action_id}' on node '{node_id}' is not allowed for this tenant",
        )

    override = str(node.get("text") or node.get("title") or "").strip()
    if override:
        ph_err = validate_placeholders(override)
        if ph_err:
            raise HTTPException(status_code=400, detail=f"Node '{node_id}': {ph_err}")


def validate_menu_tree(tree: Dict[str, Any], *, tenant: Optional[str] = None) -> None:
    """Validate the structure of a WhatsApp menu tree. Raises HTTPException on invalid."""
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
                if next_node_id and not _valid_next_target(next_node_id, node_ids):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Option in '{node_id}' points to missing node '{next_node_id}'",
                    )
        elif node_type == "action":
            _validate_action_node(node, str(node_id), tenant)


def build_meta_interactive_payload(phone: str, node: Dict[str, Any]) -> Dict[str, Any]:
    """Build a Meta Cloud interactive payload (buttons when <= 3 options, else list)."""
    title = (node.get("title") or "").strip()
    prompt = (node.get("prompt") or PROMPT_CHOOSE_OPTION).strip()
    options = node.get("options") or []
    rows = []
    for opt in options:
        key = str(opt.get("key"))
        label = str(opt.get("label") or opt.get("title") or f"Option {key}")
        rows.append({"id": key, "title": label[:20], "description": label[20:80]})
    body_text = f"{title}\n{prompt}".strip() if title else prompt
    if len(rows) <= 3:
        interactive = {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [{"type": "reply", "reply": {"id": r["id"], "title": r["title"]}} for r in rows]
            },
        }
    else:
        interactive = {
            "type": "list",
            "body": {"text": body_text},
            "action": {"button": "Choose", "sections": [{"title": "Menu", "rows": rows}]},
        }
    return {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": interactive,
    }


def send_submenu_reply(tenant: str, phone: str, node: Dict[str, Any], locale: str = "en") -> str:
    """Render and optionally log/send provider-specific submenu replies. Returns text to send."""
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    wa_config = settings.get("whatsapp_config") or {}
    provider = str(wa_config.get("provider") or "twilio").lower()
    if provider in ("meta", "meta_cloud"):
        try:
            payload = build_meta_interactive_payload(phone, node)
            logger.info("Meta Cloud interactive payload: %s", json.dumps(payload))
        except Exception as e:
            logger.error("Failed to build Meta payload: %s", e)
        options = node.get("options") or []
        labels = [str(o.get("label") or o.get("title") or o.get("key")) for o in options]
        prefix = f"{node.get('title')}\n" if node.get("title") else ""
        prompt = node.get("prompt") or PROMPT_CHOOSE
        if len(labels) <= 3:
            return f"{prefix}{prompt}\n" + " | ".join(labels) + "\n(Reply with option number)"
    return render_submenu(node, locale)


def extract_choice_key(text: str) -> str:
    """Extract a menu choice key from user text (e.g., '1' from '1) booking')."""
    s = (text or "").strip()
    if not s:
        return ""
    match = re.match(r"^\s*([0-9A-Za-z]+)", s)
    return match.group(1) if match else s


def resolve_active_menu_id(tenant: str) -> Optional[str]:
    """Resolve which menu ID is currently active for a tenant."""
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    wa_config = settings.get("whatsapp_config") or {}
    active_id = str(wa_config.get("active_menu_id") or "").strip()
    wa = get_whatsapp_service()
    if active_id:
        if wa.get_whatsapp_menu(tenant, active_id, status="published"):
            return active_id
    if wa.get_whatsapp_menu(tenant, "welcome_message", status="published"):
        return "welcome_message"
    menus = wa.list_whatsapp_menus(tenant)
    published = [m for m in menus if m.get("status") == "published"]
    if published:
        published.sort(key=lambda m: int(m.get("version") or 0), reverse=True)
        return str(published[0].get("menu_id"))
    return None
