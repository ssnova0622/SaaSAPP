"""Tenant and settings storage (list tenants, settings, seed)."""
from __future__ import annotations

import datetime as dt
import logging
import re
from typing import Any, Dict, List, Optional

from app.helpers.constants import DEFAULT_DISPLAY_DATE_FORMAT
from app.helpers.date_utils import utcnow
from app.services.db import collections, customers_collection
logger = logging.getLogger(__name__)


class TenantStorage:
    @classmethod
    def list_tenants_basic(cls) -> List[Dict[str, Any]]:
        tenants_col, _pros, _appts = collections()
        out: List[Dict[str, Any]] = []
        for t in tenants_col.find({}, {"_id": 1, "category": 1, "owner_email": 1, "owner_phone": 1, "tz": 1,
                                       "invoice_delivery": 1, "active": 1, "trial_ends_at": 1, "plan": 1,
                                       "payment_config": 1}).sort("_id", 1):
            pay_cfg = t.get("payment_config") or {}
            if not isinstance(pay_cfg, dict):
                pay_cfg = {}
            out.append({
                "tenant": t.get("_id"),
                "category": t.get("category", "salon"),
                "owner_email": t.get("owner_email"),
                "owner_phone": t.get("owner_phone"),
                "tz": t.get("tz"),
                "invoice_delivery": t.get("invoice_delivery", "both"),
                "active": bool(t.get("active", True)),
                "trial_ends_at": t.get("trial_ends_at"),
                "plan": t.get("plan"),
                "payment_config": {"provider": pay_cfg.get("provider", "dummy"),
                                   "currency": pay_cfg.get("currency", "INR")},
            })
        return out

    @classmethod
    def ensure_active_flags(cls) -> Dict[str, int]:
        tenants_col, pros_col, _appts = collections()
        customers_col = customers_collection()
        pros_result = pros_col.update_many({"active": {"$exists": False}}, {"$set": {"active": True}})
        cust_result = customers_col.update_many({"active": {"$exists": False}}, {"$set": {"active": True}})
        return {"professionals": pros_result.modified_count, "customers": cust_result.modified_count}

    @classmethod
    def get_tenant_settings(cls, tenant: str) -> Optional[Dict[str, Any]]:
        tenants_col, _pros, _appts = collections()
        doc = tenants_col.find_one({"_id": tenant})
        if not doc:
            return None
        doc = dict(doc)
        doc["tenant"] = doc.get("_id", tenant)
        doc["active"] = bool(doc.get("active", True))
        raw_modules = doc.get("modules")
        if isinstance(raw_modules, list):
            doc["modules"] = sorted({str(m).lower() for m in raw_modules if str(m).strip()})
        else:
            doc["modules"] = []
        raw_caps = doc.get("capabilities")
        if isinstance(raw_caps, list):
            doc["capabilities"] = sorted({str(c).lower() for c in raw_caps if str(c).strip()})
        else:
            doc["capabilities"] = []
        raw_action_ids = doc.get("enabled_action_ids")
        if isinstance(raw_action_ids, list):
            doc["enabled_action_ids"] = [str(a).strip() for a in raw_action_ids if str(a).strip()]
        else:
            doc["enabled_action_ids"] = []
        if "store_enabled" not in doc:
            doc["store_enabled"] = True
        pay_cfg = doc.get("payment_config") or {}
        if not isinstance(pay_cfg, dict):
            pay_cfg = {}
        pay_cfg.setdefault("provider", "dummy")
        pay_cfg.setdefault("currency", "INR")
        pay_cfg.setdefault("methods", ["ONLINE", "COD"])
        pay_cfg.setdefault("test_mode", True)
        pay_cfg.setdefault("webhook_secret", "dev")
        doc["payment_config"] = pay_cfg
        deliv_cfg = doc.get("delivery_config") or {}
        if not isinstance(deliv_cfg, dict):
            deliv_cfg = {}
        deliv_cfg.setdefault("delivery_enabled", True)
        deliv_cfg.setdefault("pickup_enabled", True)
        deliv_cfg.setdefault("service_areas", [])
        deliv_cfg.setdefault("store_hours", [])
        doc["delivery_config"] = deliv_cfg
        wa_cfg = doc.get("whatsapp_config") or {}
        if not isinstance(wa_cfg, dict):
            wa_cfg = {}
        wa_cfg.setdefault("enabled", True)
        wa_cfg.setdefault("provider", "twilio")
        if "from_numbers" not in wa_cfg:
            if "from_number" in wa_cfg and isinstance(wa_cfg.get("from_number"), str):
                wa_cfg["from_numbers"] = [wa_cfg.get("from_number")]
            else:
                wa_cfg["from_numbers"] = []
        wa_cfg.setdefault("from_number", wa_cfg["from_numbers"][0] if wa_cfg["from_numbers"] else "")
        wa_cfg.setdefault("account_sid", "")
        wa_cfg.setdefault("auth_token", "")
        wa_cfg.setdefault("phone_number_id", "")
        wa_cfg.setdefault("access_token", "")
        wa_cfg.setdefault("webhook_secret", "dev")
        wa_cfg.setdefault("active_menu_id", "")
        for unwanted in ["locale_default"]:
            wa_cfg.pop(unwanted, None)
        doc["whatsapp_config"] = wa_cfg
        smtp_cfg = doc.get("smtp_config") or {}
        if not isinstance(smtp_cfg, dict):
            smtp_cfg = {}
        smtp_cfg.setdefault("enabled", False)
        smtp_cfg.setdefault("host", "")
        smtp_cfg.setdefault("port", 587)
        smtp_cfg.setdefault("user", "")
        smtp_cfg.setdefault("password", "")
        smtp_cfg.setdefault("sender", "")
        doc["smtp_config"] = smtp_cfg
        doc.setdefault("date_format", DEFAULT_DISPLAY_DATE_FORMAT)
        # Plan (subscription tier): basic | pro | enterprise; default for existing tenants
        from app.modules.plans import DEFAULT_PLAN, PLAN_IDS
        raw_plan = doc.get("plan")
        doc["plan"] = str(raw_plan).lower() if raw_plan and str(raw_plan).lower() in PLAN_IDS else DEFAULT_PLAN
        # Messaging channels: which channels tenant can use (email, whatsapp, sms)
        ch = doc.get("messaging_channels")
        if not isinstance(ch, dict):
            ch = {}
        doc["messaging_channels"] = {
            "email": ch.get("email", True),
            "whatsapp": ch.get("whatsapp", True),
            "sms": ch.get("sms", False),
        }
        # SMS config (provider, from number, etc.) for when SMS is enabled
        sms_cfg = doc.get("sms_config") or {}
        if not isinstance(sms_cfg, dict):
            sms_cfg = {}
        sms_cfg.setdefault("enabled", False)
        sms_cfg.setdefault("provider", "twilio")
        sms_cfg.setdefault("from_number", "")
        sms_cfg.setdefault("account_sid", "")
        sms_cfg.setdefault("auth_token", "")
        doc["sms_config"] = sms_cfg
        # AI config defaults (configurable per tenant)
        from app.services.ai.config_schema import get_effective_ai_config
        doc["ai_config"] = get_effective_ai_config(doc)
        # message_templates: from tenant_message_templates collection (merged with defaults)
        from app.services.core.tenant_message_templates_service import get_templates_for_tenant
        doc["message_templates"] = get_templates_for_tenant(tenant)
        doc.setdefault("address", doc.get("address") or "")
        doc.setdefault("location", doc.get("location") or "")
        return doc

    @classmethod
    def update_tenant_settings(cls, tenant: str, updates: Dict[str, Any], user_id: Optional[str] = None) -> Dict[
        str, Any]:
        tenants_col, _pros, _appts = collections()
        allowed = {"owner_email", "owner_phone", "tz", "date_format", "invoice_delivery", "followup_prefs", "templates",
                   "message_templates", "active", "store_enabled", "payment_config", "delivery_config",
                   "whatsapp_config",
                   "smtp_config", "modules", "capabilities", "ai_config", "plan", "messaging_channels", "sms_config",
                   "address", "location"}
        payload = {k: v for k, v in (updates or {}).items() if k in allowed}
        if "modules" in payload or "capabilities" in payload:
            from app.modules.registry import normalize_selection
            mods = payload.get("modules")
            caps = payload.get("capabilities")
            if mods is not None and not isinstance(mods, list):
                raise ValueError("modules must be a list of strings")
            if caps is not None and not isinstance(caps, list):
                raise ValueError("capabilities must be a list of strings")
            norm_mods, norm_caps = normalize_selection(mods or [], caps or [])
            payload["modules"] = norm_mods
            payload["capabilities"] = norm_caps
        if tenants_col.find_one({"_id": tenant}) is None:
            raise ValueError("Tenant not found")
        if "whatsapp_config" in payload and isinstance(payload["whatsapp_config"], dict):
            wa = payload["whatsapp_config"]
            if "from_numbers" in wa and isinstance(wa["from_numbers"], list) and wa["from_numbers"]:
                wa["from_number"] = wa["from_numbers"][0]
        if "plan" in payload and payload["plan"] is not None:
            from app.modules.plans import PLAN_IDS, DEFAULT_PLAN
            p = str(payload["plan"]).strip().lower()
            payload["plan"] = p if p in PLAN_IDS else DEFAULT_PLAN
        if "messaging_channels" in payload and isinstance(payload["messaging_channels"], dict):
            ch = payload["messaging_channels"]
            payload["messaging_channels"] = {
                "email": bool(ch.get("email", True)),
                "whatsapp": bool(ch.get("whatsapp", True)),
                "sms": bool(ch.get("sms", False)),
            }
        payload["updated_at"] = utcnow()
        payload["updated_by"] = user_id
        tenants_col.update_one({"_id": tenant}, {"$set": payload}, upsert=False)
        doc = tenants_col.find_one({"_id": tenant})
        if not doc:
            raise ValueError("Tenant not found")
        doc = dict(doc)
        doc["tenant"] = doc.get("_id", tenant)
        doc["active"] = bool(doc.get("active", True))
        return doc

    @classmethod
    def _get_tenant_country_code(cls, tenant: str) -> Optional[str]:
        settings = cls.get_tenant_settings(tenant) or {}
        if settings.get("default_country_code"):
            return str(settings["default_country_code"])
        owner_phone = settings.get("owner_phone")
        if owner_phone and owner_phone.startswith("+"):
            digits = re.sub(r"\D", "", owner_phone)
            if digits.startswith("91"):
                return "91"
            if digits.startswith("971"):
                return "971"
            if len(digits) > 10:
                return digits[:2]
        return None

    @classmethod
    def tenant_exists(cls, tenant: str) -> bool:
        tenants_col, _pros, _appts = collections()
        return tenants_col.find_one({"_id": tenant}) is not None

    @classmethod
    def get_tenant(cls, tenant: str) -> Optional[Dict[str, Any]]:
        tenants_col, _pros, _appts = collections()
        return tenants_col.find_one({"_id": tenant})

    @classmethod
    def get_revenue(cls, tenant: str) -> float:
        tenants_col, _pros, _appts = collections()
        doc = tenants_col.find_one({"_id": tenant})
        return float(doc.get("revenue", 0.0)) if doc else 0.0

    @classmethod
    def delete_tenant(cls, tenant: str, user_id: Optional[str] = None) -> bool:
        tenants_col, _pros_col, _appts_col = collections()
        res = tenants_col.update_one({"_id": tenant}, {
            "$set": {"active": False, "updated_at": utcnow(), "updated_by": user_id}})
        return bool(res.matched_count)

    @classmethod
    def seed_if_absent(cls, tenant: str, data: Dict[str, Any]) -> None:
        tenants_col, pros_col, _appts_col = collections()
        from app.modules.plans import get_plan_defaults, DEFAULT_PLAN, PLAN_IDS
        plan = (data.get("plan") or DEFAULT_PLAN)
        if isinstance(plan, str) and plan.strip().lower() in PLAN_IDS:
            plan = plan.strip().lower()
        else:
            plan = DEFAULT_PLAN
        defaults = get_plan_defaults(plan)
        set_on_insert = {
            "_id": tenant,
            "category": data.get("category", "salon"),
            "revenue": float(data.get("revenue", 0.0)),
            "cancellations": int(data.get("cancellations", 0)),
            "active": True,
            "plan": plan,
            "modules": data.get("modules") if isinstance(data.get("modules"), list) and data["modules"] else defaults[
                "modules"],
            "capabilities": data.get("capabilities") if isinstance(data.get("capabilities"), list) and data[
                "capabilities"] else defaults["capabilities"],
            "messaging_channels": data.get("messaging_channels") if isinstance(data.get("messaging_channels"),
                                                                               dict) else {"email": True,
                                                                                           "whatsapp": True,
                                                                                           "sms": False},
        }
        if data.get("owner_email"):
            set_on_insert["owner_email"] = data.get("owner_email")
        if data.get("owner_phone"):
            set_on_insert["owner_phone"] = data.get("owner_phone")
        if data.get("tz"):
            set_on_insert["tz"] = data.get("tz")
        if isinstance(data.get("whatsapp_config"), dict):
            set_on_insert["whatsapp_config"] = data.get("whatsapp_config")
        if data.get("trial_ends_at") is not None:
            set_on_insert["trial_ends_at"] = data["trial_ends_at"]
        tenants_col.update_one({"_id": tenant}, {"$setOnInsert": set_on_insert}, upsert=True)
        if pros_col.count_documents({"tenant": tenant}) == 0:
            pros_raw: List[Any] = data.get("professionals") or []
            if pros_raw:
                from app.services.salon.professional_service import ProfessionalService
                from app.helpers.professional_slots import normalize_slots, default_business_slots

                for idx, p in enumerate(pros_raw):
                    if isinstance(p, dict):
                        name = p.get("name")
                        price = float(p.get("price") or 0.0)
                        slots = normalize_slots(p.get("slots"))
                        eid = str(p.get("employee_id") or "").strip() or f"EMP-{idx + 1:04d}"
                    else:
                        name = getattr(p, "name", None)
                        price = float(getattr(p, "price", 0.0) or 0.0)
                        slots = normalize_slots(getattr(p, "slots", None))
                        eid = str(getattr(p, "employee_id", None) or "").strip() or f"EMP-{idx + 1:04d}"
                    if not name:
                        continue
                    if not slots:
                        slots = default_business_slots(9, 19)
                    try:
                        ProfessionalService.add_professional(
                            tenant,
                            str(name),
                            employee_id=eid,
                            price=price,
                            slots=slots,
                        )
                    except ValueError:
                        continue

    @classmethod
    def deactivate_expired_trials(cls) -> int:
        """Deactivate tenants whose trial_ends_at is in the past. Returns number of tenants deactivated."""
        tenants_col, _pros, _appts = collections()
        now = utcnow()
        res = tenants_col.update_many(
            {"trial_ends_at": {"$exists": True, "$lt": now}, "active": True},
            {"$set": {"active": False, "updated_at": now}},
        )
        if res.modified_count:
            logger.info("Deactivated %d tenant(s) with expired trial", res.modified_count)
        return res.modified_count
