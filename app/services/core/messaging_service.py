# app/services/core/messaging_service.py
from __future__ import annotations
from typing import Any, Dict, Optional, Sequence
import logging
import requests
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from settings import env
from app.core.event_bus import event_bus

try:
    from twilio.rest import Client as TwilioClient
except Exception:
    TwilioClient = None

logger = logging.getLogger(__name__)


class Messaging:
    _initialized = False

    def __init__(self):
        if not Messaging._initialized:
            self._register_event_handlers()
            Messaging._initialized = True

    # ----------------------------------------------------------------------
    # Event Bus Registration
    # ----------------------------------------------------------------------

    def _register_event_handlers(self):
        event_bus.subscribe("send_whatsapp_text", lambda data: self.send_whatsapp_text(**data))
        event_bus.subscribe("send_whatsapp_media", lambda data: self.send_whatsapp_media(**data))
        event_bus.subscribe("send_whatsapp_interactive", lambda data: self.send_whatsapp_interactive(**data))
        event_bus.subscribe("send_email", lambda data: self.send_email(**data))

    # ----------------------------------------------------------------------
    # Config Helpers
    # ----------------------------------------------------------------------

    @staticmethod
    def _tenant_cfg(tenant: Optional[str], key: str) -> Dict[str, Any]:
        if not tenant:
            return {}
        from app.services.core.tenant_service import TenantService
        settings = TenantService.get_tenant_settings(tenant) or {}
        return settings.get(key) or {}

    @staticmethod
    def _whatsapp_uses_meta_api(provider: Optional[str]) -> bool:
        """Admin UI stores Meta as ``meta_cloud``; legacy/env may use ``meta``."""
        p = (provider or "").strip().lower()
        return p in ("meta", "meta_cloud")

    @staticmethod
    def _wa_cfg(tenant: Optional[str]) -> Dict[str, Any]:
        cfg = Messaging._tenant_cfg(tenant, "whatsapp_config")
        return {
            "enabled": cfg.get("enabled", env.bool("TWILIO_ENABLED", True)),
            "provider": cfg.get("provider", "twilio"),
            "from_number": cfg.get("from_number") or env.str("TWILIO_WHATSAPP_FROM", "whatsapp:+14155550123"),
            "sid": cfg.get("account_sid") or env.str("TWILIO_ACCOUNT_SID", ""),
            "token": cfg.get("auth_token") or env.str("TWILIO_AUTH_TOKEN", ""),
            "meta_token": cfg.get("access_token") or env.str("META_ACCESS_TOKEN", ""),
            "meta_phone_id": cfg.get("phone_number_id") or env.str("META_PHONE_NUMBER_ID", ""),
        }

    @staticmethod
    def _smtp_cfg(tenant: Optional[str]) -> Dict[str, Any]:
        cfg = Messaging._tenant_cfg(tenant, "smtp_config")
        return {
            "enabled": cfg.get("enabled", env.bool("SMTP_ENABLED", False)),
            "host": cfg.get("host") or env.str("SMTP_HOST", ""),
            "port": cfg.get("port") or env.int("SMTP_PORT", 587),
            "user": cfg.get("user") or env.str("SMTP_USER", ""),
            "password": cfg.get("password") or env.str("SMTP_PASSWORD", ""),
            "sender": cfg.get("from") or cfg.get("sender") or env.str("SMTP_FROM", cfg.get("user", "")),
        }

    @staticmethod
    def _sms_cfg(tenant: Optional[str]) -> Dict[str, Any]:
        cfg = Messaging._tenant_cfg(tenant, "sms_config")
        return {
            "enabled": bool(cfg.get("enabled", False)) or env.bool("SMS_ENABLED", False),
            "sid": cfg.get("account_sid") or env.str("TWILIO_ACCOUNT_SID", ""),
            "token": cfg.get("auth_token") or env.str("TWILIO_AUTH_TOKEN", ""),
            "from_number": cfg.get("from_number") or env.str("TWILIO_SMS_FROM", ""),
        }

    # ----------------------------------------------------------------------
    # SMS (e.g. login OTP)
    # ----------------------------------------------------------------------

    @classmethod
    def send_sms(cls, to_phone: str, body: str, tenant: Optional[str] = None) -> None:
        """Send SMS via Twilio using tenant's sms_config or env fallbacks."""
        cfg = cls._sms_cfg(tenant)
        if not cfg["enabled"] or not cfg["sid"] or not cfg["token"]:
            logger.info("[NO-OP] [%s] SMS to %s (SMS not configured)", tenant or "GLOBAL", to_phone)
            return
        client = cls._twilio_client(cfg["sid"], cfg["token"])
        if not client:
            logger.warning("Twilio client not available for SMS")
            return
        from_num = cfg["from_number"] or None
        if not from_num:
            logger.warning("Twilio from_number not set; cannot send SMS")
            return
        to_clean = "".join(c for c in to_phone if c.isdigit() or c == "+")
        if not to_clean.startswith("+"):
            to_clean = "+" + to_clean
        try:
            client.messages.create(body=body, from_=from_num, to=to_clean)
        except Exception as e:
            logger.error("Twilio SMS error: %s", e)
            raise

    # ----------------------------------------------------------------------
    # WhatsApp Provider Helpers
    # ----------------------------------------------------------------------

    @staticmethod
    def _normalize_phone_for_meta(phone: str) -> str:
        return "".join(filter(str.isdigit, phone))

    @staticmethod
    def _twilio_client(sid: str, token: str):
        if TwilioClient is None:
            logger.error("Twilio SDK not available")
            return None
        return TwilioClient(sid, token)

    @staticmethod
    def _send_meta_request(phone_id: str, token: str, payload: Dict[str, Any]):
        url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        resp = requests.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.error("Meta Cloud API error: %s", resp.text)
            raise Exception(f"Meta Cloud API error: {resp.status_code} - {resp.text}")

    # ----------------------------------------------------------------------
    # WhatsApp Text
    # ----------------------------------------------------------------------

    @classmethod
    def send_whatsapp_text(cls, to_phone: str, text: str, tenant: Optional[str] = None) -> None:
        cfg = cls._wa_cfg(tenant)
        if not cfg["enabled"]:
            logger.info("[NO-OP] [%s] WhatsApp to %s: %s", tenant or "GLOBAL", to_phone, text)
            return

        if cls._whatsapp_uses_meta_api(cfg.get("provider")):
            clean = cls._normalize_phone_for_meta(to_phone)
            payload = {
                "messaging_product": "whatsapp",
                "to": clean,
                "type": "text",
                "text": {"body": text},
            }
            return cls._send_meta_request(cfg["meta_phone_id"], cfg["meta_token"], payload)

        client = cls._twilio_client(cfg["sid"], cfg["token"])
        if not client:
            return

        try:
            client.messages.create(
                body=text,
                from_=cfg["from_number"],
                to=f"whatsapp:{to_phone}" if not to_phone.startswith("whatsapp:") else to_phone,
            )
        except Exception as e:
            logger.error("Twilio error sending text: %s", e)
            raise

    # ----------------------------------------------------------------------
    # WhatsApp Media
    # ----------------------------------------------------------------------

    @classmethod
    def send_whatsapp_media(cls, to_phone: str, media_url: str, caption: Optional[str] = None,
                            tenant: Optional[str] = None) -> None:
        cfg = cls._wa_cfg(tenant)
        if not cfg["enabled"]:
            logger.info("[NO-OP] [%s] WhatsApp media to %s: %s", tenant or "GLOBAL", to_phone, media_url)
            return

        if cls._whatsapp_uses_meta_api(cfg.get("provider")):
            clean = cls._normalize_phone_for_meta(to_phone)
            is_video = media_url.lower().endswith((".mp4", ".mov", ".avi"))
            payload = {
                "messaging_product": "whatsapp",
                "to": clean,
                "type": "video" if is_video else "image",
                "video" if is_video else "image": {
                    "link": media_url,
                    "caption": caption or "",
                },
            }
            return cls._send_meta_request(cfg["meta_phone_id"], cfg["meta_token"], payload)

        client = cls._twilio_client(cfg["sid"], cfg["token"])
        if not client:
            return

        try:
            client.messages.create(
                media_url=[media_url],
                body=caption or "",
                from_=cfg["from_number"],
                to=f"whatsapp:{to_phone}" if not to_phone.startswith("whatsapp:") else to_phone,
            )
        except Exception as e:
            logger.error("Twilio error sending media: %s", e)
            raise

    # ----------------------------------------------------------------------
    # WhatsApp Document (e.g. PDF brochure)
    # ----------------------------------------------------------------------

    @classmethod
    def send_whatsapp_document(cls, to_phone: str, document_url: str, caption: Optional[str] = None,
                               tenant: Optional[str] = None) -> None:
        """Send a document (e.g. PDF) via WhatsApp. URL must be publicly accessible."""
        cfg = cls._wa_cfg(tenant)
        if not cfg["enabled"]:
            logger.info("[NO-OP] [%s] WhatsApp document to %s: %s", tenant or "GLOBAL", to_phone, document_url)
            return

        if cls._whatsapp_uses_meta_api(cfg.get("provider")):
            clean = cls._normalize_phone_for_meta(to_phone)
            payload = {
                "messaging_product": "whatsapp",
                "to": clean,
                "type": "document",
                "document": {
                    "link": document_url,
                    "caption": (caption or "")[:1024],
                },
            }
            return cls._send_meta_request(cfg["meta_phone_id"], cfg["meta_token"], payload)

        client = cls._twilio_client(cfg["sid"], cfg["token"])
        if not client:
            return

        try:
            client.messages.create(
                media_url=[document_url],
                body=caption or "",
                from_=cfg["from_number"],
                to=f"whatsapp:{to_phone}" if not to_phone.startswith("whatsapp:") else to_phone,
            )
        except Exception as e:
            logger.error("Twilio error sending document: %s", e)
            raise

    # ----------------------------------------------------------------------
    # WhatsApp Interactive
    # ----------------------------------------------------------------------

    @classmethod
    def send_whatsapp_interactive(cls, to_phone: str, interactive_payload: Dict[str, Any],
                                  tenant: Optional[str] = None) -> None:
        cfg = cls._wa_cfg(tenant)
        if not cfg["enabled"]:
            logger.info("[NO-OP] [%s] WhatsApp interactive to %s", tenant or "GLOBAL", to_phone)
            return

        if cls._whatsapp_uses_meta_api(cfg.get("provider")):
            clean = cls._normalize_phone_for_meta(to_phone)
            payload = {
                "messaging_product": "whatsapp",
                "to": clean,
                "type": "interactive",
                "interactive": interactive_payload,
            }
            return cls._send_meta_request(cfg["meta_phone_id"], cfg["meta_token"], payload)

        # Twilio (and others): no Cloud API interactive — match ``send_whatsapp_interactive`` fallback below
        body = interactive_payload.get("body", {}).get("text") or "Interactive message"
        if interactive_payload.get("type") == "cta_url":
            params = (interactive_payload.get("action") or {}).get("parameters") or {}
            u = (params.get("url") or "").strip()
            if u:
                body = f"{body.rstrip()}\n\n{u}"
        cls.send_whatsapp_text(to_phone, body, tenant=tenant)

    # ----------------------------------------------------------------------
    # Email
    # ----------------------------------------------------------------------

    @classmethod
    def send_email(
            cls,
            to_email: str,
            subject: str,
            text_body: str,
            html_body: Optional[str] = None,
            attachments: Optional[Sequence[tuple[str, bytes, str]]] = None,
            tenant: Optional[str] = None,
    ) -> None:
        cfg = cls._smtp_cfg(tenant)
        if not cfg["enabled"]:
            logger.info("[NO-OP] [%s] Email to %s: %s", tenant or "GLOBAL", to_email, subject)
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = cfg["sender"]
        msg["To"] = to_email

        msg.attach(MIMEText(text_body or "", "plain"))
        if html_body:
            msg.attach(MIMEText(html_body, "html"))

        if attachments:
            for filename, data, mime in attachments:
                part = MIMEApplication(data, _subtype=mime.split("/")[-1])
                part.add_header("Content-Disposition", "attachment", filename=filename)
                msg.attach(part)

        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.starttls()
            if cfg["user"]:
                server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["sender"], [to_email], msg.as_string())
