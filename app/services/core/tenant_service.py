# app/services/core/tenant_service.py
from __future__ import annotations

# ============================================================
# Imports
# ============================================================

import re
from typing import Any, Dict, List, Optional
from pymongo import ReturnDocument

from app.helpers.date_utils import utcnow
from app.services.db import get_db
from app.modules.registry import normalize_selection, list_registry
from app.helpers.constants import DEFAULT_DISPLAY_DATE_FORMAT, DEFAULT_TIMEZONE
from app.helpers.countries_data import DEFAULT_TENANT_COUNTRY_ISO2, DIAL_BY_ISO2, dial_digits_for_iso
from app.helpers.phone_util import PhoneUtil
from app.repositories.tenant_repository import TenantRepository

tenant_repo = TenantRepository()


# ============================================================
# DB Helpers
# ============================================================

def _tenants_col():
    return get_db().get_collection("tenants")


def _professionals_col():
    return get_db().get_collection("professionals")


def _appointments_col():
    return get_db().get_collection("appointments")


def _customers_col():
    from app.services.db import customers_collection
    return customers_collection()


def _staff_col():
    from app.services.db import staff_collection
    return staff_collection()


# ============================================================
# Settings Normalization
# ============================================================

def _normalize_modules(raw: Any) -> List[str]:
    if isinstance(raw, list):
        return sorted({str(m).lower() for m in raw if str(m).strip()})
    return []


def _normalize_capabilities(raw: Any) -> List[str]:
    if isinstance(raw, list):
        return sorted({str(c).lower() for c in raw if str(c).strip()})
    return []


def _normalize_payment_config(raw: Any) -> Dict[str, Any]:
    cfg = raw if isinstance(raw, dict) else {}
    cfg.setdefault("provider", "dummy")
    cfg.setdefault("currency", "INR")
    cfg.setdefault("methods", ["ONLINE", "COD"])
    cfg.setdefault("test_mode", True)
    cfg.setdefault("webhook_secret", "dev")
    return cfg


def _normalize_delivery_config(raw: Any) -> Dict[str, Any]:
    cfg = raw if isinstance(raw, dict) else {}
    cfg.setdefault("delivery_enabled", True)
    cfg.setdefault("pickup_enabled", True)
    cfg.setdefault("service_areas", [])
    cfg.setdefault("store_hours", [])
    return cfg


def _normalize_whatsapp_config(raw: Any) -> Dict[str, Any]:
    cfg = raw if isinstance(raw, dict) else {}

    cfg.setdefault("enabled", True)
    cfg.setdefault("provider", "twilio")

    # Normalize from_numbers
    if "from_numbers" not in cfg:
        if isinstance(cfg.get("from_number"), str):
            cfg["from_numbers"] = [cfg["from_number"]]
        else:
            cfg["from_numbers"] = []

    cfg.setdefault("from_number", cfg["from_numbers"][0] if cfg["from_numbers"] else "")
    cfg.setdefault("account_sid", "")
    cfg.setdefault("auth_token", "")
    cfg.setdefault("phone_number_id", "")
    cfg.setdefault("access_token", "")
    cfg.setdefault("webhook_secret", "dev")
    cfg.setdefault("active_menu_id", "")

    # Remove deprecated keys
    cfg.pop("locale_default", None)

    return cfg


def _normalize_smtp_config(raw: Any) -> Dict[str, Any]:
    cfg = raw if isinstance(raw, dict) else {}
    cfg.setdefault("enabled", False)
    cfg.setdefault("host", "")
    cfg.setdefault("port", 587)
    cfg.setdefault("user", "")
    cfg.setdefault("password", "")
    cfg.setdefault("sender", "")
    return cfg


def _sanitize_tenant_country_iso(iso: Optional[str]) -> str:
    if not iso or len(str(iso).strip()) != 2:
        return DEFAULT_TENANT_COUNTRY_ISO2
    u = str(iso).strip().upper()
    return u if u in DIAL_BY_ISO2 else DEFAULT_TENANT_COUNTRY_ISO2


def _merge_tenant_phone_payload(tenant: str, payload: Dict[str, Any]) -> None:
    """Normalize tenant_country and owner_phone_number only (mutates dict)."""
    cur = TenantService.get_tenant_settings(tenant) or {}
    effective_iso = _sanitize_tenant_country_iso(
        payload.get("tenant_country", cur.get("tenant_country"))
    )
    if "tenant_country" in payload:
        payload["tenant_country"] = effective_iso
    dial = dial_digits_for_iso(effective_iso)

    if "owner_phone_number" in payload:
        opn = payload.get("owner_phone_number")
        if opn is None:
            payload["owner_phone_number"] = None
        elif isinstance(opn, dict):
            pn = PhoneUtil.normalize_phone_number(opn)
            if not pn:
                payload["owner_phone_number"] = None
            else:
                PhoneUtil.validate(pn)
                payload["owner_phone_number"] = pn
    if "owner_phone" in payload and "owner_phone_number" not in payload:
        op = payload.get("owner_phone")
        if op is None or str(op).strip() == "":
            payload["owner_phone_number"] = None
        else:
            payload["owner_phone_number"] = PhoneUtil.from_raw(str(op).strip(), dial)
    payload.pop("owner_phone", None)


# ============================================================
# TenantService
# ============================================================

class TenantService:

    # --------------------------------------------------------
    # Listing
    # --------------------------------------------------------

    @staticmethod
    def list_tenants() -> List[Dict[str, Any]]:
        tenants = tenant_repo.list_all()
        return [
            {
                "tenant": t.id,
                "category": t.category,
                "owner_email": t.owner_email,
                "owner_phone_number": PhoneUtil.normalize_phone_number(
                    getattr(t, "owner_phone_number", None)
                ),
                "tenant_country": getattr(t, "tenant_country", None) or DEFAULT_TENANT_COUNTRY_ISO2,
                "tz": t.tz,
                "invoice_delivery": getattr(t, "invoice_delivery", "both"),
                "active": t.active,
            }
            for t in tenants
        ]

    # --------------------------------------------------------
    # Settings Retrieval
    # --------------------------------------------------------

    @staticmethod
    def get_tenant_settings(tenant: str) -> Optional[Dict[str, Any]]:
        from app.core.cache import cache_get_tenant_settings, cache_set_tenant_settings
        cached = cache_get_tenant_settings(tenant)
        if cached is not None:
            return cached

        t_model = tenant_repo.find_by_id(tenant)
        if not t_model:
            return None

        doc = t_model.dict(by_alias=True)
        doc["tenant"] = doc.get("_id", tenant)
        doc["active"] = bool(doc.get("active", True))

        # Normalize modules & capabilities
        doc["modules"] = _normalize_modules(doc.get("modules"))
        doc["capabilities"] = _normalize_capabilities(doc.get("capabilities"))

        # Store enabled default
        doc.setdefault("store_enabled", True)

        # Payment / Delivery / WhatsApp / SMTP
        doc["payment_config"] = _normalize_payment_config(doc.get("payment_config"))
        doc["delivery_config"] = _normalize_delivery_config(doc.get("delivery_config"))
        doc["whatsapp_config"] = _normalize_whatsapp_config(doc.get("whatsapp_config"))
        doc["smtp_config"] = _normalize_smtp_config(doc.get("smtp_config"))

        doc.setdefault("date_format", DEFAULT_DISPLAY_DATE_FORMAT)
        doc.setdefault("currency", "INR")
        doc["tenant_country"] = _sanitize_tenant_country_iso(doc.get("tenant_country"))
        pn = PhoneUtil.normalize_phone_number(doc.get("owner_phone_number"))
        if not pn and doc.get("owner_phone"):
            try:
                dial = dial_digits_for_iso(doc.get("tenant_country"))
                pn = PhoneUtil.from_raw(str(doc["owner_phone"]), dial)
            except Exception:
                pn = None
        if pn:
            doc["owner_phone_number"] = pn
        else:
            doc["owner_phone_number"] = doc.get("owner_phone_number")
        doc.pop("owner_phone", None)

        # Messaging channels and SMS config (so UI and SMS toggle persist correctly)
        ch = doc.get("messaging_channels")
        if not isinstance(ch, dict):
            ch = {}
        doc["messaging_channels"] = {
            "email": ch.get("email", True),
            "whatsapp": ch.get("whatsapp", True),
            "sms": bool(ch.get("sms", False)),
        }
        sc = doc.get("sms_config")
        if not isinstance(sc, dict):
            sc = {}
        doc["sms_config"] = {
            "enabled": bool(sc.get("enabled", False)),
            "provider": str(sc.get("provider", "twilio")).strip() or "twilio",
            "from_number": str(sc.get("from_number", "")).strip(),
            "account_sid": str(sc.get("account_sid", "")).strip(),
            "auth_token": str(sc.get("auth_token", "")).strip(),
        }

        # message_templates: from tenant_message_templates collection (merged with defaults)
        from app.services.core.tenant_message_templates_service import get_templates_for_tenant
        doc["message_templates"] = get_templates_for_tenant(tenant)
        # Address & location (tenant collection; used in booking messages / map link)
        doc.setdefault("address", doc.get("address") or "")
        doc.setdefault("location", doc.get("location") or "")

        cache_set_tenant_settings(tenant, doc)
        return doc

    # --------------------------------------------------------
    # Settings Update
    # --------------------------------------------------------

    @staticmethod
    def update_tenant_settings(
            tenant: str,
            patch: Dict[str, Any],
            user_id: Optional[str] = None
    ) -> Dict[str, Any]:

        tenants_col = _tenants_col()

        allowed = {
            "owner_email", "owner_phone", "owner_phone_number", "tenant_country",
            "tz", "date_format", "invoice_delivery",
            "currency",  # ISO 4217 currency code displayed across all pages
            "display_name", "followup_prefs", "templates", "active", "store_enabled",
            "payment_config", "delivery_config", "whatsapp_config", "smtp_config",
            "plan", "modules", "capabilities", "appointments", "ai_config",
            "messaging_channels", "sms_config", "faq",
            "address", "location",  # business address and map link for messages
        }

        payload = {k: v for k, v in (patch or {}).items() if k in allowed}

        if payload and (
            {"owner_phone", "owner_phone_number", "tenant_country"} & set(payload.keys())
        ):
            _merge_tenant_phone_payload(tenant, payload)

        # Normalize messaging_channels and sms_config so they persist correctly
        if "messaging_channels" in payload and isinstance(payload["messaging_channels"], dict):
            ch = payload["messaging_channels"]
            payload["messaging_channels"] = {
                "email": bool(ch.get("email", True)),
                "whatsapp": bool(ch.get("whatsapp", True)),
                "sms": bool(ch.get("sms", False)),
            }
        if "sms_config" in payload and isinstance(payload["sms_config"], dict):
            sc = payload["sms_config"]
            payload["sms_config"] = {
                "enabled": bool(sc.get("enabled", False)),
                "provider": str(sc.get("provider", "twilio")).strip() or "twilio",
                "from_number": str(sc.get("from_number", "")).strip(),
                "account_sid": str(sc.get("account_sid", "")).strip(),
                "auth_token": str(sc.get("auth_token", "")).strip(),
            }

        # Normalize modules/capabilities
        if "modules" in payload or "capabilities" in payload:
            current = TenantService.get_tenant_settings(tenant) or {}
            mods = payload.get("modules") if "modules" in payload else current.get("modules", [])
            caps = payload.get("capabilities") if "capabilities" in payload else current.get("capabilities", [])
            if not isinstance(mods, list) or not isinstance(caps, list):
                raise ValueError("modules and capabilities must be lists")
            payload["modules"], payload["capabilities"] = normalize_selection(mods, caps)

        # Normalize WhatsApp config
        if "whatsapp_config" in payload:
            payload["whatsapp_config"] = _normalize_whatsapp_config(payload["whatsapp_config"])

        if tenants_col.find_one({"_id": tenant}) is None:
            raise ValueError("Tenant not found")

        payload["updated_at"] = utcnow()
        payload["updated_by"] = user_id

        tenants_col.find_one_and_update(
            {"_id": tenant},
            {"$set": payload},
            return_document=ReturnDocument.AFTER
        )
        from app.core.cache import cache_delete_tenant_settings
        cache_delete_tenant_settings(tenant)
        return TenantService.get_tenant_settings(tenant) or {}

    # --------------------------------------------------------
    # Tenant Creation
    # --------------------------------------------------------

    @staticmethod
    def create_tenant(
            tenant_id: str,
            name: str,
            email: str,
            phone: str,
            modules: List[str],
            capabilities: List[str],
            tz: Optional[str] = None
    ) -> Dict[str, Any]:

        mods, caps = normalize_selection(modules, capabilities)

        data = {
            "category": "salon",
            "owner_email": email,
            "owner_phone": phone,
            "tz": tz,
            "modules": mods,
            "capabilities": caps,
            "active": True,
        }

        TenantService.seed_if_absent(tenant_id, data)
        return TenantService.get_tenant_settings(tenant_id) or {}

    # --------------------------------------------------------
    # Tenant Deletion
    # --------------------------------------------------------

    @staticmethod
    def delete_tenant(tenant: str, user_id: Optional[str] = None) -> bool:
        tenants_col = _tenants_col()
        res = tenants_col.delete_one({"_id": tenant})

        if res.deleted_count == 0:
            return False
        from app.core.cache import cache_delete_tenant_settings
        cache_delete_tenant_settings(tenant)
        # Cascading delete (demo)
        _professionals_col().delete_many({"tenant": tenant})
        _appointments_col().delete_many({"tenant": tenant})
        _customers_col().delete_many({"tenant": tenant})
        _staff_col().delete_many({"tenant": tenant})

        return True

    # --------------------------------------------------------
    # Registry
    # --------------------------------------------------------

    @staticmethod
    def list_registry() -> List[Dict[str, Any]]:
        return list_registry()

    # --------------------------------------------------------
    # Misc Helpers
    # --------------------------------------------------------

    @staticmethod
    def tenant_exists(tenant: str) -> bool:
        return _tenants_col().count_documents({"_id": tenant}, limit=1) > 0

    @staticmethod
    def get_tenant(tenant: str) -> Optional[Dict[str, Any]]:
        doc = _tenants_col().find_one({"_id": tenant})
        if doc:
            doc["id"] = doc.get("_id")
        return dict(doc) if doc else None

    @staticmethod
    def get_revenue(tenant: str) -> float:
        doc = _tenants_col().find_one({"_id": tenant}, {"revenue": 1})
        return float(doc.get("revenue", 0.0)) if doc else 0.0

    # --------------------------------------------------------
    # Seeding
    # --------------------------------------------------------

    @staticmethod
    def seed_if_absent(tenant: str, data: Dict[str, Any]) -> None:
        tenants_col = _tenants_col()

        if tenants_col.find_one({"_id": tenant}):
            return

        tc = _sanitize_tenant_country_iso(data.get("tenant_country"))
        dial = dial_digits_for_iso(tc)
        owner_raw = data.get("owner_phone_number") or data.get("owner_phone")
        owner_pn = None
        if isinstance(owner_raw, dict):
            owner_pn = PhoneUtil.normalize_phone_number(owner_raw)
        elif owner_raw:
            try:
                owner_pn = PhoneUtil.from_raw(str(owner_raw).strip(), dial)
            except Exception:
                owner_pn = None
        doc = {
            "_id": tenant,
            "category": data.get("category", "salon"),
            "revenue": float(data.get("revenue", 0.0)),
            "cancellations": int(data.get("cancellations", 0)),
            "created_at": utcnow(),
            "tenant_country": tc,
            "owner_email": data.get("owner_email"),
            "owner_phone_number": owner_pn,
            "tz": data.get("tz"),
            "modules": data.get("modules") or [],
            "capabilities": data.get("capabilities") or [],
            "active": True,
            "whatsapp_config": data.get("whatsapp_config", {}),
            "payment_config": data.get("payment_config", {}),
            "delivery_config": data.get("delivery_config", {}),
            "smtp_config": data.get("smtp_config", {}),
            "date_format": data.get("date_format", DEFAULT_DISPLAY_DATE_FORMAT),
        }

        tenants_col.insert_one(doc)

    # --------------------------------------------------------
    # Active Flag Repair
    # --------------------------------------------------------

    @staticmethod
    def ensure_active_flags() -> Dict[str, int]:
        pros_col = _professionals_col()
        cust_col = _customers_col()

        pros_result = pros_col.update_many({"active": {"$exists": False}}, {"$set": {"active": True}})
        cust_result = cust_col.update_many({"active": {"$exists": False}}, {"$set": {"active": True}})

        return {
            "professionals_updated": pros_result.modified_count,
            "customers_updated": cust_result.modified_count,
        }

    # --------------------------------------------------------
    # WhatsApp Helpers
    # --------------------------------------------------------

    @staticmethod
    def resolve_tenant_by_whatsapp_number(number: str) -> Optional[str]:
        """Resolve tenant ID from WhatsApp from_number (e.g. whatsapp:+1234567890)."""
        tenants_col = _tenants_col()
        if not number:
            return None
        num = number if str(number).lower().startswith("whatsapp:") else f"whatsapp:{number}"
        doc = tenants_col.find_one({"whatsapp_config.from_number": num})
        if not doc:
            return None
        return str(doc.get("_id"))

    # --------------------------------------------------------
    # Country Code Helper
    # --------------------------------------------------------

    @staticmethod
    def _get_tenant_country_code(tenant: str) -> Optional[str]:
        """ITU dial digits for tenant (e.g. '91' for India) from tenant_country; default India."""
        settings = TenantService.get_tenant_settings(tenant) or {}
        if settings.get("default_country_code"):
            return re.sub(r"\D", "", str(settings["default_country_code"]))
        return dial_digits_for_iso(settings.get("tenant_country"))
