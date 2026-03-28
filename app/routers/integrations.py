from __future__ import annotations
from fastapi import APIRouter, Request
from typing import Dict, Any

from ..core.container import get_professional_service
from .ws import notifier

router = APIRouter()
_ai = None  # AI module removed


@router.post("/integrations/twilio/whatsapp")
async def twilio_whatsapp_webhook(request: Request) -> Dict[str, Any]:
    form = await request.form()
    # Common Twilio WhatsApp fields
    from_id = form.get("WaId") or form.get("From", "").replace("whatsapp:", "")
    body = (form.get("Body") or "").strip()
    tenant = form.get("tenant") or "demo-salon"  # demo default; in prod, map number->tenant

    # Very simple conversational flow (AI removed): basic keyword handling
    intent_text = body.lower()
    if "book" in intent_text or body.isdigit():
        msg = "Please share your preferred time (e.g., 10:30). We will confirm if available."
    elif "list" in intent_text or "who" in intent_text:
        pros = ", ".join([p.name for p in get_professional_service().get_professionals(tenant)]) or "None"
        msg = f"Available professionals: {pros}. Reply 'book' to get time suggestions."
    else:
        msg = "Hi! Reply 'book' to get time suggestions or 'list' to see professionals."

    # In a real integration, you'd send a reply via Twilio API. Here we broadcast to WebSocket clients
    await notifier.broadcast({
        "type": "twilio.message",
        "tenant": tenant,
        "from": from_id,
        "body": body,
        "reply": msg,
    })
    # Respond 200 to Twilio with empty body or simple text
    return {"status": "ok", "reply": msg}
