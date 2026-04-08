"""
WhatsApp routes: API endpoints only. No business logic.
- Parse request → call service (inbound_handler, action_registry, webhook_parsers) → return response.
"""
from __future__ import annotations
from typing import Any, Dict, Optional
import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Body, Header, Request, Response

from app.routers.deps import get_current_user
from app.core.container import get_tenant_service, get_whatsapp_service
from app.services.whatsapp.pipeline.inbound_pipeline import handle_incoming
from app.services.whatsapp.webhook_parsers import (
    extract_meta_webhook_payload,
    extract_twilio_webhook_params,
    parse_bot_next_body,
)
from app.services.whatsapp.usecases.action_registry import get_all_workflow_actions
from app.services.whatsapp.workflow.workflow_engine import WorkflowEngine
from app.helpers.phone_util import PhoneUtil
from app.helpers.constants_roles import ROLE_SUPER_ADMIN, ROLE_TENANT_ADMIN

router = APIRouter()
logger = logging.getLogger(__name__)

_CDATA_END = re.compile(r"]]>")


def _twilio_reply_xml(message: str) -> str:
    """TwiML body safe for &, newlines, unicode (CDATA)."""
    text = message if message is not None else ""
    safe = _CDATA_END.sub("]] ]]", text)
    return f"<Response><Message><![CDATA[{safe}]]></Message></Response>"


@router.get("/whatsapp/actions", tags=["Admin"])
def list_whatsapp_actions(tenant: Optional[str] = None) -> Dict[str, Any]:
    """Return available system actions for menu builder. Optional tenant filters by capabilities."""
    context: Dict[str, Any] = {}
    if tenant:
        t = get_tenant_service().get_tenant_settings(tenant) or {}
        context = {
            "tenant": tenant,
            "category": t.get("category"),
            "modules": t.get("modules") or [],
            "capabilities": t.get("capabilities") or [],
        }
        items = WorkflowEngine.list_whatsapp_menu_items(tenant)
    else:
        items = [
            {"id": a.action_code, "label": a.label, "module": a.module or "core", "requires_caps": a.requires_caps or []}
            for a in get_all_workflow_actions()
        ]
    return {"items": items, "context": context, "total": len(items)}


@router.post("/bot/whatsapp/next", tags=["Admin"])
async def bot_next_step(
        request: Request,
        x_tenant: Optional[str] = Header(None, alias="X-Tenant"),
        user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Internal Bot API: parse body, resolve tenant, normalize phone, call handle_incoming."""
    user_role = str(user.get("role")).lower()
    if user_role != ROLE_SUPER_ADMIN:
        # Tenant admins may test the bot only for their own tenant
        if user_role != ROLE_TENANT_ADMIN or (x_tenant and x_tenant != user.get("tenant")):
            raise HTTPException(status_code=403, detail="Access denied: can only test your own tenant's bot")

    try:
        body = json.loads((await request.body()).decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    phone, user_input, menu_id, locale, node = parse_bot_next_body(body)
    tenant = x_tenant or get_tenant_service().resolve_tenant_by_whatsapp_number(phone)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    cc = get_tenant_service()._get_tenant_country_code(tenant)
    phone = PhoneUtil.normalize_e164_input(phone, cc)
    if not phone:
        raise HTTPException(status_code=400, detail="Invalid phone number")

    result = await handle_incoming(
        tenant, phone, user_input, locale,
        menu_id=menu_id,
        client_node=node,
    )
    return {"reply": result["reply"], "node": result["node"]}


@router.post("/integrations/twilio/whatsapp/webhook")
async def twilio_whatsapp_webhook(request: Request) -> Response:
    """Twilio webhook: parse form/json → resolve tenant → handle_incoming → XML response."""
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/x-www-form-urlencoded" in content_type:
        params = dict(await request.form())
    else:
        try:
            params = json.loads((await request.body()).decode("utf-8"))
        except Exception as e:
            logger.warning("Twilio webhook body parse failed: %s", e)
            params = {}

    from_num, to_num, body = extract_twilio_webhook_params(params)
    tenant = get_tenant_service().resolve_tenant_by_whatsapp_number(to_num)
    if not tenant:
        return Response(
            content="<Response><Message>Unknown number</Message></Response>",
            media_type="application/xml",
        )

    try:
        cc = get_tenant_service()._get_tenant_country_code(tenant)
        from_num = PhoneUtil.normalize_e164_input(from_num, cc) or from_num
    except Exception:
        pass

    try:
        get_whatsapp_service().increment_whatsapp_inbound(tenant)
    except Exception:
        pass

    result = await handle_incoming(tenant, from_num, body, "en")
    reply = result.get("reply") or ""
    return Response(
        content=_twilio_reply_xml(reply),
        media_type="application/xml",
    )


@router.post("/integrations/meta/whatsapp/webhook")
async def meta_whatsapp_webhook(data: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Meta Cloud API webhook: parse payload → resolve tenant → handle_incoming."""
    phone, to_num, body_text, choice_id = extract_meta_webhook_payload(data)
    if not phone:
        phone = str(data.get("from") or data.get("phone") or "").strip()
    if not to_num:
        to_num = str(data.get("to") or data.get("to_number") or "").strip()

    user_input = str(choice_id or body_text or "").strip()
    tenant = get_tenant_service().resolve_tenant_by_whatsapp_number(to_num)
    if not tenant:
        return {"error": "Unknown tenant"}

    try:
        get_whatsapp_service().increment_whatsapp_inbound(tenant)
    except Exception:
        pass

    result = await handle_incoming(tenant, phone, user_input, "en")
    return {"reply": result.get("reply") or ""}
