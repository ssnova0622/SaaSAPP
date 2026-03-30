"""
WhatsApp keyword triggers: evaluate inbound text against configured triggers, execute matched action.
Routes call evaluate_triggers then execute_trigger_action; no trigger logic in routes.
"""
from __future__ import annotations
import re
import logging
from typing import Any, Callable, Dict, List, Optional

from app.core.container import get_tenant_service, get_whatsapp_service
from app.services.whatsapp.menu_tree_service import find_node, render_submenu
from app.services.core import message_templates as msg_tpl

logger = logging.getLogger(__name__)

# Split user-entered alternatives: comma, pipe, or newline (and normalize whitespace).
_MATCH_VALUE_SPLIT = re.compile(r"[\n\r|,\u2022\u00b7]+")

def _split_match_alternatives(fragment: str) -> List[str]:
    """Split one string into trimmed non-empty tokens (multi-delimiter)."""
    return [p.strip() for p in _MATCH_VALUE_SPLIT.split(fragment) if p.strip()]

def _expand_match_values(match_val: Any) -> List[str]:
    """
    All alternatives for exact / prefix / contains, lowercased and de-duplicated.
    Accepts a string or list of strings; each piece may use | , or newlines inside it.
    """
    tokens: List[str] = []
    if match_val is None:
        return tokens
    if isinstance(match_val, list):
        for item in match_val:
            tokens.extend(_split_match_alternatives(str(item)))
    else:
        tokens.extend(_split_match_alternatives(str(match_val)))
    seen: set[str] = set()
    out: List[str] = []
    for t in tokens:
        low = t.lower()
        if low and low not in seen:
            seen.add(low)
            out.append(low)
    return out


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

        is_match = False
        if match_type in ("exact", "prefix", "contains"):
            vals_to_check = _expand_match_values(match_val)
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


def _missing_invoke_action_reply(tenant: str, menu_id: str) -> str:
    """User-visible hint when invoke_action has no action_id / misconfigured."""
    base = (
        "This keyword should run an action, but none is configured. "
        "Open Admin → WhatsApp → Triggers, edit this trigger, set Action kind to *invoke_action*, "
        "and choose an action or workflow from the list."
    )
    tpl = msg_tpl.get_message(tenant, "wa_trigger_invoke_not_configured")
    return (tpl or "").strip() or base


async def execute_trigger_action(
    tenant: str,
    action: Dict[str, Any],
    locale: str,
    phone: str = "",
    run_action: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    """
    Execute a matched trigger action. Returns {"reply": str, "node": str|None}.
    Never raises HTTPException — inbound pipeline must always get a user-safe reply.
    """
    kind = str(action.get("kind") or "").lower()
    action_id = str(action.get("action_id") or "").strip()
    menu_id = str(action.get("menu_id") or "").strip() or "welcome_message"
    node_id = str(action.get("node_id") or "").strip()

    if kind == "static_text":
        text = action.get("text") or ""
        if isinstance(text, dict):
            text = text.get(locale) or text.get("en") or next(iter(text.values()), "")
        out = str(text).strip()
        if not out:
            logger.warning("static_text trigger matched but text is empty tenant=%s", tenant)
        return {"reply": out or msg_tpl.get_message(tenant, "whatsapp_processing") or " ", "node": None}

    if kind == "invoke_action":
        if action_id:
            if not run_action:
                return {"reply": msg_tpl.get_message(tenant, "whatsapp_done"), "node": None}
            try:
                reply = await run_action(tenant, action_id, {"phone": phone}, locale)
            except Exception:
                logger.exception(
                    "trigger invoke_action run failed tenant=%s action_id=%s", tenant, action_id
                )
                return {
                    "reply": msg_tpl.get_message(tenant, "whatsapp_processing")
                    or "That action could not run. Please try again or use the menu.",
                    "node": None,
                }
            return {"reply": reply or msg_tpl.get_message(tenant, "whatsapp_done"), "node": None}

        # Legacy: invoke_action with menu_id/node_id only (no action_id)
        menu_doc = get_whatsapp_service().get_whatsapp_menu(tenant, menu_id, status="published")
        if not menu_doc:
            return {
                "reply": _missing_invoke_action_reply(tenant, menu_id)
                + f' (Menu "{menu_id}" is not published.)',
                "node": None,
            }
        tree = menu_doc.get("tree") or {}
        target_id = node_id or tree.get("root")
        node = find_node(tree, target_id)
        if not node:
            return {
                "reply": _missing_invoke_action_reply(tenant, menu_id)
                + " (Menu node missing — check trigger menu/node.)",
                "node": None,
            }
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
            "reply": render_submenu(node, locale)
            if node.get("type") == "submenu"
            else msg_tpl.get_message(tenant, "whatsapp_processing"),
            "node": target_id,
        }

    menu_doc = get_whatsapp_service().get_whatsapp_menu(tenant, menu_id, status="published")
    if not menu_doc:
        return {
            "reply": f'No published menu "{menu_id}". Publish a menu under Admin → WhatsApp → Menus.',
            "node": None,
        }

    tree = menu_doc.get("tree") or {}
    target_id = node_id or tree.get("root")
    node = find_node(tree, target_id)

    if not node:
        return {
            "reply": f'Menu "{menu_id}" has no node "{target_id}". Check the trigger configuration.',
            "node": None,
        }

    if kind in ("render_submenu", "jump_node"):
        if node.get("type") != "submenu":
            reply = node.get("title") or node.get("label") or msg_tpl.get_message(tenant, "whatsapp_processing")
            return {"reply": reply, "node": tree.get("root")}
        return {"reply": render_submenu(node, locale), "node": target_id}

    root_id = tree.get("root")
    root_node = find_node(tree, root_id)
    return {"reply": render_submenu(root_node, locale) if root_node else "", "node": root_id}
