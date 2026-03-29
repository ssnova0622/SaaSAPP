"""MongoDB persistence for salon professionals (stylists, doctors) and slots.

Used by Storage (storage_mongo) for backward compatibility; colocated with salon services.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from pymongo import ReturnDocument

from app.helpers.date_utils import utcnow
from app.services.db import collections
from app.services.salon.professional_service import ProfessionalService
from app.services.storage.models import Professional, Slot

logger = logging.getLogger(__name__)


class ProfessionalStorage:
    @classmethod
    def add_professional(
        cls,
        tenant: str,
        name: str,
        employee_id: str,
        price: float,
        slots: List[Slot],
        active: bool = True,
        user_id: Optional[str] = None,
        **kwargs,
    ) -> Professional:
        tenants_col, pros_col, _appts = collections()
        if tenants_col.find_one({"_id": tenant}) is None:
            raise ValueError("Tenant not found")

        eid = (employee_id or "").strip()
        if not eid:
            raise ValueError("employee_id is required")
        if pros_col.find_one({"tenant": tenant, "name": name}):
            raise ValueError("A professional with this name already exists for this tenant.")
        if pros_col.find_one({"tenant": tenant, "employee_id": eid}):
            raise ValueError("A professional with this employee id already exists for this tenant.")

        short_name = cls._generate_prof_short(tenant, name)
        now = utcnow()
        professional_id = ProfessionalService.allocate_professional_id(
            tenant, name, short_name, pros_col
        )

        doc = {
            "tenant": tenant,
            "professional_id": professional_id,
            "employee_id": eid,
            "name": name,
            "short_name": short_name,
            "price": float(price or 0.0),
            "slots": [{"time": s.time, "status": s.status} for s in (slots or [])],
            "active": bool(active),
            "availability_criteria": kwargs.get("availability_criteria", "daily"),
            "available_days": kwargs.get("available_days", []),
            "services": kwargs.get("services", []),
            "phone": kwargs.get("phone"),
            "degree": kwargs.get("degree"),
            "address": kwargs.get("address"),
            "bio": kwargs.get("bio"),
            "created_at": now,
            "updated_at": now,
            "created_by": user_id,
            "updated_by": user_id,
        }
        try:
            pros_col.insert_one(doc)
        except Exception as e:
            if getattr(e, "code", None) == 11000 or "E11000" in str(e):
                err = str(e)
                if "employee_id" in err:
                    raise ValueError(
                        "A professional with this employee id already exists for this tenant."
                    ) from e
                if "name" in err:
                    raise ValueError(
                        "A professional with this name already exists for this tenant."
                    ) from e
                raise ValueError("Professional id collision; retry") from e
            raise
        return Professional(
            name=name,
            professional_id=professional_id,
            employee_id=eid,
            short_name=short_name,
            price=float(price or 0.0),
            slots=slots,
            active=bool(active),
            availability_criteria=str(kwargs.get("availability_criteria") or "daily"),
            available_days=list(kwargs.get("available_days") or []),
            services=list(kwargs.get("services") or []),
            phone=kwargs.get("phone"),
            degree=kwargs.get("degree"),
            address=kwargs.get("address"),
            bio=kwargs.get("bio"),
        )

    @classmethod
    def update_professional_slots(
        cls,
        tenant: str,
        name: str,
        slots: List[Slot],
        date_str: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Professional:
        tenants_col, pros_col, _appts = collections()
        doc = pros_col.find_one({"tenant": tenant, "name": name})
        if not doc:
            raise ValueError("Professional not found")
        if not bool(doc.get("active", True)):
            raise ValueError("Professional is inactive")

        slot_data = [{"time": s.time, "status": s.status} for s in (slots or [])]
        update_payload: Dict[str, Any] = {"updated_at": utcnow(), "updated_by": user_id}

        if date_str:
            pros_col.update_one(
                {"tenant": tenant, "name": name},
                {"$set": {f"date_overrides.{date_str}": slot_data, **update_payload}},
            )
        else:
            pros_col.update_one(
                {"tenant": tenant, "name": name},
                {"$set": {"slots": slot_data, **update_payload}},
            )
        return Professional(name=name, price=float(doc.get("price", 0.0)), slots=slots)

    @classmethod
    def get_professionals(cls, tenant: str) -> List[Professional]:
        _tenants, pros_col, _appts = collections()
        pros: List[Professional] = []
        for doc in pros_col.find({"tenant": tenant}).sort("name", 1):
            pros.append(
                Professional(
                    name=doc["name"],
                    price=float(doc.get("price", 0.0)),
                    slots=[Slot(**s) for s in doc.get("slots", [])],
                    active=bool(doc.get("active", True)),
                    availability_criteria=doc.get("availability_criteria", "daily"),
                    available_days=doc.get("available_days", []),
                    services=doc.get("services", []),
                    phone=doc.get("phone"),
                    degree=doc.get("degree"),
                    address=doc.get("address"),
                    bio=doc.get("bio"),
                )
            )
        return pros

    @classmethod
    def get_professional(cls, tenant: str, name: str) -> Optional[Professional]:
        _tenants, pros_col, _appts = collections()
        doc = pros_col.find_one({"tenant": tenant, "name": name})
        if not doc:
            return None
        return Professional(
            name=doc["name"],
            price=float(doc.get("price", 0.0)),
            slots=[Slot(**s) for s in doc.get("slots", [])],
            active=bool(doc.get("active", True)),
            date_overrides=doc.get("date_overrides", {}),
            availability_criteria=doc.get("availability_criteria", "daily"),
            available_days=doc.get("available_days", []),
            services=doc.get("services", []),
            phone=doc.get("phone"),
            degree=doc.get("degree"),
            address=doc.get("address"),
            bio=doc.get("bio"),
        )

    @classmethod
    def list_professionals_full(
        cls, tenant: str, active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        _tenants, pros_col, _appts = collections()
        q: Dict[str, Any] = {"tenant": tenant}
        if active is True:
            q["active"] = True
        elif active is False:
            q["active"] = False
        items: List[Dict[str, Any]] = []
        for doc in pros_col.find(q, {"_id": 0}).sort("name", 1):
            row = dict(doc)
            row["active"] = bool(row.get("active", True))
            items.append(row)
        return items

    @classmethod
    def set_professional_active(
        cls, tenant: str, name: str, active: bool
    ) -> Dict[str, Any]:
        _tenants, pros_col, _appts = collections()
        doc = pros_col.find_one_and_update(
            {"tenant": tenant, "name": name},
            {"$set": {"active": bool(active)}},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        if not doc:
            raise ValueError("Professional not found")
        out = dict(doc)
        out["active"] = bool(out.get("active", True))
        return out

    @classmethod
    def update_professional(
        cls,
        tenant: str,
        name: str,
        patch: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        _tenants, pros_col, _appts = collections()
        allowed = {
            "price",
            "active",
            "availability_criteria",
            "available_days",
            "services",
            "phone",
            "degree",
            "address",
            "bio",
        }
        payload = {k: v for k, v in patch.items() if k in allowed}
        if not payload:
            doc = pros_col.find_one({"tenant": tenant, "name": name}, {"_id": 0})
            if not doc:
                raise ValueError("Professional not found")
            return dict(doc)

        payload["updated_at"] = utcnow()
        payload["updated_by"] = user_id
        doc = pros_col.find_one_and_update(
            {"tenant": tenant, "name": name},
            {"$set": payload},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        if not doc:
            raise ValueError("Professional not found")
        out = dict(doc)
        out["active"] = bool(out.get("active", True))
        return out

    @classmethod
    def list_slots(cls, tenant: str, professional: str) -> List[Slot]:
        p = cls.get_professional(tenant, professional)
        return p.slots if p else []

    @classmethod
    def _generate_prof_short(cls, tenant: str, name: str) -> str:
        if not name:
            return "XX"
        parts = [p.strip() for p in name.split() if p.strip()]
        base = "XX"
        if len(parts) >= 2:
            base = (parts[0][0] + parts[1][0]).upper()
        elif len(parts) == 1:
            base = (parts[0][:2]).upper()
            if len(base) < 2:
                base = (base + "X").upper()

        _tenants, pros_col, _appts = collections()
        existing_shorts = {
            str(p.get("short_name")).upper()
            for p in pros_col.find({"tenant": tenant}, {"short_name": 1})
            if p.get("short_name")
        }
        if base not in existing_shorts:
            return base
        if len(parts) >= 2:
            trial = (parts[0][0] + parts[1][:2]).upper()
            if trial not in existing_shorts:
                return trial
            trial = (parts[0][:2] + parts[1][0]).upper()
            if trial not in existing_shorts:
                return trial
        elif len(parts) == 1:
            trial = (parts[0][:3]).upper()
            if trial not in existing_shorts:
                return trial
        for i in range(1, 10):
            trial = f"{base}{i}"
            if trial not in existing_shorts:
                return trial
        return base
