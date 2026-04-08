"""MongoDB storage for WhatsApp menus, sessions, triggers and tenant stats."""
from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Dict, List, Optional

from app.helpers.date_utils import utcnow
from app.services.db import collections, get_db

logger = logging.getLogger(__name__)


class WhatsAppStorage:
    @classmethod
    def _whatsapp_menus_col(cls):
        db = get_db()
        col = db["whatsapp_menus"]
        try:
            col.create_index(
                [("tenant", 1), ("menu_id", 1), ("status", 1), ("version", -1)],
                name="tenant_menu_status_ver",
            )
        except Exception as e:
            logger.warning("whatsapp_menus index creation skipped: %s", e)
        return col

    @classmethod
    def _whatsapp_sessions_col(cls):
        db = get_db()
        col = db["whatsapp_sessions"]
        try:
            col.create_index([("tenant", 1), ("phone", 1)], name="tenant_phone")
            col.create_index("expires_at", expireAfterSeconds=0, name="ttl_expires_at")
        except Exception as e:
            logger.warning("whatsapp_sessions index creation skipped: %s", e)
        return col

    @classmethod
    def _whatsapp_triggers_col(cls):
        db = get_db()
        col = db["whatsapp_triggers"]
        try:
            col.create_index(
                [("tenant", 1), ("enabled", 1), ("priority", -1)],
                name="tenant_enabled_pri",
            )
            col.create_index(
                [("tenant", 1), ("trigger_id", 1)],
                unique=True,
                name="tenant_trigger_id",
            )
        except Exception as e:
            logger.warning("whatsapp_triggers index creation skipped: %s", e)
        return col

    @classmethod
    def _whatsapp_tenant_stats_col(cls):
        db = get_db()
        col = db.get_collection("whatsapp_tenant_stats")
        try:
            col.create_index([("tenant", 1)], unique=True, name="tenant_unique")
        except Exception as e:
            logger.warning("whatsapp_tenant_stats index creation skipped: %s", e)
        return col

    @classmethod
    def increment_whatsapp_inbound(cls, tenant: str) -> None:
        if not tenant:
            return
        col = cls._whatsapp_tenant_stats_col()
        col.update_one(
            {"tenant": tenant},
            {"$inc": {"inbound_count": 1}, "$set": {"updated_at": utcnow()}},
            upsert=True,
        )

    @classmethod
    def get_whatsapp_inbound_counts(cls) -> Dict[str, int]:
        col = cls._whatsapp_tenant_stats_col()
        out: Dict[str, int] = {}
        for doc in col.find({}, {"tenant": 1, "inbound_count": 1}):
            out[str(doc.get("tenant", ""))] = int(doc.get("inbound_count") or 0)
        return out

    @classmethod
    def increment_whatsapp_outbound(cls, tenant: str) -> None:
        if not tenant:
            return
        col = cls._whatsapp_tenant_stats_col()
        col.update_one(
            {"tenant": tenant},
            {"$inc": {"outbound_count": 1}, "$set": {"updated_at": utcnow()}},
            upsert=True,
        )

    @classmethod
    def get_whatsapp_outbound_counts(cls) -> Dict[str, int]:
        col = cls._whatsapp_tenant_stats_col()
        out: Dict[str, int] = {}
        for doc in col.find({}, {"tenant": 1, "outbound_count": 1}):
            out[str(doc.get("tenant", ""))] = int(doc.get("outbound_count") or 0)
        return out

    @classmethod
    def resolve_tenant_by_whatsapp_number(cls, number: str) -> Optional[str]:
        tenants_col, _pros, _appts = collections()
        if not number:
            return None
        num = (
            number
            if number.lower().startswith("whatsapp:")
            else f"whatsapp:{number}"
        )
        doc = tenants_col.find_one({"whatsapp_config.from_numbers": num})
        if not doc:
            return None
        return str(doc.get("_id"))

    @classmethod
    def list_whatsapp_menus(cls, tenant: str) -> List[Dict[str, Any]]:
        col = cls._whatsapp_menus_col()
        cur = col.find({"tenant": tenant}, {"_id": 0}).sort(
            [("menu_id", 1), ("status", 1), ("version", -1)]
        )
        return [dict(d) for d in cur]

    @classmethod
    def get_whatsapp_menu(
        cls,
        tenant: str,
        menu_id: str,
        status: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        col = cls._whatsapp_menus_col()
        if status:
            query = {"tenant": tenant, "menu_id": menu_id, "status": status}
            if version is not None:
                query["version"] = int(version)
            doc = col.find_one(
                query, sort=[("version", -1)], projection={"_id": 0}
            )
            return dict(doc) if doc else None
        draft = col.find_one(
            {"tenant": tenant, "menu_id": menu_id, "status": "draft"},
            projection={"_id": 0},
        )
        if draft:
            return dict(draft)
        pub = col.find_one(
            {"tenant": tenant, "menu_id": menu_id, "status": "published"},
            sort=[("version", -1)],
            projection={"_id": 0},
        )
        return dict(pub) if pub else None

    @classmethod
    def upsert_whatsapp_menu_draft(
        cls, tenant: str, doc: Dict[str, Any]
    ) -> Dict[str, Any]:
        col = cls._whatsapp_menus_col()
        now = utcnow()
        payload = {
            "tenant": tenant,
            "menu_id": str(doc.get("menu_id") or "default").strip().lower()
            or "default",
            "name": doc.get("name") or doc.get("menu_id") or "default",
            "status": "draft",
            "version": int(doc.get("version") or 0),
            "tree": doc.get("tree") or {},
            "locales": doc.get("locales") or {},
            "updated_at": now,
            "updated_by": doc.get("updated_by") or None,
        }
        col.update_one(
            {"tenant": tenant, "menu_id": payload["menu_id"], "status": "draft"},
            {"$set": payload},
            upsert=True,
        )
        out = col.find_one(
            {"tenant": tenant, "menu_id": payload["menu_id"], "status": "draft"},
            {"_id": 0},
        )
        return dict(out or payload)

    @classmethod
    def publish_whatsapp_menu(
        cls, tenant: str, menu_id: str, user_id: str
    ) -> Dict[str, Any]:
        col = cls._whatsapp_menus_col()
        draft = col.find_one(
            {"tenant": tenant, "menu_id": menu_id, "status": "draft"}
        )
        if not draft:
            raise ValueError("Draft not found")
        latest_pub = col.find_one(
            {"tenant": tenant, "menu_id": menu_id, "status": "published"},
            sort=[("version", -1)],
        )
        next_ver = int((latest_pub or {}).get("version") or 0) + 1
        now = utcnow()
        pub_doc = {
            "tenant": tenant,
            "menu_id": menu_id,
            "name": draft.get("name") or menu_id,
            "status": "published",
            "version": next_ver,
            "tree": draft.get("tree") or {},
            "locales": draft.get("locales") or {},
            "published_at": now,
            "published_by": user_id,
        }
        col.insert_one(pub_doc)
        out = col.find_one(
            {
                "tenant": tenant,
                "menu_id": menu_id,
                "status": "published",
                "version": next_ver,
            },
            {"_id": 0},
        )
        return dict(out or pub_doc)

    @classmethod
    def delete_whatsapp_menu(
        cls, tenant: str, menu_id: str, user_id: Optional[str] = None
    ) -> bool:
        col = cls._whatsapp_menus_col()
        res = col.delete_one(
            {"tenant": tenant, "menu_id": menu_id, "status": "draft"}
        )
        return res.deleted_count > 0

    @classmethod
    def get_whatsapp_session(
        cls, tenant: str, phone: str
    ) -> Optional[Dict[str, Any]]:
        col = cls._whatsapp_sessions_col()
        logger.debug("get_whatsapp_session tenant=%s phone=%s", tenant, phone)
        doc = col.find_one({"tenant": tenant, "phone": phone}, {"_id": 0})
        if not doc and phone.startswith("+"):
            doc = col.find_one({"tenant": tenant, "phone": phone[1:]}, {"_id": 0})
            if doc:
                logger.debug(
                    "get_whatsapp_session fallback match without + prefix"
                )
        logger.debug(
            "get_whatsapp_session result has_ctx=%s", bool((doc or {}).get("ctx"))
        )
        return dict(doc) if doc else None

    @classmethod
    def upsert_whatsapp_session(
        cls,
        tenant: str,
        phone: str,
        data: Dict[str, Any],
        ttl_minutes: int = 30,
    ) -> Dict[str, Any]:
        col = cls._whatsapp_sessions_col()
        now = utcnow()
        exp = now + dt.timedelta(minutes=ttl_minutes)
        logger.debug("upsert_whatsapp_session tenant=%s phone=%s", tenant, phone)
        update = {
            "$set": {
                **(data or {}),
                "tenant": tenant,
                "phone": phone,
                "updated_at": now,
                "expires_at": exp,
            },
            "$setOnInsert": {"created_at": now},
        }
        res = col.update_one(
            {"tenant": tenant, "phone": phone}, update, upsert=True
        )
        logger.debug(
            "upsert_whatsapp_session matched=%s modified=%s",
            res.matched_count,
            res.modified_count,
        )
        doc = col.find_one({"tenant": tenant, "phone": phone}, {"_id": 0})
        return dict(doc or {"tenant": tenant, "phone": phone, **data})

    @classmethod
    def list_whatsapp_triggers(cls, tenant: str) -> List[Dict[str, Any]]:
        col = cls._whatsapp_triggers_col()
        cur = col.find({"tenant": tenant}, {"_id": 0}).sort(
            [("priority", -1), ("trigger_id", 1)]
        )
        return [dict(d) for d in cur]

    @classmethod
    def get_whatsapp_trigger(
        cls, tenant: str, trigger_id: str
    ) -> Optional[Dict[str, Any]]:
        col = cls._whatsapp_triggers_col()
        doc = col.find_one(
            {"tenant": tenant, "trigger_id": trigger_id}, {"_id": 0}
        )
        return dict(doc) if doc else None

    @classmethod
    def upsert_whatsapp_trigger(
        cls, tenant: str, trigger: Dict[str, Any]
    ) -> Dict[str, Any]:
        col = cls._whatsapp_triggers_col()
        now = utcnow()
        tid = str(trigger.get("trigger_id") or "").strip()
        if not tid:
            raise ValueError("trigger_id is required")
        payload = {
            "tenant": tenant,
            "trigger_id": tid,
            "match": trigger.get("match") or {},
            "action": trigger.get("action") or {},
            "enabled": bool(trigger.get("enabled", True)),
            "priority": int(trigger.get("priority") or 0),
            "updated_at": now,
            "updated_by": trigger.get("updated_by") or None,
        }
        col.update_one(
            {"tenant": tenant, "trigger_id": tid}, {"$set": payload}, upsert=True
        )
        doc = col.find_one({"tenant": tenant, "trigger_id": tid}, {"_id": 0})
        return dict(doc or payload)

    @classmethod
    def delete_whatsapp_trigger(
        cls, tenant: str, trigger_id: str, user_id: Optional[str] = None
    ) -> bool:
        col = cls._whatsapp_triggers_col()
        res = col.delete_one({"tenant": tenant, "trigger_id": trigger_id})
        return res.deleted_count > 0

    @classmethod
    def fetch_enabled_triggers(cls, tenant: str) -> List[Dict[str, Any]]:
        col = cls._whatsapp_triggers_col()
        cur = col.find(
            {"tenant": tenant, "enabled": True}, {"_id": 0}
        ).sort([("priority", -1), ("trigger_id", 1)])
        return [dict(d) for d in cur]
