"""
WhatsApp session and flow state. No business logic; only get/save session, waiting state, reset to root.
Routes must not contain session logic – use this service only.
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Tuple

from app.core.container import get_tenant_service, get_whatsapp_service
from app.helpers.constants import FLOW_MODES_EXPECTING_INPUT
from app.helpers.phone_util import PhoneUtil


def get_session(tenant: str, phone: str) -> Dict[str, Any]:
    """Retrieve WhatsApp session for a user."""
    if not phone:
        return {"last_node": None, "ctx": {}}
    cc = get_tenant_service()._get_tenant_country_code(tenant)
    s_phone = PhoneUtil.normalize_e164_input(phone, cc) or phone
    session = get_whatsapp_service().get_whatsapp_session(tenant, s_phone) or {}
    if not isinstance(session.get("ctx"), dict):
        session["ctx"] = {}
    return session


def save_session(tenant: str, phone: str, session: Dict[str, Any], ttl_minutes: int = 30) -> None:
    """Persist WhatsApp session for a user."""
    if not phone:
        return
    cc = get_tenant_service()._get_tenant_country_code(tenant)
    s_phone = PhoneUtil.normalize_e164_input(phone, cc) or phone
    existing = get_whatsapp_service().get_whatsapp_session(tenant, s_phone) or {}
    existing_ctx = existing.get("ctx") or {}
    data = {
        "last_node": session.get("last_node") if "last_node" in session else existing.get("last_node"),
        "ctx": session.get("ctx") if "ctx" in session else existing_ctx,
    }
    get_whatsapp_service().upsert_whatsapp_session(tenant, s_phone, data, ttl_minutes=ttl_minutes)


def set_waiting_store_input(tenant: str, phone: str, action_id: str, param_key: str) -> None:
    """Set session so next user message is passed as follow-up input to the given store action."""
    if not phone:
        return
    session = get_session(tenant, phone)
    ctx = dict(session.get("ctx") or {})
    ctx["waiting_for_store_input"] = {"action_id": action_id, "param_key": param_key}
    save_session(tenant, phone, {"ctx": ctx})


def set_waiting_action_input(tenant: str, phone: str, action_id: str, param_key: str = "input") -> None:
    """Set session so next user message is passed as follow-up input to this action."""
    if not phone:
        return
    session = get_session(tenant, phone)
    ctx = dict(session.get("ctx") or {})
    ctx["waiting_for_action_input"] = {"action_id": action_id, "param_key": param_key}
    save_session(tenant, phone, {"ctx": ctx})


def is_waiting_for_any_input(session: dict) -> bool:
    """True if the menu action requires user input and is waiting for it."""
    ctx = session.get("ctx") or {}
    for key in ("waiting_for_store_input", "waiting_for_action_input"):
        w = ctx.get(key)
        if isinstance(w, dict) and w.get("action_id"):
            return True
    if ctx.get("workflow_id"):
        return True
    if ctx.get("mode") in FLOW_MODES_EXPECTING_INPUT:
        return True
    return False


def get_waiting_action_payload(session: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (waiting_key, action_id, param_key) if session is waiting for action input, else (None, None, None)."""
    ctx = session.get("ctx") or {}
    for key in ("waiting_for_store_input", "waiting_for_action_input"):
        w = ctx.get(key)
        if isinstance(w, dict) and w.get("action_id"):
            return key, w.get("action_id"), w.get("param_key", "input")
    return None, None, None


def reset_session_to_root(tenant: str, phone: str, tree: Dict[str, Any]) -> None:
    """Reset user session to the menu root."""
    if not phone:
        return
    cc = get_tenant_service()._get_tenant_country_code(tenant)
    s_phone = PhoneUtil.normalize_e164_input(phone, cc) or phone
    get_whatsapp_service().upsert_whatsapp_session(
        tenant, s_phone,
        {"last_node": tree.get("root"), "ctx": {}},
        ttl_minutes=30,
    )
