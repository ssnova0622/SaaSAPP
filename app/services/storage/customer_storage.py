"""MongoDB storage for customers (per-tenant)."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from pymongo import ReturnDocument

from app.helpers.phone_util import PhoneUtil
from app.helpers.date_utils import utcnow
from app.services.db import customers_collection

logger = logging.getLogger(__name__)


class CustomerStorage:
    """Requires TenantStorage in MRO for _get_tenant_country_code."""

    @classmethod
    def upsert_customer(
        cls,
        tenant: str,
        name: str,
        phone: str,
        email: Optional[str] = None,
        tags: Optional[List[str]] = None,
        active: Optional[bool] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        col = customers_collection()
        cc = cls._get_tenant_country_code(tenant) or PhoneUtil.DEFAULT_DIAL_DIGITS
        struct = PhoneUtil.prepare_storage(str(phone).strip(), cc)
        if not struct:
            raise ValueError("Invalid phone")
        name = (name or "").strip()
        email = (email or "").strip() if email else None
        tags = [t.strip() for t in (tags or []) if t and isinstance(t, str)]
        if not tenant:
            raise ValueError("tenant and phone are required")
        now = utcnow()
        flt = PhoneUtil.customer_filter(tenant, struct)
        set_payload: Dict[str, Any] = {
            "tenant": tenant,
            "phone_number": struct,
            "name": name,
            "email": email,
            "tags": tags,
            "updated_at": now,
            "updated_by": user_id,
        }
        if active is not None:
            set_payload["active"] = bool(active)
        update_doc = {
            "$set": set_payload,
            "$unset": {"phone": ""},
            "$setOnInsert": {"created_at": now, "active": True, "created_by": user_id},
        }
        col.update_one(flt, update_doc, upsert=True)
        doc = col.find_one(flt, {"_id": 0})
        out = dict(doc or {})
        out["active"] = bool(out.get("active", True))
        return out

    @classmethod
    def list_customers(
        cls,
        tenant: str,
        search: Optional[str] = None,
        tag: Optional[str] = None,
        active: Optional[bool] = None,
        page: int = 1,
        size: int = 50,
    ) -> Dict[str, Any]:
        col = customers_collection()
        q: Dict[str, Any] = {"tenant": tenant}
        if search:
            cc = cls._get_tenant_country_code(tenant) or PhoneUtil.DEFAULT_DIAL_DIGITS
            norm_search = PhoneUtil.normalize_e164_input(search, cc)
            name_pattern = re.escape(search)
            email_pattern = re.escape(search)
            phone_or_conditions: List[Dict[str, Any]] = []
            if norm_search.startswith("+"):
                digits = norm_search[1:]
                phone_regex = "^\\s*\\+?" + re.escape(digits)
                phone_or_conditions.append({"phone": {"$regex": phone_regex, "$options": "i"}})
                try:
                    pn = PhoneUtil.prepare_storage(search.strip(), cc)
                    if pn:
                        phone_or_conditions.append(
                            {
                                "phone_number.code": pn["code"],
                                "phone_number.number": pn["number"],
                            }
                        )
                except ValueError:
                    pass
                try:
                    num_val = int(digits)
                    phone_or_conditions.append({"phone": norm_search})
                    phone_or_conditions.append({"phone": num_val})
                except Exception as e:
                    logger.debug("Phone search int parse skipped: %s", e)
            else:
                phone_or_conditions.append(
                    {"phone": {"$regex": re.escape(search), "$options": "i"}}
                )
                try:
                    pn = PhoneUtil.prepare_storage(search.strip(), cc)
                    if pn:
                        phone_or_conditions.append(
                            {
                                "phone_number.code": pn["code"],
                                "phone_number.number": pn["number"],
                            }
                        )
                except ValueError:
                    pass
            q["$or"] = [
                {"name": {"$regex": name_pattern, "$options": "i"}},
                {"email": {"$regex": email_pattern, "$options": "i"}},
                *phone_or_conditions,
            ]
        if tag:
            q["tags"] = tag
        if active is True:
            q["active"] = True
        elif active is False:
            q["active"] = False
        page = max(1, int(page or 1))
        size = max(1, min(200, int(size or 50)))
        skip = (page - 1) * size
        total = col.count_documents(q)
        items: List[Dict[str, Any]] = []
        for d in col.find(q, {"_id": 0}).sort("name", 1).skip(skip).limit(size):
            row = dict(d)
            row["active"] = bool(row.get("active", True))
            items.append(row)
        return {"items": items, "total": total, "page": page, "size": size}

    @classmethod
    def set_customer_active(
        cls,
        tenant: str,
        phone: str,
        active: bool,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        col = customers_collection()
        cc = cls._get_tenant_country_code(tenant) or PhoneUtil.DEFAULT_DIAL_DIGITS
        struct = PhoneUtil.prepare_storage(str(phone).strip(), cc)
        if not struct:
            raise ValueError("Invalid phone")
        flt = PhoneUtil.customer_filter(tenant, struct)
        res = col.find_one_and_update(
            flt,
            {
                "$set": {"active": bool(active), "updated_at": utcnow(), "updated_by": user_id},
                "$unset": {"phone": ""},
            },
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        if not res:
            raise ValueError("Customer not found")
        out = dict(res)
        out["active"] = bool(out.get("active", True))
        return out
