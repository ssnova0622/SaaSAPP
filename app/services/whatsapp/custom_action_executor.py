"""Execute tenant custom WhatsApp actions (custom.{action_id})."""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Optional

from app.core.container import get_whatsapp_service
from app.services.whatsapp.custom_action_service import custom_action_runtime_id
from app.services.whatsapp.message_render_service import (
    build_tenant_render_context,
    render_message_template,
)
from app.services.whatsapp.session_flow_service import get_session

RunActionFn = Callable[..., Awaitable[str]]


def is_custom_action_id(action_id: str) -> bool:
    return str(action_id or "").strip().lower().startswith("custom.")


def parse_custom_action_id(action_id: str) -> Optional[str]:
    raw = str(action_id or "").strip().lower()
    if not raw.startswith("custom."):
        return None
    aid = raw[7:].strip()
    return aid or None


async def run_custom_action(
    tenant: str,
    action_id: str,
    params: Dict[str, Any],
    locale: str,
    *,
    run_action: RunActionFn,
) -> str:
    """Resolve and run a tenant custom action by runtime id custom.{slug}."""
    slug = parse_custom_action_id(action_id)
    if not slug:
        return ""
    doc = get_whatsapp_service().get_tenant_whatsapp_action(tenant, slug)
    if not doc or not doc.get("enabled", True):
        return "This action is not available."

    phone = str(params.get("phone") or "")
    session = get_session(tenant, phone) if phone else {}
    ctx = build_tenant_render_context(
        tenant, phone=phone, session_ctx=session.get("ctx") or {}
    )

    atype = str(doc.get("action_type") or "static_text").lower()
    prefix = render_message_template(str(doc.get("text") or ""), ctx) if doc.get("text") else ""

    if atype == "static_text":
        return prefix or " "

    if atype == "workflow":
        wf_id = str(doc.get("workflow_id") or "").strip()
        if not wf_id:
            return "Workflow action is not configured."
        body = await run_action(tenant, f"workflow.{wf_id}", {**params, "phone": phone}, locale)
        if prefix and body:
            return f"{prefix}\n\n{body}"
        return body or prefix or " "

    if atype == "predefined":
        sys_id = str(doc.get("system_action_id") or "").strip()
        if not sys_id:
            return "Predefined action is not configured."
        merged = {**(doc.get("params") or {}), **params, "phone": phone}
        body = await run_action(tenant, sys_id, merged, locale)
        if prefix and body:
            return f"{prefix}\n\n{body}"
        return body or prefix or " "

    return "Unsupported custom action type."


def custom_action_catalog_entry(doc: Dict[str, Any]) -> Dict[str, Any]:
    aid = str(doc.get("action_id") or "")
    return {
        "id": custom_action_runtime_id(aid),
        "label": f"{doc.get('name') or aid} (custom)",
        "module": "custom",
        "requires_caps": [],
        "action_type": doc.get("action_type"),
        "custom_action_id": aid,
    }
