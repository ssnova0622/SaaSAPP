from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from ..models.schemas import AppointmentIn, AppointmentOut
from ..core.container import get_tenant_service, get_appointment_service
from ..helpers.constants import (APPOINTMENT_STATUS_BOOKED, APPOINTMENT_STATUS_CANCELED, APPOINTMENT_STATUS_COMPLETED,
                                 APPOINTMENT_STATUS_NEEDS_RESCHEDULE, APPOINTMENT_STATUS_NO_SHOW)
from ..helpers.constants_capabilities import (CAP_SALON_APPOINTMENTS, CAP_SALON_APPOINTMENTS_VIEW,
                                              CAP_SALON_APPOINTMENTS_EDIT, CAP_AI_NO_SHOW, CAP_SALON_NO_SHOW_BLOCKED,
                                              CAP_SALON_NO_SHOW_BLOCKED_VIEW,
                                              CAP_SALON_NO_SHOW_BLOCKED_EDIT)
from .deps import (ensure_tenant_active, ensure_tenant_scope, ensure_module_enabled, ensure_capability_enabled,
                   ensure_capability_any_enabled, get_current_user)
from .ws import notifier
from ..services import followups as followups_service
from app.services.messaging.messaging import Messaging

router = APIRouter()


class AppointmentListItem(AppointmentOut):
    pass


class ReschedulePayload(BaseModel):
    new_time: str
    new_date: Optional[str] = Field(None, description="YYYY-MM-DD")


class StatusUpdatePayload(BaseModel):
    status: str = Field(...,
                        pattern=f"^({APPOINTMENT_STATUS_BOOKED}|{APPOINTMENT_STATUS_COMPLETED}|{APPOINTMENT_STATUS_NO_SHOW})$")


@router.get("/tenants/{tenant}/appointments", response_model=List[AppointmentListItem])
async def list_appointments(
        tenant: str,
        professional: Optional[str] = Query(None),
        date: Optional[str] = Query(None, description="YYYY-MM-DD"),
        status: Optional[str] = Query(None,
                                      pattern=f"^({APPOINTMENT_STATUS_BOOKED}|{APPOINTMENT_STATUS_CANCELED}|{APPOINTMENT_STATUS_NEEDS_RESCHEDULE}|blocked|{APPOINTMENT_STATUS_COMPLETED}|{APPOINTMENT_STATUS_NO_SHOW})$"),
        search: Optional[str] = Query(None, description="Unified search: name, phone, or token"),
        search_type: Optional[str] = Query(None, pattern="^(phone|name|token)$"),
        search_value: Optional[str] = Query(None),
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled([CAP_SALON_APPOINTMENTS, CAP_SALON_APPOINTMENTS_VIEW])),
):
    # Single search box: when "search" is set, use it as search_value with no type (unified)
    effective_value = (search or search_value or "").strip() or None
    effective_type = None if search else search_type
    items = await get_appointment_service().list_appointments(
        tenant=tenant,
        professional=professional,
        date=date,
        status=status,
        search_type=effective_type,
        search_value=effective_value,
    )
    return [AppointmentListItem(**a) for a in items]


@router.post("/tenants/{tenant}/appointments", response_model=AppointmentOut, status_code=201)
async def create_appointment(
        tenant: str,
        payload: AppointmentIn,
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled([CAP_SALON_APPOINTMENTS_EDIT, CAP_SALON_APPOINTMENTS])),
):
    if tenant != payload.tenant:
        raise HTTPException(status_code=400, detail="Tenant mismatch")

    user_id = user.get("sub") or user.get("email")

    try:
        appt = await get_appointment_service().create_appointment(
            tenant=tenant,
            payload=payload.model_dump() if hasattr(payload, "model_dump") else payload,
            user_id=user_id,
        )
    except ValueError as e:
        msg = str(e)
        if msg == "Professional not found":
            raise HTTPException(status_code=404, detail=msg)
        if msg == "Professional is inactive":
            raise HTTPException(status_code=403, detail=msg)
        if msg == "Slot not available":
            raise HTTPException(status_code=400, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    # enqueue follow-ups
    try:
        followups_service.schedule_for_appointment(
            tenant=tenant,
            appointment_id=appt["id"],
            customer_name=appt.customer_name,
            customer_phone=appt.customer_phone,
            customer_email=None,
            professional=appt.professional,
            time_label=appt.time,
        )
    except Exception:
        pass

    # notify via WebSocket
    await notifier.broadcast({"type": "appointment.created", "tenant": tenant, "appointment": appt})
    return AppointmentOut(**appt)


@router.delete("/tenants/{tenant}/appointments/{appointment_id}", response_model=AppointmentOut)
async def cancel_appointment(
        tenant: str,
        appointment_id: str,
        reason: str = Query(APPOINTMENT_STATUS_CANCELED,
                            pattern=f"^({APPOINTMENT_STATUS_CANCELED}|{APPOINTMENT_STATUS_NEEDS_RESCHEDULE})$"),
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled([CAP_SALON_APPOINTMENTS_EDIT, CAP_SALON_APPOINTMENTS])),
):
    user_id = user.get("sub") or user.get("email")
    try:
        appt = await get_appointment_service().cancel_appointment(
            tenant=tenant, appointment_id=appointment_id, reason=reason, user_id=user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        followups_service.cancel_for_appointment(tenant, appointment_id)
    except Exception:
        pass

    if appt.get("customer_phone"):
        try:
            from ..services.salon.appointments.messaging_service import AppointmentMessagingService
            msg = await AppointmentMessagingService.build_cancel_notification_message(tenant, appt)
            Messaging.send_whatsapp_text(appt.get("customer_phone"), msg, tenant=tenant)
        except Exception:
            pass

    await notifier.broadcast({"type": "appointment.canceled", "tenant": tenant, "appointment": appt})
    return AppointmentOut(**appt)


@router.patch("/tenants/{tenant}/appointments/{appointment_id}/reschedule", response_model=AppointmentOut)
async def reschedule_appointment(
        tenant: str,
        appointment_id: str,
        payload: ReschedulePayload,
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled([CAP_SALON_APPOINTMENTS_EDIT, CAP_SALON_APPOINTMENTS])),
):
    user_id = user.get("sub") or user.get("email")
    try:
        appt = await get_appointment_service().reschedule_appointment(
            tenant=tenant,
            appointment_id=appointment_id,
            new_time=payload.new_time,
            new_date=payload.new_date,
            user_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if appt.get("customer_phone"):
        try:
            from ..services.salon.appointments.messaging_service import AppointmentMessagingService
            AppointmentMessagingService.send_rescheduled(
                tenant, appt.get("customer_phone"), appt.get("professional") or "", appt.get("time") or "",
                                                    appt.get("date") or ""
            )
        except Exception:
            pass

    await notifier.broadcast({"type": "appointment.rescheduled", "tenant": tenant, "appointment": appt})
    return AppointmentOut(**appt)


@router.patch("/tenants/{tenant}/appointments/{appointment_id}/status", response_model=AppointmentOut)
def update_appointment_status(
        tenant: str,
        appointment_id: str,
        payload: StatusUpdatePayload,
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled([CAP_SALON_APPOINTMENTS_EDIT, CAP_SALON_APPOINTMENTS])),
):
    user_id = user.get("sub") or user.get("email")
    try:
        appt = get_appointment_service().update_appointment_status(
            tenant=tenant, appointment_id=appointment_id, status=payload.status, user_id=user_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return AppointmentOut(**appt)


# ---- No-show blocking: list blocked phones, reset (requires AI module + ai.no_show; Basic without AI gets 403) ----
@router.get("/tenants/{tenant}/no_show/blocked",
            dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                          Depends(ensure_module_enabled("salon")), Depends(ensure_module_enabled("ai")),
                          Depends(ensure_capability_enabled(CAP_AI_NO_SHOW)), Depends(
                    ensure_capability_any_enabled([CAP_SALON_NO_SHOW_BLOCKED, CAP_SALON_NO_SHOW_BLOCKED_VIEW]))])
def list_no_show_blocked(
        tenant: str,
        search: Optional[str] = Query(None, description="Filter by phone or name"),
):
    """List customers (phone, name, no_show_count) with any no-show. Optional search filters by phone or name."""
    from ..services.salon.appointments.no_show_block_service import list_blocked
    from ..services.ai.config_schema import get_effective_ai_config
    items = list_blocked(tenant, search=search)
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    effective = get_effective_ai_config(settings)
    # Use None-safe default: if the tenant hasn't set a threshold, use 3 as the displayed default.
    raw_threshold = effective.get("no_show_block_threshold")
    threshold = int(raw_threshold) if raw_threshold is not None else 3
    return {"items": items, "threshold": threshold}


class NoShowResetPayload:
    def __init__(self, phone: str):
        self.phone = phone


@router.post("/tenants/{tenant}/no_show/reset",
             dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                           Depends(ensure_module_enabled("salon")), Depends(ensure_module_enabled("ai")),
                           Depends(ensure_capability_enabled(CAP_AI_NO_SHOW)), Depends(
                     ensure_capability_any_enabled([CAP_SALON_NO_SHOW_BLOCKED_EDIT, CAP_SALON_NO_SHOW_BLOCKED]))])
def reset_no_show(
        tenant: str,
        body: dict,
):
    """Reset no_show_count to 0 for a customer so they can book again. Body: { \"phone\": \"+91...\" }."""
    from ..services.salon.appointments.no_show_block_service import reset_no_show as do_reset
    phone = (body or {}).get("phone") or ""
    if not phone or not str(phone).strip():
        raise HTTPException(status_code=400, detail="phone is required")
    result = do_reset(tenant, str(phone).strip())
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("detail", "Customer not found"))
    return result
