# app/services/core/promotions/promotion_service.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId
from app.helpers.date_utils import utcnow
from .helpers.db_utils import promotions_col
from .sender_service import PromotionSenderService
from .logs_service import PromotionLogsService


class PromotionService:
    @staticmethod
    def create_promotion(
            tenant: str,
            name: str,
            channel: str,
            message: str,
            html_message: Optional[str],
            media_url: Optional[str],
            audience: Dict[str, Any],
            schedule_at: Optional[datetime] = None,
            attachments: Optional[List[Dict[str, Any]]] = None,
            interactive_type: Optional[str] = None,
            buttons: Optional[List[Dict[str, Any]]] = None,
            list_sections: Optional[List[Dict[str, Any]]] = None,
            cta_url: Optional[str] = None,
            cta_display_text: Optional[str] = None,
            cta_footer: Optional[str] = None,
            cta_entries: Optional[List[Dict[str, Any]]] = None,
            cta_append_urls_to_body: Optional[bool] = None,
            offer_code: Optional[str] = None,
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        col = promotions_col()
        now = utcnow()
        entries = list(cta_entries) if cta_entries else []
        if entries:
            fe = entries[0]
            if (fe.get("url") or "").strip():
                cta_url = fe["url"].strip()
                cta_display_text = (fe.get("display_text") or cta_display_text or "Open").strip()
        entries_out: Optional[List[Dict[str, Any]]] = entries if entries else None
        doc = {
            "tenant": tenant,
            "name": name,
            "channel": channel or "both",
            "message": message or "",
            "html_message": html_message,
            "media_url": media_url,
            "attachments": attachments,
            "interactive_type": interactive_type,
            "buttons": buttons,
            "list_sections": list_sections,
            "cta_url": cta_url,
            "cta_display_text": cta_display_text,
            "cta_footer": cta_footer,
            "cta_entries": entries_out,
            "cta_append_urls_to_body": True if cta_append_urls_to_body is None else bool(cta_append_urls_to_body),
            "offer_code": offer_code,
            "audience": audience or {"type": "all"},
            "schedule_at": schedule_at,
            "created_at": now,
            "created_by": user_id,
            "updated_at": now,
            "updated_by": user_id,
            "status": "draft" if schedule_at is None else "scheduled",
        }
        res = col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return PromotionService._public(doc)

    @staticmethod
    def list_promotions(tenant: str) -> List[Dict[str, Any]]:
        col = promotions_col()
        return [PromotionService._public(d) for d in col.find({"tenant": tenant}).sort("created_at", -1)]

    @staticmethod
    def get_promotion(tenant: str, prom_id: str) -> Optional[Dict[str, Any]]:
        col = promotions_col()
        try:
            _id = ObjectId(prom_id)
        except Exception:
            return None
        d = col.find_one({"_id": _id, "tenant": tenant})
        return PromotionService._public(d) if d else None

    @staticmethod
    def update_promotion(
            tenant: str,
            prom_id: str,
            updates: Dict[str, Any],
            user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        col = promotions_col()
        try:
            _id = ObjectId(prom_id)
        except Exception:
            return None

        doc = col.find_one({"_id": _id, "tenant": tenant})
        if not doc:
            return None
        if doc.get("status") in ("running", "completed"):
            raise ValueError("Cannot update a promotion that has started")

        allowed = {
            "name",
            "channel",
            "message",
            "html_message",
            "media_url",
            "attachments",
            "audience",
            "schedule_at",
            "status",
            "interactive_type",
            "buttons",
            "list_sections",
            "cta_url",
            "cta_display_text",
            "cta_footer",
            "offer_code",
            "cta_entries",
            "cta_append_urls_to_body",
        }
        payload = {k: v for k, v in (updates or {}).items() if k in allowed}
        payload["updated_at"] = utcnow()
        payload["updated_by"] = user_id
        if "cta_entries" in payload and payload.get("cta_entries"):
            fe = payload["cta_entries"][0]
            if isinstance(fe, dict) and (fe.get("url") or "").strip():
                payload["cta_url"] = fe["url"].strip()
                payload["cta_display_text"] = (fe.get("display_text") or payload.get("cta_display_text") or "Open").strip()

        col.update_one({"_id": _id}, {"$set": payload})
        d = col.find_one({"_id": _id})
        return PromotionService._public(d) if d else None

    @staticmethod
    def delete_promotion(tenant: str, prom_id: str, user_id: Optional[str] = None) -> bool:
        col = promotions_col()
        try:
            _id = ObjectId(prom_id)
        except Exception:
            return False
        res = col.delete_one({"_id": _id, "tenant": tenant})
        return res.deleted_count > 0

    @staticmethod
    def send_promotion_now(tenant: str, prom_id: str) -> Dict[str, Any]:
        return PromotionSenderService.send_now(tenant, prom_id)

    @staticmethod
    def list_logs(
            tenant: str,
            prom_id: str,
            page: int = 1,
            size: int = 50,
            status: Optional[str] = None,
            channel: Optional[str] = None,
            from_ts: Optional[datetime] = None,
            to_ts: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        return PromotionLogsService.list_logs(
            tenant=tenant,
            prom_id=prom_id,
            page=page,
            size=size,
            status=status,
            channel=channel,
            from_ts=from_ts,
            to_ts=to_ts,
        )

    @staticmethod
    def _public(d: Dict[str, Any]) -> Dict[str, Any]:
        if not d:
            return {}
        out = dict(d)
        out["id"] = str(out.pop("_id"))
        return out
