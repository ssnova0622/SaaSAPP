"""
WhatsApp menu tree: resolve node, render submenu, validate tree, send submenu reply.
All menu/navigation logic lives here; routes only call this service.
"""
from __future__ import annotations
import json
import re
from typing import Any, Dict, Optional

from fastapi import HTTPException
from app.core.container import get_tenant_service, get_whatsapp_service
from app.services.whatsapp.action_support import get_action_logger
from app.services.whatsapp.helpers.constants import PROMPT_CHOOSE_OPTION, PROMPT_CHOOSE, LABEL_OPTION, REPLY_WITH_NUMBER

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


def validate_menu_tree(tree: Dict[str, Any]) -> None:
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
                if next_node_id and next_node_id not in node_ids and not (
                        isinstance(next_node_id, str) and next_node_id.strip().startswith("workflow.")
                ):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Option in '{node_id}' points to missing node '{next_node_id}'",
                    )


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
