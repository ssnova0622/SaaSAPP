"""
WhatsApp promotion sends — maps tenant promotion documents to provider calls.

**Extending when Meta adds features**
- Prefer adding structured fields on the promotion doc (e.g. ``cta_url``, ``cta_display_text``)
  and a branch here, *or* a versioned ``whatsapp_payload`` dict built by admin.
- Session messages support: reply buttons, lists, ``cta_url`` (+ header), text, image/video/document.
- **Copy offer code** + mixed CTAs in *one* bubble are typically **approved marketing templates**
  (see Meta coupon templates). Put the code in the message body and use ``cta_url`` for “Shop Now”,
  or send a template message in a future ``interactive_type == "template"`` branch.

See: https://developers.facebook.com/docs/whatsapp/cloud-api/messages/interactive-cta-url-messages
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.core.messaging_service import Messaging


def get_cta_entries(promo: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return normalized CTA rows with non-empty ``url``. Falls back to legacy ``cta_url`` fields."""
    raw = promo.get("cta_entries")
    out: List[Dict[str, Any]] = []
    if isinstance(raw, list):
        for i, e in enumerate(raw):
            if not isinstance(e, dict):
                continue
            url = (e.get("url") or "").strip()
            if not url:
                continue
            label = (e.get("display_text") or e.get("title") or "Link").strip() or "Link"
            eid = str(e.get("id") or f"cta_{i + 1}").strip()
            out.append({"id": eid, "display_text": label, "url": url})
    if out:
        return out
    u = (promo.get("cta_url") or "").strip()
    if u:
        label = (promo.get("cta_display_text") or "Open").strip() or "Open"
        return [{"id": "cta_1", "display_text": label, "url": u}]
    return []


def cta_append_urls_to_body_enabled(promo: Dict[str, Any]) -> bool:
    """Default ``True`` when missing (older promotions)."""
    if "cta_append_urls_to_body" not in promo:
        return True
    return bool(promo.get("cta_append_urls_to_body"))


def append_cta_urls_to_message_text(message: str, promo: Dict[str, Any], *, force: bool = False) -> str:
    """Append ``Label: url`` lines for each CTA entry when enabled (or when ``force``)."""
    if (promo.get("interactive_type") or "").strip().lower() != "cta_url":
        return message
    if not force and not cta_append_urls_to_body_enabled(promo):
        return message
    entries = get_cta_entries(promo)
    if not entries:
        return message
    lines = [f"{e['display_text']}: {e['url']}" for e in entries]
    block = "\n".join(lines)
    low = (message or "").lower()
    if all((e["url"].lower() in low) for e in entries):
        return message
    missing = [e for e in entries if e["url"] not in message]
    if not missing:
        return message
    extra = "\n".join(f"{e['display_text']}: {e['url']}" for e in missing)
    return f"{message.rstrip()}\n\n{extra}"


def _first_media_header(attachments: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for a in attachments or []:
        t = (a.get("type") or "").lower()
        url = (a.get("url") or "").strip()
        if not url:
            continue
        if t == "image":
            return {"type": "image", "image": {"link": url}}
        if t == "video":
            return {"type": "video", "video": {"link": url}}
        if t == "document":
            return {"type": "document", "document": {"link": url}}
    return None


def _truncate(s: str, max_len: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


def build_cta_url_interactive(promo: Dict[str, Any], body_text: str) -> Dict[str, Any]:
    """Build Meta ``interactive`` object with ``type: cta_url``."""
    entries = get_cta_entries(promo)
    primary = entries[0] if entries else {}
    url = (primary.get("url") or promo.get("cta_url") or "").strip()
    display = _truncate(primary.get("display_text") or promo.get("cta_display_text") or "Open", 20)
    body = _truncate(body_text, 1024)
    out: Dict[str, Any] = {
        "type": "cta_url",
        "body": {"text": body},
        "action": {
            "name": "cta_url",
            "parameters": {
                "display_text": display,
                "url": url,
            },
        },
    }
    footer = (promo.get("cta_footer") or "").strip()
    if footer:
        out["footer"] = {"text": _truncate(footer, 60)}
    att = promo.get("attachments") or []
    header = _first_media_header(att)
    if header:
        out["header"] = header
    return out


def append_offer_code_line(message: str, promo: Dict[str, Any]) -> str:
    code = (promo.get("offer_code") or "").strip()
    if not code:
        return message
    line = f"Use code: {code}"
    if code.lower() in (message or "").lower():
        return message
    return f"{message.rstrip()}\n\n{line}"


def send_promotion_whatsapp(
    tenant: str,
    to_phone: str,
    promo: Dict[str, Any],
    message_with_links: str,
) -> None:
    """
    Dispatch one WhatsApp promotion payload for ``tenant`` to ``to_phone``.

    ``promo`` is the Mongo document (or dict with same keys).
    """
    itype = (promo.get("interactive_type") or "").strip().lower()
    attachments: List[Dict[str, Any]] = list(promo.get("attachments") or [])
    buttons: List[Dict[str, Any]] = list(promo.get("buttons") or [])
    list_sections: List[Dict[str, Any]] = list(promo.get("list_sections") or [])

    body_text = append_offer_code_line(message_with_links, promo)

    if itype == "cta_url":
        _cta_entries = get_cta_entries(promo)
        url = ((_cta_entries[0].get("url") if _cta_entries else "") or (promo.get("cta_url") or "")).strip()
        if not url:
            Messaging.send_whatsapp_text(to_phone, body_text, tenant=tenant)
            return
        interactive = build_cta_url_interactive(promo, body_text)
        Messaging.send_whatsapp_interactive(to_phone, interactive, tenant=tenant)
        return

    if itype == "button" and buttons:
        Messaging.send_whatsapp_interactive(
            to_phone,
            {
                "type": "button",
                "body": {"text": body_text},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": b["id"], "title": _truncate(b.get("title") or "OK", 20)}}
                        for b in buttons
                    ]
                },
            },
            tenant=tenant,
        )
        return

    if itype == "list" and list_sections:
        Messaging.send_whatsapp_interactive(
            to_phone,
            {
                "type": "list",
                "body": {"text": body_text},
                "action": {"button": "View Options", "sections": list_sections},
            },
            tenant=tenant,
        )
        return

    doc_att = next((a for a in attachments if (a.get("type") or "").lower() == "document"), None)
    media_att = next((a for a in attachments if (a.get("type") or "").lower() in ("image", "video")), None)

    if doc_att and (doc_att.get("url") or "").strip():
        Messaging.send_whatsapp_document(
            to_phone,
            doc_att["url"].strip(),
            body_text or None,
            tenant=tenant,
        )
        return

    if media_att and (media_att.get("url") or "").strip():
        Messaging.send_whatsapp_media(to_phone, media_att["url"].strip(), body_text, tenant=tenant)
        return

    Messaging.send_whatsapp_text(to_phone, body_text, tenant=tenant)
