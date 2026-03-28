# app/services/salon/appointments/appointment_status_service.py
from __future__ import annotations
import logging
from typing import Dict, Any, Optional
from zoneinfo import ZoneInfo

from app.services.core.tenant_service import TenantService
from app.services.core.user_service import UserService
from app.services.db import collections
from app.helpers.constants import APPOINTMENT_STATUS_COMPLETED, APPOINTMENT_STATUS_NO_SHOW, SLOT_STATUS_AVAILABLE
from app.helpers.date_utils import format_date_for_tenant, utcnow

from .slot_service import SlotService

logger = logging.getLogger(__name__)


class AppointmentStatusService:
    @staticmethod
    def update_status(
        tenant: str,
        appointment_id: str,
        status: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        tenants_col, pros_col, appts_col = collections()
        doc = appts_col.find_one({"tenant": tenant, "id": appointment_id})
        if not doc:
            raise ValueError("Appointment not found")

        update_payload = {
            "status": status,
            "updated_at": utcnow(),
            "updated_by": user_id,
        }
        appts_col.update_one({"tenant": tenant, "id": appointment_id}, {"$set": update_payload})

        old_status = doc.get("status")
        price = float(doc.get("price") or 0.0)

        # When marking as no_show, free the slot and increment customer no_show_count for blocking
        if status == APPOINTMENT_STATUS_NO_SHOW:
            if doc.get("start") and doc.get("professional") and doc.get("time"):
                try:
                    tenant_doc = TenantService.get_tenant_settings(tenant) or {}
                    tz_name = tenant_doc.get("tz") or DEFAULT_TIMEZONE
                    tz = ZoneInfo(tz_name)
                except Exception:
                    tz = ZoneInfo(DEFAULT_TIMEZONE)
                SlotService.set_slot_status(
                    tenant,
                    doc.get("professional"),
                    doc.get("time"),
                    SLOT_STATUS_AVAILABLE,
                    date=doc.get("start").astimezone(tz).date(),
                )
            try:
                from .no_show_block_service import increment_no_show_count
                from app.helpers.phone_utils import normalize_phone
                raw_phone = (doc.get("customer_phone") or doc.get("phone") or "").strip()
                if not raw_phone:
                    logger.warning(
                        "no_show: appointment %s tenant=%s has no customer_phone/phone; cannot increment no_show_count",
                        appointment_id, tenant,
                    )
                else:
                    cc = TenantService._get_tenant_country_code(tenant)
                    norm_phone = normalize_phone(str(raw_phone), country_code=cc)
                    if norm_phone:
                        new_count = increment_no_show_count(tenant, norm_phone, doc.get("customer_name"))
                        logger.info(
                            "no_show: incremented no_show_count for tenant=%s phone=%s -> count=%s",
                            tenant, norm_phone, new_count,
                        )
                    else:
                        logger.warning(
                            "no_show: could not normalize phone %r for tenant=%s",
                            raw_phone, tenant,
                        )
            except Exception as e:
                logger.exception(
                    "no_show: failed to increment no_show_count for appointment %s tenant=%s: %s",
                    appointment_id, tenant, e,
                )

        if old_status != APPOINTMENT_STATUS_COMPLETED and status == APPOINTMENT_STATUS_COMPLETED:
            tenants_col.update_one({"_id": tenant}, {"$inc": {"revenue": price}})
        elif old_status == APPOINTMENT_STATUS_COMPLETED and status != APPOINTMENT_STATUS_COMPLETED:
            tenants_col.update_one({"_id": tenant}, {"$inc": {"revenue": -price}})

        updated = appts_col.find_one({"tenant": tenant, "id": appointment_id})
        tenant_doc = TenantService.get_tenant_settings(tenant) or {}

        user_ids = {updated.get("created_by"), user_id} - {None}
        user_names = UserService.resolve_user_names(list(user_ids)) if user_ids else {}
        created_by_name = user_names.get(updated.get("created_by")) or updated.get("created_by") or "system"
        updated_by_name = user_names.get(user_id) or user_id

        date_label = (
            format_date_for_tenant(updated.get("start").date(), tenant_doc)
            if updated.get("start")
            else None
        )

        return {
            "id": str(updated.get("id") or updated.get("_id") or appointment_id),
            "tenant": tenant,
            "customer_name": str(updated.get("customer_name") or ""),
            "customer_phone": str(updated.get("customer_phone") or ""),
            "professional": str(updated.get("professional") or ""),
            "time": str(updated.get("time") or ""),
            "date": date_label,
            "price": float(updated.get("price", 0.0)),
            "status": str(updated.get("status") or status),
            "created_by": created_by_name,
            "updated_by": updated_by_name,
        }
