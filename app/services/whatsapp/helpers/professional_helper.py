# app/services/whatsapp/helpers/professional_helper.py
from __future__ import annotations
import datetime as dt
from typing import List, Optional

from app.services.salon.professional_service import ProfessionalService


def list_professionals(
        tenant: str,
        date: Optional[str] = None,
        service: Optional[str] = None,
) -> List[str]:
    """Return professionals filtered by date and service."""
    try:
        pros = ProfessionalService.get_professionals(tenant)
    except Exception:
        return []

    assigned, general = [], []

    for pro in pros:
        name = getattr(pro, "name", None) or pro.get("name")
        if not name:
            continue

        # Service filtering
        if service:
            pro_services = getattr(pro, "services", None) or pro.get("services") or []
            normalized = [str(s).lower() for s in pro_services]
            if normalized:
                if service.lower() not in normalized:
                    continue
                bucket = assigned
            else:
                bucket = general
        else:
            bucket = assigned

        # Date filtering
        if date:
            try:
                d = dt.date.fromisoformat(date)
                crit = getattr(pro, "availability_criteria", "daily")
                days = getattr(pro, "available_days", [])
                if crit == "weekly" and days and d.weekday() not in days:
                    continue
                if crit == "monthly" and days and d.day not in days:
                    continue
            except Exception:
                pass

        if name not in bucket:
            bucket.append(name)

    return assigned + general
