from __future__ import annotations
from typing import Optional, Sequence, Dict, Any
import logging

from settings import env

try:
    from twilio.rest import Client as TwilioClient  # type: ignore
except Exception:  # pragma: no cover - twilio optional at dev
    TwilioClient = None  # type: ignore

import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

logger = logging.getLogger(__name__)


def _whatsapp_uses_meta_api(provider: Optional[str]) -> bool:
    p = (provider or "").strip().lower()
    return p in ("meta", "meta_cloud")


class Messaging:
    @staticmethod
    def get_config(tenant: str) -> Dict[str, Any]:
        from app.core.container import get_tenant_service
        settings = get_tenant_service().get_tenant_settings(tenant) or {}
        return settings

    @classmethod
    def send_whatsapp_text(cls, to_phone: str, text: str, tenant: Optional[str] = None) -> None:
        wa_cfg = {}
        if tenant:
            wa_cfg = cls.get_config(tenant).get("whatsapp_config") or {}

        # Fallback to env if tenant config is missing crucial parts or if no tenant context
        enabled = wa_cfg.get("enabled", env.bool("TWILIO_ENABLED", True))
        provider = wa_cfg.get("provider", "twilio")

        if not enabled:
            logger.info("[NO-OP] [%s] WhatsApp to %s: %s", tenant or "GLOBAL", to_phone, text)
            return

        # Meta Cloud API
        if _whatsapp_uses_meta_api(provider):
            token = wa_cfg.get("access_token") or env.str("META_ACCESS_TOKEN", "")
            phone_id = wa_cfg.get("phone_number_id") or env.str("META_PHONE_NUMBER_ID", "")
            if not token or not phone_id:
                logger.error("Meta Cloud API credentials missing")
                return

            # Normalize to_phone for Meta (digits only, no '+' or 'whatsapp:')
            clean_phone = "".join(filter(str.isdigit, to_phone))

            url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": clean_phone,
                "type": "text",
                "text": {"body": text},
            }
            resp = requests.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                logger.error("Meta Cloud API error: %s", resp.text)
                raise Exception(f"Meta Cloud API error: {resp.status_code} - {resp.text}")
            return

        # Twilio (Default)
        from_number = wa_cfg.get("from_number") or env.str("TWILIO_WHATSAPP_FROM", "whatsapp:+14155550123")
        sid = wa_cfg.get("account_sid") or env.str("TWILIO_ACCOUNT_SID", "")
        token = wa_cfg.get("auth_token") or env.str("TWILIO_AUTH_TOKEN", "")

        if sid and not sid.startswith("AC"):
            logger.warning("Twilio account_sid for tenant %s likely invalid: %s (should start with AC)", tenant, sid)

        if TwilioClient is None:
            logger.error("Twilio SDK not available")
            return

        client = TwilioClient(sid, token)
        try:
            client.messages.create(
                body=text,
                from_=from_number,
                to=f"whatsapp:{to_phone}" if not to_phone.startswith("whatsapp:") else to_phone,
            )
        except Exception as e:
            if sid and not sid.startswith("AC") and "401" in str(e):
                logger.error(
                    "Twilio Authentication Error for tenant %s. The account_sid '%s' is likely a Messaging Service SID (starting with HX) instead of an Account SID (starting with AC). Please use your Account SID for authentication.",
                    tenant, sid)
            else:
                logger.error("Twilio error sending text: %s", e)
            raise e

    @classmethod
    def send_whatsapp_media(cls, to_phone: str, media_url: str, caption: Optional[str] = None,
                            tenant: Optional[str] = None) -> None:
        wa_cfg = {}
        if tenant:
            wa_cfg = cls.get_config(tenant).get("whatsapp_config") or {}

        enabled = wa_cfg.get("enabled", env.bool("TWILIO_ENABLED", True))
        provider = wa_cfg.get("provider", "twilio")

        if not enabled:
            logger.info("[NO-OP] [%s] WhatsApp media to %s: %s (%s)", tenant or "GLOBAL", to_phone, media_url, caption)
            return

        # Meta Cloud API
        if _whatsapp_uses_meta_api(provider):
            token = wa_cfg.get("access_token") or env.str("META_ACCESS_TOKEN", "")
            phone_id = wa_cfg.get("phone_number_id") or env.str("META_PHONE_NUMBER_ID", "")
            if not token or not phone_id:
                logger.error("Meta Cloud API credentials missing")
                return

            clean_phone = "".join(filter(str.isdigit, to_phone))
            url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            # Simple media message using image or video type
            # NOTE: Meta API distinguishes between image and video. 
            # We'll guess based on extension or use a generic approach.
            is_video = any(media_url.lower().endswith(ext) for ext in [".mp4", ".mov", ".avi"])
            payload = {
                "messaging_product": "whatsapp",
                "to": clean_phone,
                "type": "video" if is_video else "image",
                "video" if is_video else "image": {
                    "link": media_url,
                    "caption": caption or ""
                },
            }
            resp = requests.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                logger.error("Meta Cloud API error: %s", resp.text)
                raise Exception(f"Meta Cloud API error: {resp.status_code} - {resp.text}")
            return

        # Twilio (Default)
        from_number = wa_cfg.get("from_number") or env.str("TWILIO_WHATSAPP_FROM", "whatsapp:+14155550123")
        sid = wa_cfg.get("account_sid") or env.str("TWILIO_ACCOUNT_SID", "")
        token = wa_cfg.get("auth_token") or env.str("TWILIO_AUTH_TOKEN", "")

        if sid and not sid.startswith("AC"):
            logger.warning("Twilio account_sid for tenant %s likely invalid: %s (should start with AC)", tenant, sid)

        if TwilioClient is None:
            logger.error("Twilio SDK not available")
            return

        client = TwilioClient(sid, token)
        try:
            client.messages.create(
                media_url=[media_url],
                body=caption or "",
                from_=from_number,
                to=f"whatsapp:{to_phone}" if not to_phone.startswith("whatsapp:") else to_phone,
            )
        except Exception as e:
            if sid and not sid.startswith("AC") and "401" in str(e):
                logger.error(
                    "Twilio Authentication Error for tenant %s. The account_sid '%s' is likely a Messaging Service SID (starting with HX) instead of an Account SID (starting with AC). Please use your Account SID for authentication.",
                    tenant, sid)
            else:
                logger.error("Twilio error sending media: %s", e)
            raise e

    @classmethod
    def send_whatsapp_document(
        cls,
        to_phone: str,
        document_url: str,
        caption: Optional[str] = None,
        filename: Optional[str] = None,
        tenant: Optional[str] = None,
    ) -> None:
        """Send a document (e.g. PDF) via WhatsApp. URL must be publicly reachable (e.g. presigned S3)."""
        wa_cfg = {}
        if tenant:
            wa_cfg = cls.get_config(tenant).get("whatsapp_config") or {}

        enabled = wa_cfg.get("enabled", env.bool("TWILIO_ENABLED", True))
        provider = wa_cfg.get("provider", "twilio")

        if not enabled:
            logger.info(
                "[NO-OP] [%s] WhatsApp document to %s: %s",
                tenant or "GLOBAL",
                to_phone,
                document_url,
            )
            return

        if _whatsapp_uses_meta_api(provider):
            token = wa_cfg.get("access_token") or env.str("META_ACCESS_TOKEN", "")
            phone_id = wa_cfg.get("phone_number_id") or env.str("META_PHONE_NUMBER_ID", "")
            if not token or not phone_id:
                logger.error("Meta Cloud API credentials missing")
                return

            clean_phone = "".join(filter(str.isdigit, to_phone))
            url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            doc_block: Dict[str, Any] = {
                "link": document_url,
                "caption": (caption or "")[:1024],
            }
            if filename:
                doc_block["filename"] = filename
            payload = {
                "messaging_product": "whatsapp",
                "to": clean_phone,
                "type": "document",
                "document": doc_block,
            }
            resp = requests.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                logger.error("Meta Cloud API error: %s", resp.text)
                raise Exception(f"Meta Cloud API error: {resp.status_code} - {resp.text}")
            return

        from_number = wa_cfg.get("from_number") or env.str("TWILIO_WHATSAPP_FROM", "whatsapp:+14155550123")
        sid = wa_cfg.get("account_sid") or env.str("TWILIO_ACCOUNT_SID", "")
        token = wa_cfg.get("auth_token") or env.str("TWILIO_AUTH_TOKEN", "")

        if sid and not sid.startswith("AC"):
            logger.warning("Twilio account_sid for tenant %s likely invalid: %s (should start with AC)", tenant, sid)

        if TwilioClient is None:
            logger.error("Twilio SDK not available")
            return

        client = TwilioClient(sid, token)
        try:
            client.messages.create(
                media_url=[document_url],
                body=caption or "",
                from_=from_number,
                to=f"whatsapp:{to_phone}" if not to_phone.startswith("whatsapp:") else to_phone,
            )
        except Exception as e:
            if sid and not sid.startswith("AC") and "401" in str(e):
                logger.error(
                    "Twilio Authentication Error for tenant %s. The account_sid '%s' is likely a Messaging Service SID (starting with HX) instead of an Account SID (starting with AC). Please use your Account SID for authentication.",
                    tenant,
                    sid,
                )
            else:
                logger.error("Twilio error sending document: %s", e)
            raise e

    @classmethod
    def send_whatsapp_interactive(cls, to_phone: str, interactive_payload: Dict[str, Any],
                                  tenant: Optional[str] = None) -> None:
        wa_cfg = {}
        if tenant:
            wa_cfg = cls.get_config(tenant).get("whatsapp_config") or {}

        enabled = wa_cfg.get("enabled", env.bool("TWILIO_ENABLED", True))
        provider = wa_cfg.get("provider", "twilio")

        if not enabled:
            logger.info("[NO-OP] [%s] WhatsApp interactive to %s: %s", tenant or "GLOBAL", to_phone,
                        interactive_payload)
            return

        if _whatsapp_uses_meta_api(provider):
            token = wa_cfg.get("access_token") or env.str("META_ACCESS_TOKEN", "")
            phone_id = wa_cfg.get("phone_number_id") or env.str("META_PHONE_NUMBER_ID", "")
            if not token or not phone_id:
                logger.error("Meta Cloud API credentials missing")
                return

            clean_phone = "".join(filter(str.isdigit, to_phone))
            url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": clean_phone,
                "type": "interactive",
                "interactive": interactive_payload,
            }
            resp = requests.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                logger.error("Meta Cloud API error: %s", resp.text)
                raise Exception(f"Meta Cloud API error: {resp.status_code} - {resp.text}")
            return

        # Fallback to text for other providers (align with core.messaging_service)
        body = interactive_payload.get("body", {}).get("text") or "Interactive message"
        itype = interactive_payload.get("type")
        if itype == "cta_url":
            params = (interactive_payload.get("action") or {}).get("parameters") or {}
            u = (params.get("url") or "").strip()
            if u:
                body = f"{body.rstrip()}\n\n{u}"
        elif itype == "button":
            btns = interactive_payload.get("action", {}).get("buttons", [])
            btn_labels = [b.get("reply", {}).get("title") for b in btns]
            body += "\n\nOptions: " + ", ".join(btn_labels)
        elif itype == "list":
            btn_label = interactive_payload.get("action", {}).get("button") or "Options"
            body += f"\n\nReply '{btn_label}' to see options"

        cls.send_whatsapp_text(to_phone, body, tenant=tenant)

    @classmethod
    def send_email(
            cls,
            to_email: str,
            subject: str,
            text_body: str,
            html_body: Optional[str] = None,
            attachments: Optional[Sequence[tuple[str, bytes, str]]] = None,  # (filename, data, mime)
            tenant: Optional[str] = None,
    ) -> None:
        smtp_cfg = {}
        if tenant:
            smtp_cfg = cls.get_config(tenant).get("smtp_config") or {}

        enabled = smtp_cfg.get("enabled", env.bool("SMTP_ENABLED", False))
        if not enabled:
            logger.info("[NO-OP] [%s] Email to %s: %s | %s", tenant or "GLOBAL", to_email, subject, text_body[:120])
            return

        host = smtp_cfg.get("host") or env.str("SMTP_HOST", "")
        port = smtp_cfg.get("port") or env.int("SMTP_PORT", 587)
        user = smtp_cfg.get("user") or env.str("SMTP_USER", "")
        password = smtp_cfg.get("password") or env.str("SMTP_PASSWORD", "")
        sender = smtp_cfg.get("from") or smtp_cfg.get("sender") or env.str("SMTP_FROM", user or "noreply@example.com")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_email

        msg.attach(MIMEText(text_body or "", "plain"))
        if html_body:
            msg.attach(MIMEText(html_body, "html"))
        if attachments:
            for filename, data, mime in attachments:
                part = MIMEApplication(data, _subtype=(mime.split("/")[1] if "/" in mime else "octet-stream"))
                part.add_header('Content-Disposition', 'attachment', filename=filename)
                msg.attach(part)

        with smtplib.SMTP(host, port) as server:
            server.starttls()
            if user:
                server.login(user, password)
            server.sendmail(sender, [to_email], msg.as_string())
