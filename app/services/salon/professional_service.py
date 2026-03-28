# app/services/salon/professional_service.py
from __future__ import annotations
from typing import List, Optional, Dict, Any

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
    def _generate_prof_short(tenant: str, name: str) -> str:
        """Generate a short name from the professional's name for ID prefixes."""
        import re
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
    def get_professional(tenant: str, name: str) -> Optional[Dict[str, Any]]:
        prof = prof_repo.find_by_name(tenant, name)
        return prof.dict() if prof else None

    @staticmethod
    def update_professional(
            tenant: str,
            name: str,
            patch: Dict[str, Any],
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        pros_col = ProfessionalService._pros_col()

        allowed = {"price", "active", "availability_criteria", "available_days", "services", "phone", "degree",
                   "address", "bio"}
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

    @staticmethod
    def get_slots(tenant: str, professional: str) -> List[Slot]:
        p = ProfessionalService.get_professional(tenant, professional)
        return p.slots if p else []

    @staticmethod
    def list_professionals_full(tenant: str, active: Optional[bool] = None) -> List[Dict[str, Any]]:
        pros = prof_repo.list_by_tenant(tenant, active)
        return [p.dict() for p in pros]

    @staticmethod
    def set_professional_active(tenant: str, name: str, active: bool) -> bool:
        pros_col = ProfessionalService._pros_col()
        res = pros_col.update_one({"tenant": tenant, "name": name}, {"$set": {"active": bool(active)}})
        return res.modified_count > 0

    @staticmethod
    def add_professional(
            tenant: str,
            name: str,
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

        short_name = ProfessionalService._generate_prof_short(tenant, name)
        now = utcnow()
        doc = {
            "tenant": tenant,
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
                raise ValueError("Professional already exists")
            raise
        return Professional(
            name=name,
            price=float(price or 0.0),
            slots=slots or [],
            active=bool(active),
            availability_criteria=availability_criteria,
            available_days=available_days or [],
            phone=kwargs.get("phone"),
            degree=kwargs.get("degree"),
            address=kwargs.get("address"),
            bio=kwargs.get("bio")
        )

    @staticmethod
    def update_professional_slots(tenant: str, professional: str, slots: List[Slot], date_str: Optional[str] = None,
                                  user_id: Optional[str] = None) -> Professional:
        pros_col = ProfessionalService._pros_col()
        # Ensure professional exists
        doc = pros_col.find_one({"tenant": tenant, "name": professional})
        if not doc:
            raise ValueError("Professional not found")
        if not bool(doc.get("active", True)):
            raise ValueError("Professional is inactive")

        slot_data = [{"time": s.time, "status": s.status} for s in (slots or [])]

        update_payload: Dict[str, Any] = {
            "updated_at": utcnow(),
            "updated_by": user_id
        }

        if date_str:
            pros_col.update_one(
                {"tenant": tenant, "name": professional},
                {
                    "$set": {
                        f"date_overrides.{date_str}": slot_data,
                        **update_payload
                    }
                },
            )
        else:
            pros_col.update_one(
                {"tenant": tenant, "name": professional},
                {
                    "$set": {
                        "slots": slot_data,
                        **update_payload
                    }
                },
            )
        return Professional(name=professional, price=float(doc.get("price", 0.0)), slots=slots)
