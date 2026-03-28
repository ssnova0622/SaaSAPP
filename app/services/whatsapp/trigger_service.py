"""
WhatsApp keyword triggers: evaluate inbound text against configured triggers, execute matched action.
Routes call evaluate_triggers then execute_trigger_action; no trigger logic in routes.
"""
from __future__ import annotations
import re
import logging
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException

from app.core.container import get_tenant_service, get_whatsapp_service
from app.services.whatsapp.menu_tree_service import find_node, render_submenu
from app.services.core import message_templates as msg_tpl

logger = logging.getLogger(__name__)


def _tenant_has_caps(tenant: str, required_caps: List[str]) -> bool:
    if not required_caps:
        return True
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    tenant_caps = {str(c).lower() for c in (settings.get("capabilities") or [])}
    return all(str(r).lower() in tenant_caps for r in required_caps)


def evaluate_triggers(tenant: str, text: str, locale: str = "en") -> Optional[Dict[str, Any]]:
    """Evaluate inbound text against configured keyword triggers. Returns matched action dict or None."""
    if not text:
        return None
    norm_text = text.strip().lower()
    if not norm_text:
        return None

    triggers = get_whatsapp_service().fetch_enabled_triggers(tenant)
    for trig in triggers:
        match_cfg = trig.get("match") or {}
        match_type = str(match_cfg.get("type") or "exact").lower()
        match_val = match_cfg.get("value")
        match_locale = str(match_cfg.get("locale") or "").lower()

        if match_locale and match_locale != locale.lower():
            continue

        vals_to_check: List[str] = []
        if isinstance(match_val, list):
            vals_to_check = [str(v).strip().lower() for v in match_val if str(v).strip()]
        else:
            raw_val = str(match_val or "").strip().lower()
            vals_to_check = (
                [p.strip() for p in raw_val.split(",") if p.strip()]
                if "," in raw_val
                else ([raw_val] if raw_val else [])
            )

        is_match = False
        if match_type in ("exact", "prefix", "contains"):
            for val in vals_to_check:
                if not val:
                    continue
                if match_type == "exact" and norm_text == val:
                    is_match = True
                elif match_type == "prefix" and norm_text.startswith(val):
                    is_match = True
                elif match_type == "contains" and val in norm_text:
                    is_match = True
                if is_match:
                    break
        elif match_type == "regex":
            patterns = match_val if isinstance(match_val, list) else [str(match_val)]
            for pat in patterns:
                try:
                    if re.search(str(pat), norm_text, re.IGNORECASE):
                        is_match = True
                        break
                except Exception:
                    continue

        if is_match:
            action = dict(trig.get("action") or {})
            action["source_trigger_id"] = trig.get("trigger_id")
            return action

    return None


async def execute_trigger_action(
    tenant: str,
    action: Dict[str, Any],
    locale: str,
    phone: str = "",
    run_action: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """
    Execute a matched trigger action. Returns {"reply": str, "node": str|None}.
    run_action: async (tenant, action_id, params, locale) -> str; required for kind=invoke_action with action_id.
    """
    kind = str(action.get("kind") or "").lower()
    action_id = str(action.get("action_id") or "").strip()
    menu_id = str(action.get("menu_id") or "welcome_message")
    node_id = str(action.get("node_id") or "")

    if kind == "static_text":
        text = action.get("text") or ""
        if isinstance(text, dict):
            text = text.get(locale) or text.get("en") or next(iter(text.values()), "")
        return {"reply": str(text), "node": None}

    if kind == "invoke_action" and action_id:
        if not run_action:
            return {"reply": msg_tpl.get_message(tenant, "whatsapp_done"), "node": None}
        reply = await run_action(tenant, action_id, {"phone": phone}, locale)
        return {"reply": reply or msg_tpl.get_message(tenant, "whatsapp_done"), "node": None}

    menu_doc = get_whatsapp_service().get_whatsapp_menu(tenant, menu_id, status="published")
    if not menu_doc:
        raise HTTPException(status_code=404, detail="No published menu found for trigger action")

    tree = menu_doc.get("tree") or {}
    target_id = node_id or tree.get("root")
    node = find_node(tree, target_id)

    if not node:
        raise HTTPException(status_code=400, detail="Target menu node not found")

    if kind in ("render_submenu", "jump_node"):
        if node.get("type") != "submenu":
            reply = node.get("title") or node.get("label") or msg_tpl.get_message(tenant, "whatsapp_processing")
            return {"reply": reply, "node": tree.get("root")}
        return {"reply": render_submenu(node, locale), "node": target_id}

    if kind == "invoke_action":
        if node.get("type") == "action":
            required = node.get("requires_caps") or []
            if not _tenant_has_caps(tenant, required):
                return {
                    "reply": msg_tpl.get_message(tenant, "whatsapp_feature_not_available"),
                    "node": tree.get("root"),
                }
            reply = node.get("title") or node.get("label") or msg_tpl.get_message(tenant, "whatsapp_processing")
            return {"reply": reply, "node": tree.get("root")}
        return {
            "reply": render_submenu(node, locale) if node.get("type") == "submenu" else msg_tpl.get_message(tenant, "whatsapp_processing"),
            "node": target_id,
        }

    root_id = tree.get("root")
    root_node = find_node(tree, root_id)
    return {"reply": render_submenu(root_node, locale) if root_node else "", "node": root_id}
