# app/services/core/promotions/sender_service.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
import time
import logging
from bson import ObjectId
from pymongo.collection import Collection

from app.helpers.date_utils import utcnow
from app.helpers.phone_util import PhoneUtil
from app.services.core.tenant_service import TenantService
from app.helpers.ws_utils import broadcast_safe
from settings import env

from app.services.db import customers_collection
from .helpers.db_utils import promotions_col, promotion_logs_col
from .audience_service import AudienceService
from .logs_service import PromotionLogsService
from ..messaging_service import Messaging
from .whatsapp_delivery import append_cta_urls_to_message_text, append_offer_code_line, send_promotion_whatsapp

logger = logging.getLogger(__name__)


class PromotionSenderService:
    @staticmethod
    def send_now(tenant: str, prom_id: str) -> Dict[str, Any]:
        promos = promotions_col()
        logs = promotion_logs_col()

        try:
            _id = ObjectId(prom_id)
        except Exception:
            raise ValueError("Invalid promotion id")

        promo = promos.find_one({"_id": _id, "tenant": tenant})
        if not promo:
            raise ValueError("Promotion not found")

        stats = promo.get("stats") or {"total": 0, "sent": 0, "failed": 0}
        if promo.get("status") in ("running", "completed"):
            return {
                "id": str(_id),
                "tenant": tenant,
                "status": promo.get("status"),
                "total": stats.get("total", 0),
                "sent": stats.get("sent", 0),
                "failed": stats.get("failed", 0),
            }

        recipients = AudienceService.resolve(tenant, promo.get("audience") or {})
        total = len(recipients)

        promos.update_one(
            {"_id": _id},
            {"$set": {"status": "running", "started_at": utcnow(), "stats": {"total": total, "sent": 0, "failed": 0}}},
        )

        broadcast_safe({
            "type": "promotion.started",
            "tenant": tenant,
            "promotion_id": str(_id),
            "total": total,
        })

        batch_size = env.int("PROMO_BATCH_SIZE", 50)
        rps = max(1, env.int("PROMO_RPS", 20))
        delay = 1.0 / float(rps)

        sent = failed = processed = 0

        def progress():
            broadcast_safe({
                "type": "promotion.progress",
                "tenant": tenant,
                "promotion_id": str(_id),
                "total": total,
                "sent": sent,
                "failed": failed,
                "processed": processed,
            })

        channel = (promo.get("channel") or "both").lower()
        message = promo.get("message", "")
        html_message = promo.get("html_message")
        interactive_type = promo.get("interactive_type")
        buttons = promo.get("buttons") or []
        list_sections = promo.get("list_sections") or []
        attachments = promo.get("attachments")

        message_with_links = PromotionSenderService._append_links(
            message, interactive_type, buttons, list_sections,
        )
        message_for_whatsapp = append_cta_urls_to_message_text(message_with_links, promo)
        email_body = append_offer_code_line(
            append_cta_urls_to_message_text(message_with_links, promo, force=True),
            promo,
        )

        active_map = PromotionSenderService._build_active_map(tenant, recipients)

        for idx, r in enumerate(recipients, start=1):
            phone = r.get("phone")
            email = r.get("email")

            if channel in ("whatsapp", "both") and phone:
                s, f = PromotionSenderService._send_whatsapp_for_recipient(
                    tenant,
                    _id,
                    phone,
                    message_for_whatsapp,
                    interactive_type,
                    buttons,
                    list_sections,
                    attachments,
                    promo,
                    logs,
                    active_map,
                )
                sent += s
                failed += f

            if channel in ("email", "both") and email:
                s, f = PromotionSenderService._send_email_for_recipient(
                    tenant,
                    _id,
                    email,
                    promo.get("name", "Promotion"),
                    email_body,
                    html_message,
                    logs,
                )
                sent += s
                failed += f

            processed += 1
            time.sleep(delay)
            if (idx % batch_size) == 0 or idx == total:
                progress()

        status = "completed"
        promos.update_one(
            {"_id": _id},
            {"$set": {"status": status, "completed_at": utcnow(),
                      "stats": {"total": total, "sent": sent, "failed": failed}}},
        )

        broadcast_safe({
            "type": "promotion.completed",
            "tenant": tenant,
            "promotion_id": str(_id),
            "total": total,
            "sent": sent,
            "failed": failed,
        })

        return {"id": str(_id), "tenant": tenant, "status": status, "total": total, "sent": sent, "failed": failed}

    # --- helpers below ---

    @staticmethod
    def _append_links(
        message: str,
        interactive_type: Optional[str],
        buttons,
        list_sections,
    ) -> str:
        msg = message
        it = (interactive_type or "").lower()
        if it == "button" and any(b.get("url") for b in buttons):
            links = [f"{b['title']}: {b['url']}" for b in buttons if b.get("url")]
            msg += "\n\n" + "\n".join(links)
        elif it == "list" and any(r.get("url") for s in list_sections for r in s.get("rows", [])):
            links = [f"{r['title']}: {r['url']}" for s in list_sections for r in s.get("rows", []) if r.get("url")]
            msg += "\n\n" + "\n".join(links)
        return msg

    @staticmethod
    def _build_active_map(tenant: str, recipients: List[Dict[str, Any]]) -> Dict[str, bool]:
        phones = [PhoneUtil.promo_normalize(r.get("phone")) for r in recipients if r.get("phone")]
        if not phones:
            return {}
        col_cust = customers_collection()
        dial = TenantService._get_tenant_country_code(tenant) or PhoneUtil.DEFAULT_DIAL_DIGITS
        active_map: Dict[str, bool] = {}
        seen: set[str] = set()
        for ph in phones:
            if ph in seen:
                continue
            seen.add(ph)
            doc = col_cust.find_one(PhoneUtil.customer_match_query(tenant, ph, dial), {"active": 1})
            if doc:
                active_map[ph] = bool(doc.get("active", True))
        return active_map

    @staticmethod
    def _send_whatsapp_for_recipient(
            tenant: str,
            prom_id,
            phone: str,
            message_with_links: str,
            interactive_type: str,
            buttons,
            list_sections,
            attachments,
            promo: Dict[str, Any],
            logs: Collection,
            active_map: Dict[str, bool],
    ) -> tuple[int, int]:
        to_val = PhoneUtil.promo_normalize(phone)
        sent = failed = 0

        if active_map.get(to_val, True) is False:
            PromotionLogsService.insert_safe({
                "promotion_id": prom_id,
                "tenant": tenant,
                "to": to_val,
                "channel": "whatsapp",
                "status": "skipped",
                "reason": "inactive_customer",
                "sent_at": utcnow(),
            })
            return 0, 0

        if logs.find_one({"promotion_id": prom_id, "channel": "whatsapp", "to": to_val}):
            return 0, 0

        try:
            promo_snapshot = {
                "interactive_type": interactive_type,
                "attachments": attachments or [],
                "buttons": buttons,
                "list_sections": list_sections,
                "cta_url": promo.get("cta_url"),
                "cta_display_text": promo.get("cta_display_text"),
                "cta_footer": promo.get("cta_footer"),
                "cta_entries": promo.get("cta_entries"),
                "cta_append_urls_to_body": promo.get("cta_append_urls_to_body"),
                "offer_code": promo.get("offer_code"),
            }
            send_promotion_whatsapp(tenant, to_val, promo_snapshot, message_with_links)

            PromotionLogsService.insert_safe({
                "promotion_id": prom_id,
                "tenant": tenant,
                "to": to_val,
                "channel": "whatsapp",
                "status": "sent",
                "sent_at": utcnow(),
            })
            sent += 1
        except Exception as e:
            PromotionLogsService.insert_safe({
                "promotion_id": prom_id,
                "tenant": tenant,
                "to": to_val,
                "channel": "whatsapp",
                "status": "failed",
                "error": str(e),
                "sent_at": utcnow(),
            })
            failed += 1

        return sent, failed

    @staticmethod
    def _send_email_for_recipient(
            tenant: str,
            prom_id,
            email: str,
            subject: str,
            text: str,
            html: str,
            logs: Collection,
    ) -> tuple[int, int]:
        sent = failed = 0
        if logs.find_one({"promotion_id": prom_id, "channel": "email", "to": email}):
            return 0, 0

        try:
            Messaging.send_email(email, subject, text, html, tenant=tenant)
            PromotionLogsService.insert_safe({
                "promotion_id": prom_id,
                "tenant": tenant,
                "to": email,
                "channel": "email",
                "status": "sent",
                "sent_at": utcnow(),
            })
            sent += 1
        except Exception as e:
            PromotionLogsService.insert_safe({
                "promotion_id": prom_id,
                "tenant": tenant,
                "to": email,
                "channel": "email",
                "status": "failed",
                "error": str(e),
                "sent_at": utcnow(),
            })
            failed += 1

        return sent, failed
