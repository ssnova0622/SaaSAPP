"""
WhatsApp webhook payload parsing. Used by routers to extract (phone, to_num, body, choice_id) from raw payloads.
No HTTP or request handling here; pure data extraction.
"""
from __future__ import annotations

from typing import Any, Dict, Tuple


def extract_meta_webhook_payload(data: Dict[str, Any]) -> Tuple[str, str, str, Any]:
    """
    Extract (from_phone, to_phone, body_text, interactive_choice_id) from Meta Cloud API or flattened payload.
    Returns ("", "", "", None) if nothing found.
    """
    phone = str(data.get("from") or data.get("phone") or "").strip()
    to_num = str(data.get("to") or data.get("to_number") or "").strip()
    body = data.get("body") or data.get("message")
    interactive = data.get("interactive") or {}
    choice_id = None
    if isinstance(interactive, dict):
        reply = interactive.get("button_reply") or interactive.get("list_reply") or {}
        choice_id = reply.get("id")

    if not phone or body is None:
        entries = data.get("entry") or []
        for entry in entries[:1]:
            changes = entry.get("changes") or []
            for change in changes[:1]:
                value = change.get("value") or {}
                if not phone:
                    contacts = value.get("contacts") or []
                    if contacts:
                        phone = str(contacts[0].get("wa_id") or "").strip()
                if not phone:
                    msgs = value.get("messages") or []
                    for msg in msgs[:1]:
                        phone = str(msg.get("from") or "").strip()
                        if body is None and msg.get("text"):
                            body = (msg.get("text") or {}).get("body") or ""
                        if choice_id is None and msg.get("interactive"):
                            ir = (msg.get("interactive") or {}).get("button_reply") or (
                                msg.get("interactive") or {}
                            ).get("list_reply") or {}
                            choice_id = ir.get("id")
                        break
                if not to_num:
                    to_num = str(value.get("metadata", {}).get("display_phone_number") or "").strip()
                break
    return (phone or "", to_num or "", body if body is not None else "", choice_id)


def extract_twilio_webhook_params(params: Dict[str, Any]) -> Tuple[str, str, str]:
    """Extract (from_num, to_num, body) from Twilio form or JSON params."""
    from_num = str(params.get("From") or "").strip()
    to_num = str(params.get("To") or "").strip()
    body = str(params.get("Body") or "").strip()
    return (from_num, to_num, body)


def parse_bot_next_body(body: Dict[str, Any]) -> Tuple[str, str, str, str, Any]:
    """Extract (phone, user_input, menu_id, locale, node) from bot next-step JSON body."""
    phone = str(body.get("phone") or body.get("from") or "").strip()
    user_input = str(body.get("input") or "").strip()
    menu_id = str(body.get("menu_id") or "welcome_message").strip()
    locale = str(body.get("locale") or "en").strip()
    node = body.get("node")
    return (phone, user_input, menu_id, locale, node)
