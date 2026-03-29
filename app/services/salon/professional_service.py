# app/services/salon/professional_service.py
from __future__ import annotations
from typing import List, Optional, Dict, Any
import re

from app.helpers.date_utils import utcnow
import datetime as dt
from pymongo import ReturnDocument
from app.repositories.professional_repository import ProfessionalRepository
from app.services.storage import Slot, Professional

prof_repo = ProfessionalRepository()


class ProfessionalService:
    @staticmethod
    def _pros_col():
        from app.services.db import get_db
        return get_db().get_collection("professionals")

    @staticmethod
    def resolve_professional_raw(tenant: str, key: str) -> Dict[str, Any]:
        """
        Resolve API path key to a professional document.
        Prefer ``professional_id`` (stable key from tenant + name + short_name, or legacy UUID);
        fall back to display ``name`` when needed.
        """
        key = (key or "").strip()
        if not key:
            raise ValueError("Professional not found")
        pros_col = ProfessionalService._pros_col()
        doc = pros_col.find_one({"tenant": tenant, "professional_id": key})
        if doc:
            out = dict(doc)
            out.pop("_id", None)
            return out
        matches = list(pros_col.find({"tenant": tenant, "name": key}))
        if len(matches) > 1:
            raise ValueError(
                f"Multiple professionals named {key!r}; use each row's professional_id from "
                f"GET /v1/tenants/{{tenant}}/professionals/full in API paths."
            )
        if len(matches) == 1:
            out = dict(matches[0])
            out.pop("_id", None)
            return out
        raise ValueError("Professional not found")

    @staticmethod
    def appointment_match_query(prof_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Mongo fragment: appointments for this professional (new ``professional_id`` or legacy name-only rows)."""
        pid = (prof_doc.get("professional_id") or "").strip()
        name = prof_doc.get("name") or ""
        if not pid:
            return {"professional": name}
        return {
            "$or": [
                {"professional_id": pid},
                {
                    "$and": [
                        {"professional": name},
                        {
                            "$or": [
                                {"professional_id": {"$exists": False}},
                                {"professional_id": None},
                                {"professional_id": ""},
                            ]
                        },
                    ]
                },
            ]
        }

    @staticmethod
    def _pro_filter(prof_doc: Dict[str, Any]) -> Dict[str, Any]:
        return {"tenant": prof_doc["tenant"], "professional_id": prof_doc["professional_id"]}
    @staticmethod
    def _generate_prof_short(tenant: str, name: str) -> str:
        """Generate a short name from the professional's name for ID prefixes."""
        parts = re.split(r'\s+', name.strip())
        
        # Trial 0: Initials
        if len(parts) >= 2:
            base = (parts[0][0] + parts[1][0]).upper()
        else:
            base = parts[0][:2].upper()
            
        pros_col = ProfessionalService._pros_col()
        
        if not pros_col.find_one({"tenant": tenant, "short_name": base}):
            return base
            
        # Trial 1: parts[0][0] + parts[1][:2]
        if len(parts) >= 2:
            t1 = (parts[0][0] + parts[1][:2]).upper()
            if not pros_col.find_one({"tenant": tenant, "short_name": t1}):
                return t1
                
        # Trial 2: parts[0][:2] + parts[1][0]
        if len(parts) >= 2:
            t2 = (parts[0][:2] + parts[1][0]).upper()
            if not pros_col.find_one({"tenant": tenant, "short_name": t2}):
                return t2
                
        # Trial 3: base + digits
        count = 1
        while True:
            t3 = f"{base}{count}"
            if not pros_col.find_one({"tenant": tenant, "short_name": t3}):
                return t3
            count += 1

    @staticmethod
    def build_professional_id(tenant: str, name: str, short_name: str) -> str:
        """URL-safe id: slug(tenant)__slug(name)__sanitized(short_name)."""

        def slug(s: str, max_len: int) -> str:
            x = (s or "").strip().lower()
            x = re.sub(r"[^a-z0-9]+", "-", x)
            x = re.sub(r"-+", "-", x).strip("-") or "x"
            x = x[:max_len].rstrip("-") or "x"
            return x

        sh = re.sub(r"[^a-z0-9]+", "", (short_name or "").strip().lower())
        sh = (sh[:16] if sh else "") or "xx"
        return f"{slug(tenant, 48)}__{slug(name, 64)}__{sh}"

    @staticmethod
    def allocate_professional_id(
        tenant: str,
        name: str,
        short_name: str,
        pros_col: Any,
    ) -> str:
        """Assign a unique ``professional_id`` under ``tenant``; suffix if the base composite exists."""
        import uuid

        base = ProfessionalService.build_professional_id(tenant, name, short_name)
        candidate = base
        n = 0
        while pros_col.find_one({"tenant": tenant, "professional_id": candidate}):
            n += 1
            if n <= 999:
                candidate = f"{base}__{n}"
            else:
                candidate = f"{base}__{uuid.uuid4().hex[:10]}"
        return candidate

    @staticmethod
    def get_professionals(tenant: str) -> List[Professional]:
        return prof_repo.list_by_tenant(tenant)

    @staticmethod
    def filter_professionals(
            tenant: str,
            date_str: Optional[str] = None,
            service: Optional[str] = None,
    ) -> List[str]:
        pros = ProfessionalService.get_professionals(tenant)
        assigned: List[str] = []
        general: List[str] = []

        for pro in pros:
            name_s = pro.name
            bucket: Optional[List[str]] = None
            if service:
                pro_services = pro.services or []
                normalized = [str(s).lower() for s in pro_services]
                requested = str(service).lower()

                if normalized:
                    if requested not in normalized:
                        continue
                    bucket = assigned
                else:
                    bucket = general
            else:
                bucket = assigned

            if date_str:
                try:
                    day = dt.date.fromisoformat(date_str)
                    crit = pro.availability_criteria or "daily"
                    days_cfg = pro.available_days or []
                    is_avail = True
                    if crit == "weekly" and days_cfg and day.weekday() not in days_cfg:
                        is_avail = False
                    elif crit == "monthly" and days_cfg and day.day not in days_cfg:
                        is_avail = False
                    if not is_avail:
                        continue
                except Exception:
                    pass

            if name_s not in bucket and name_s not in assigned and name_s not in general:
                bucket.append(name_s)

        return assigned + general

    @staticmethod
    def get_professional(tenant: str, key: str) -> Optional[Dict[str, Any]]:
        try:
            return ProfessionalService.resolve_professional_raw(tenant, key)
        except ValueError:
            return None

    @staticmethod
    def update_professional(
            tenant: str,
            key: str,
            patch: Dict[str, Any],
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        pros_col = ProfessionalService._pros_col()
        prof_doc = ProfessionalService.resolve_professional_raw(tenant, key)
        filt = ProfessionalService._pro_filter(prof_doc)
        my_pid = prof_doc.get("professional_id")

        allowed = {"price", "active", "availability_criteria", "available_days", "services", "phone", "degree",
                   "address", "bio", "name", "employee_id"}
        payload = {k: v for k, v in patch.items() if k in allowed}

        if not payload:
            doc = pros_col.find_one(filt, {"_id": 0})
            if not doc:
                raise ValueError("Professional not found")
            return dict(doc)

        if "name" in payload:
            nm = str(payload["name"]).strip()
            if not nm:
                raise ValueError("name must not be empty")
            payload["name"] = nm
            clash = pros_col.find_one({"tenant": tenant, "name": nm})
            if clash and clash.get("professional_id") != my_pid:
                raise ValueError("A professional with this name already exists for this tenant.")
        if "employee_id" in payload:
            eid = str(payload["employee_id"]).strip()
            if not eid:
                raise ValueError("employee_id must not be empty")
            payload["employee_id"] = eid
            clash = pros_col.find_one({"tenant": tenant, "employee_id": eid})
            if clash and clash.get("professional_id") != my_pid:
                raise ValueError("A professional with this employee id already exists for this tenant.")

        payload["updated_at"] = utcnow()
        payload["updated_by"] = user_id

        try:
            doc = pros_col.find_one_and_update(
                filt,
                {"$set": payload},
                return_document=ReturnDocument.AFTER,
                projection={"_id": 0},
            )
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
                raise ValueError("Update failed due to a duplicate value.") from e
        if not doc:
            raise ValueError("Professional not found")

        out = dict(doc)
        out["active"] = bool(out.get("active", True))
        return out

    @staticmethod
    def get_slots(tenant: str, professional: str) -> List[Slot]:
        p = ProfessionalService.get_professional(tenant, professional)
        if not p:
            return []
        raw = p.get("slots") if isinstance(p, dict) else []
        out: List[Slot] = []
        for s in raw or []:
            if isinstance(s, dict):
                out.append(Slot(time=str(s.get("time", "")), status=str(s.get("status", "available"))))
        return out

    @staticmethod
    def list_professionals_full(tenant: str, active: Optional[bool] = None) -> List[Dict[str, Any]]:
        pros = prof_repo.list_by_tenant(tenant, active)
        return [p.dict() for p in pros]

    @staticmethod
    def set_professional_active(tenant: str, key: str, active: bool) -> bool:
        pros_col = ProfessionalService._pros_col()
        prof_doc = ProfessionalService.resolve_professional_raw(tenant, key)
        res = pros_col.update_one(
            ProfessionalService._pro_filter(prof_doc),
            {"$set": {"active": bool(active)}},
        )
        return res.modified_count > 0

    @staticmethod
    def add_professional(
            tenant: str,
            name: str,
            employee_id: str,
            price: float = 0.0,
            slots: Optional[List[Slot]] = None,
            active: bool = True,
            user_id: Optional[str] = None,
            availability_criteria: str = "daily",
            available_days: Optional[List[int]] = None,
            **kwargs
    ) -> Professional:
        pros_col = ProfessionalService._pros_col()
        from app.services.core.tenant_service import TenantService
        if not TenantService.tenant_exists(tenant):
            raise ValueError("Tenant not found")

        eid = (employee_id or "").strip()
        if not eid:
            raise ValueError("employee_id is required")

        if pros_col.find_one({"tenant": tenant, "name": name}):
            raise ValueError("A professional with this name already exists for this tenant.")
        if pros_col.find_one({"tenant": tenant, "employee_id": eid}):
            raise ValueError("A professional with this employee id already exists for this tenant.")

        short_name = ProfessionalService._generate_prof_short(tenant, name)
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
            "availability_criteria": availability_criteria,
            "available_days": available_days or [],
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
            slots=slots or [],
            active=bool(active),
            availability_criteria=availability_criteria,
            available_days=available_days or [],
            services=kwargs.get("services") or [],
            phone=kwargs.get("phone"),
            degree=kwargs.get("degree"),
            address=kwargs.get("address"),
            bio=kwargs.get("bio"),
        )

    @staticmethod
    def update_professional_slots(tenant: str, key: str, slots: List[Slot], date_str: Optional[str] = None,
                                  user_id: Optional[str] = None) -> Professional:
        pros_col = ProfessionalService._pros_col()
        doc = ProfessionalService.resolve_professional_raw(tenant, key)
        if not bool(doc.get("active", True)):
            raise ValueError("Professional is inactive")

        filt = ProfessionalService._pro_filter(doc)
        slot_data = [{"time": s.time, "status": s.status} for s in (slots or [])]

        update_payload: Dict[str, Any] = {
            "updated_at": utcnow(),
            "updated_by": user_id
        }

        if date_str:
            pros_col.update_one(
                filt,
                {
                    "$set": {
                        f"date_overrides.{date_str}": slot_data,
                        **update_payload
                    }
                },
            )
        else:
            pros_col.update_one(
                filt,
                {
                    "$set": {
                        "slots": slot_data,
                        **update_payload
                    }
                },
            )
        return Professional(
            name=str(doc.get("name") or ""),
            professional_id=str(doc.get("professional_id") or ""),
            employee_id=str(doc.get("employee_id") or "") or None,
            short_name=doc.get("short_name"),
            price=float(doc.get("price", 0.0)),
            slots=slots,
            active=bool(doc.get("active", True)),
            availability_criteria=str(doc.get("availability_criteria") or "daily"),
            available_days=list(doc.get("available_days") or []),
            services=list(doc.get("services") or []),
            phone=doc.get("phone"),
            degree=doc.get("degree"),
            address=doc.get("address"),
            bio=doc.get("bio"),
        )
