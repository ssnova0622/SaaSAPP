# app/services/salon/appointments/listing_service.py
"""
Listing and serialization of appointments with tenant-aware date display and search.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import datetime as dt
import re

from app.helpers.tools import uuid4
from app.services.core.tenant_service import TenantService
from app.services.core.user_service import UserService
from app.services.db import collections
from app.services.storage.appointment_storage import Appointment
from app.helpers.constants import SLOT_STATUS_BLOCKED
from app.helpers.date_utils import format_date_for_display, get_tenant_timezone_zoneinfo, utcnow
from app.helpers.phone_utils import normalize_phone
from app.services.salon.professional_service import ProfessionalService

logger = logging.getLogger(__name__)


def _build_date_range_query(tenant: str, date_str: Optional[str]) -> Dict[str, Any]:
    """
    Build MongoDB query fragment for filtering by a single date (start within that day).
    Returns empty dict if date_str is invalid or missing.
    """
    if not date_str:
        return {}
    settings = TenantService.get_tenant_settings(tenant) or {}
    tz = get_tenant_timezone_zoneinfo(settings)
    try:
        day = dt.date.fromisoformat(date_str)
        start_local = dt.datetime.combine(day, dt.time(0, 0, 0)).replace(tzinfo=tz)
        end_local = start_local + dt.timedelta(days=1)
        return {"start": {"$gte": start_local, "$lt": end_local}}
    except (ValueError, TypeError) as e:
        logger.debug("Invalid date_str for listing query %r: %s", date_str, e)
        return {}


def _build_search_query_fragment(
    search_type: str,
    search_value: str,
    tenant: str,
) -> Dict[str, Any]:
    """
    Build MongoDB query fragment for search_type (phone, name, token).
    Returns empty dict if search_type/search_value not applicable.
    """
    val = str(search_value or "").strip()
    if not val:
        return {}

    if search_type == "phone":
        cc = TenantService._get_tenant_country_code(tenant)
        val = normalize_phone(val, country_code=cc)
        if val.startswith("+"):
            digits = val[1:]
            escaped = "^\\s*\\+?" + re.escape(digits) + "\\s*$"
            try:
                num_val = int(digits)
                return {
                    "$or": [
                        {"customer_phone": {"$regex": escaped, "$options": "i"}},
                        {"customer_phone": num_val},
                        {"customer_phone": val},
                        {"customer_phone": search_value},
                    ]
                }
            except ValueError:
                return {"customer_phone": {"$regex": escaped, "$options": "i"}}
        escaped = re.escape(val)
        return {
            "$or": [
                {"customer_phone": {"$regex": escaped, "$options": "i"}},
                {"customer_phone": val},
                {"customer_phone": search_value},
            ]
        }
    if search_type == "name":
        escaped = re.escape(val)
        # Substring match: allow any characters before/after (required for customer name search)
        pattern = re.compile(".*" + escaped + ".*", re.IGNORECASE)
        return {"customer_name": pattern}
    if search_type == "token":
        escaped = re.escape(val)
        return {"id": {"$regex": escaped, "$options": "i"}}
    return {}


def _build_unified_search_query(search_value: str, tenant: str) -> Dict[str, Any]:
    """
    Build $or query that matches name, phone, or token (id) for a single search box.
    """
    val = str(search_value or "").strip()
    if not val:
        return {}
    name_q = _build_search_query_fragment("name", val, tenant)
    phone_q = _build_search_query_fragment("phone", val, tenant)
    token_q = _build_search_query_fragment("token", val, tenant)
    or_parts = [q for q in (name_q, phone_q, token_q) if q]
    if not or_parts:
        return {}
    return {"$or": or_parts}


class AppointmentListingService:
    """Service for listing and serializing appointments with tenant date format and timezone."""

    @staticmethod
    async def list_appointments(
        tenant: str,
        professional: Optional[str] = None,
        date: Optional[str] = None,
        status: Optional[str] = None,
        search_type: Optional[str] = None,
        search_value: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List appointments for a tenant with optional filters.
        Returns list of dicts with tenant-display date format applied to the date field.
        """
        _tenants, pros_col, appts_col = collections()
        appts: List[Appointment] = []
        query: Dict[str, Any] = {"tenant": tenant}

        if professional:
            try:
                pro_doc = ProfessionalService.resolve_professional_raw(tenant, professional)
                query.update(ProfessionalService.appointment_match_query(pro_doc))
            except ValueError:
                query["professional"] = professional
        if status:
            query["status"] = status

        date_query = _build_date_range_query(tenant, date)
        query.update(date_query)

        if search_value and str(search_value or "").strip():
            if search_type:
                search_query = _build_search_query_fragment(search_type, search_value, tenant)
            else:
                search_query = _build_unified_search_query(search_value, tenant)
            if search_query:
                query.update(search_query)

        for doc in appts_col.find(query).sort("created_at", -1):
            appts.append(
                Appointment(
                    id=str(doc.get("id") or doc.get("_id") or uuid4()),
                    customer_name=str(doc.get("customer_name") or ""),
                    customer_phone=str(doc.get("customer_phone") or ""),
                    professional=str(doc.get("professional") or ""),
                    time=str(doc.get("time") or ""),
                    price=float(doc.get("price", 0.0)),
                    status=str(doc.get("status", "booked")),
                    service=doc.get("service"),
                    created_at=doc.get("created_at") or utcnow(),
                    created_by=doc.get("created_by"),
                    updated_at=doc.get("updated_at"),
                    updated_by=doc.get("updated_by"),
                    start=doc.get("start"),
                    end=doc.get("end"),
                    professional_id=(
                        str(doc.get("professional_id")).strip() or None
                    ) if doc.get("professional_id") is not None else None,
                )
            )

        if (not status or status == SLOT_STATUS_BLOCKED) and date:
            AppointmentListingService._append_blocked_slots_for_date(
                tenant, date, professional, pros_col, appts
            )

        settings = TenantService.get_tenant_settings(tenant) or {}
        user_ids = {a.created_by for a in appts if a.created_by}
        user_ids |= {a.updated_by for a in appts if a.updated_by}
        user_names = UserService.resolve_user_names(list(user_ids)) if user_ids else {}

        return AppointmentListingService._serialize_appointments_for_display(
            appts, tenant, settings, user_names
        )

    @staticmethod
    def _append_blocked_slots_for_date(
        tenant: str,
        date: str,
        professional: Optional[str],
        pros_col: Any,
        appts: List[Appointment],
    ) -> None:
        """Append BLOCKED pseudo-appointments for slots blocked on the given date."""
        prof_query: Dict[str, Any] = {"tenant": tenant}
        if professional:
            try:
                row = ProfessionalService.resolve_professional_raw(tenant, professional)
                prof_query["professional_id"] = row["professional_id"]
            except ValueError:
                prof_query["name"] = professional
        for prof_doc in pros_col.find(prof_query):
            overrides = prof_doc.get("date_overrides") or {}
            day_slots = overrides.get(date) or []
            for s in day_slots:
                if s.get("status") == SLOT_STATUS_BLOCKED:
                    pid = prof_doc.get("professional_id")
                    already = any(
                        a.time == s["time"]
                        and (
                            (pid and getattr(a, "professional_id", None) == pid)
                            or (not pid and a.professional == prof_doc["name"])
                        )
                        for a in appts
                    )
                    if not already:
                        appts.append(
                            Appointment(
                                id=f"BLOCKED-{prof_doc.get('professional_id') or prof_doc['name']}-{s['time']}",
                                customer_name="BLOCKED",
                                customer_phone="NA",
                                professional=prof_doc["name"],
                                time=s["time"],
                                price=0.0,
                                status=SLOT_STATUS_BLOCKED,
                                start=None,
                                end=None,
                                professional_id=prof_doc.get("professional_id"),
                            )
                        )

    @staticmethod
    def _serialize_appointments_for_display(
        appts: List[Appointment],
        tenant: str,
        settings: Dict[str, Any],
        user_names: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """Serialize appointment list to dicts with display date format."""
        return [
            {
                "id": a.id,
                "tenant": tenant,
                "customer_name": a.customer_name,
                "customer_phone": a.customer_phone,
                "professional": a.professional,
                "professional_id": getattr(a, "professional_id", None),
                "time": a.time,
                "date": format_date_for_display(a.start.date(), settings) if a.start else None,
                "price": a.price,
                "status": a.status,
                "created_by": user_names.get(a.created_by) or a.created_by or "system",
                "updated_by": user_names.get(a.updated_by) or a.updated_by or "-",
            }
            for a in appts
        ]
