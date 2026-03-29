from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Any

from ..helpers.constants import SLOT_STATUS_AVAILABLE
from ..helpers.professional_slots import normalize_slots, default_business_slots, slots_from_schedule
from ..models.schemas import (Slot as SlotModel, PredictRequest, Professional as ProfessionalModel,
                              ProfessionalBrief, ProfessionalCreate, AvailabilityItem)
from ..core.container import get_tenant_service, get_professional_service, get_slot_service, get_user_service
from .deps import (ensure_tenant_active, ensure_module_enabled, ensure_capability_any_enabled,
                   ensure_tenant_scope)
from .deps import get_current_user, check_professional_patch_capability
from pydantic import BaseModel, Field
from typing import Union
import datetime as dt

from ..services.storage import Slot

router = APIRouter()


def _professional_model_from_any(
        *,
        name: str,
        professional_id: str,
        employee_id: str = "",
        price: float,
        slots_out: List[Any],
        active: bool = True,
        availability_criteria: str = "daily",
        available_days: Optional[List[int]] = None,
        services: Optional[List[str]] = None,
        phone: Optional[str] = None,
        degree: Optional[str] = None,
        address: Optional[str] = None,
        bio: Optional[str] = None,
) -> ProfessionalModel:
    return ProfessionalModel(
        name=name,
        professional_id=professional_id or "",
        employee_id=employee_id or "",
        price=float(price or 0.0),
        slots=[SlotModel(time=s.time, status=s.status) for s in slots_out],
        active=bool(active),
        availability_criteria=availability_criteria or "daily",
        available_days=available_days or [],
        services=services or [],
        phone=phone,
        degree=degree,
        address=address,
        bio=bio,
    )


class UpdateSlotsBody(BaseModel):
    slots: Union[List[str], List[SlotModel]] = Field(default_factory=list,
                                                     description="List of HH:MM strings or Slot objects")
    date: Optional[str] = Field(None, description="YYYY-MM-DD for date-specific override")


@router.get("/tenants/{tenant}/professionals", response_model=List[ProfessionalBrief])
def list_professionals(
        tenant: str,
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _scope_ok: bool = Depends(ensure_tenant_scope()),
        _cap_ok: bool = Depends(ensure_capability_any_enabled(["salon.professionals", "salon.professionals.view"])),
) -> List[ProfessionalBrief]:
    out: List[ProfessionalBrief] = []
    for p in get_professional_service().get_professionals(tenant):
        d = p.model_dump() if hasattr(p, "model_dump") else {}
        pid = str(d.get("professional_id") or getattr(p, "professional_id", None) or "").strip()
        nm = str(d.get("name") or getattr(p, "name", "") or "")
        eid = str(d.get("employee_id") or getattr(p, "employee_id", None) or "").strip()
        out.append(ProfessionalBrief(professional_id=pid, name=nm, employee_id=eid))
    return out


@router.post("/tenants/{tenant}/professionals", response_model=ProfessionalModel, status_code=201)
def create_professional(
        tenant: str,
        body: ProfessionalCreate,
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled(["salon.professionals.create", "salon.professionals"])),
) -> ProfessionalModel:
    user_id = user.get("sub") or user.get("email")
    if not get_tenant_service().tenant_exists(tenant):
        raise HTTPException(status_code=404, detail="Tenant mismatch or tenant not found")
    slots = normalize_slots(body.slots)
    if not slots:
        try:
            slots = slots_from_schedule(body.work_start, body.work_end, body.slot_interval_minutes)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    if not slots:
        slots = default_business_slots(9, 19)
    try:
        created = get_professional_service().add_professional(
            tenant=tenant,
            name=body.name,
            employee_id=body.employee_id,
            price=body.price or 0.0,
            slots=slots,
            active=body.active,
            user_id=user_id,
            availability_criteria=body.availability_criteria or "daily",
            available_days=body.available_days,
            services=body.services or [],
            phone=body.phone,
            degree=body.degree,
            address=body.address,
            bio=body.bio,
        )
    except ValueError as e:
        msg = str(e)
        if msg == "Professional id collision; retry" or msg.startswith("A professional with this "):
            raise HTTPException(status_code=409, detail=msg)
        if msg == "Tenant not found":
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    return _professional_model_from_any(
        name=created.name,
        professional_id=str(getattr(created, "professional_id", None) or ""),
        employee_id=str(getattr(created, "employee_id", None) or ""),
        price=created.price,
        slots_out=created.slots,
        active=created.active,
        availability_criteria=created.availability_criteria,
        available_days=created.available_days,
        services=getattr(created, "services", None) or [],
        phone=getattr(created, "phone", None),
        degree=getattr(created, "degree", None),
        address=getattr(created, "address", None),
        bio=getattr(created, "bio", None),
    )


@router.get("/tenants/{tenant}/professionals/full")
def list_professionals_full(
        tenant: str,
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _scope_ok: bool = Depends(ensure_tenant_scope()),
        _cap_ok: bool = Depends(ensure_capability_any_enabled(["salon.professionals", "salon.professionals.view"])),
        active: Optional[bool] = Query(default=None),
):
    """Return full professional documents including active flag; optional active filter."""
    items = get_professional_service().list_professionals_full(tenant=tenant, active=active)
    user_ids = {p.get("created_by") for p in items if p.get("created_by")} | {p.get("updated_by") for p in items if
                                                                              p.get("updated_by")}
    user_names = get_user_service().resolve_user_names(list(user_ids)) if user_ids else {}
    for p in items:
        p["created_by"] = user_names.get(p.get("created_by")) or p.get("created_by") or "system"
        p["updated_by"] = user_names.get(p.get("updated_by")) or p.get("updated_by") or "-"
    return items


@router.get("/tenants/{tenant}/professionals/{professional}/slots", response_model=List[SlotModel])
def list_slots(
        tenant: str,
        professional: str,
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled(["salon.professionals", "salon.professionals.view"])),
) -> List[SlotModel]:
    p = get_professional_service().get_professional(tenant, professional)
    if not p:
        raise HTTPException(status_code=404, detail="Professional not found")
    slots_data = p.get("slots") or []
    return [SlotModel(time=s.get("time", ""), status=s.get("status", SLOT_STATUS_AVAILABLE)) for s in slots_data]


@router.put("/tenants/{tenant}/professionals/{professional}/slots", response_model=ProfessionalModel)
def update_slots(
        tenant: str,
        professional: str,
        body: UpdateSlotsBody,
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled(["salon.professionals.edit", "salon.professionals"])),
) -> ProfessionalModel:
    user_id = user.get("sub") or user.get("email")
    slots = normalize_slots(body.slots)
    slot_dicts = [{"time": s.time, "status": s.status} for s in slots]
    try:
        updated = get_slot_service().update_professional_slots(tenant, professional, slot_dicts, date_str=body.date,
                                                               user_id=user_id)
    except ValueError as e:
        msg = str(e)
        if msg == "Professional not found":
            raise HTTPException(status_code=404, detail=msg)
        if msg == "Professional is inactive":
            raise HTTPException(status_code=403, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    slots_out = getattr(updated, "slots", None) or []
    return _professional_model_from_any(
        name=getattr(updated, "name", professional),
        professional_id=str(getattr(updated, "professional_id", None) or ""),
        employee_id=str(getattr(updated, "employee_id", None) or ""),
        price=getattr(updated, "price", 0.0),
        slots_out=slots_out,
        active=getattr(updated, "active", True),
        availability_criteria=getattr(updated, "availability_criteria", "daily"),
        available_days=getattr(updated, "available_days", []),
        services=getattr(updated, "services", None) or [],
        phone=getattr(updated, "phone", None),
        degree=getattr(updated, "degree", None),
        address=getattr(updated, "address", None),
        bio=getattr(updated, "bio", None),
    )


class SlotStatusPatch(BaseModel):
    status: str = Field(..., pattern="^(available|blocked)$")


@router.patch("/tenants/{tenant}/professionals/{name}/slots/{time}")
def patch_slot_status(
        tenant: str,
        name: str,
        time: str,
        body: SlotStatusPatch,
        date: Optional[str] = Query(None, description="YYYY-MM-DD"),
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled(["salon.professionals.edit", "salon.professionals"])),
):
    user_id = user.get("sub") or user.get("email")
    try:
        d = dt.date.fromisoformat(date) if date else None
        get_slot_service().set_slot_status(tenant, name, time, body.status, date=d, user_id=user_id)
        return {"status": "ok", "time": time, "new_status": body.status, "date": date}
    except ValueError as e:
        msg = str(e)
        if msg == "Professional not found":
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class StatusPatch(BaseModel):
    active: Optional[bool] = None
    name: Optional[str] = None
    employee_id: Optional[str] = None
    price: Optional[float] = None
    availability_criteria: Optional[str] = None
    available_days: Optional[List[int]] = None
    services: Optional[List[str]] = None
    phone: Optional[str] = None
    degree: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None


@router.patch("/tenants/{tenant}/professionals/{name}", response_model=ProfessionalModel)
def update_professional(
        tenant: str,
        name: str,
        body: StatusPatch,
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _scope_ok: bool = Depends(ensure_tenant_scope()),
        _cap_ok: bool = Depends(ensure_capability_any_enabled(
            ["salon.professionals", "salon.professionals.edit", "salon.professionals.edit_sensitive"])),
):
    patch = body.model_dump(exclude_none=True)
    check_professional_patch_capability(tenant, user, patch)
    user_id = user.get("sub") or user.get("email")
    try:
        updated = get_professional_service().update_professional(tenant=tenant, key=name, patch=patch, user_id=user_id)
        raw_slots = updated.get("slots") or []
        slots_out = [
            SlotModel(time=s.get("time", ""), status=s.get("status", SLOT_STATUS_AVAILABLE))
            for s in raw_slots
            if isinstance(s, dict) and s.get("time")
        ]
        return _professional_model_from_any(
            name=updated.get("name") or name,
            professional_id=str(updated.get("professional_id") or ""),
            employee_id=str(updated.get("employee_id") or ""),
            price=float(updated.get("price") if updated.get("price") is not None else 0),
            slots_out=slots_out,
            active=bool(updated.get("active", True)),
            availability_criteria=updated.get("availability_criteria") or "daily",
            available_days=updated.get("available_days") or [],
            services=updated.get("services") or [],
            phone=updated.get("phone"),
            degree=updated.get("degree"),
            address=updated.get("address"),
            bio=updated.get("bio"),
        )
    except ValueError as e:
        msg = str(e)
        if msg == "Professional not found":
            raise HTTPException(status_code=404, detail=msg)
        if msg.startswith("Multiple professionals named"):
            raise HTTPException(status_code=400, detail=msg)
        if msg.startswith("A professional with this "):
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@router.post("/tenants/{tenant}/slots/predict")
def predict_slots(
        tenant: str,
        body: PredictRequest,
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
):
    # AI functionality removed
    raise HTTPException(status_code=404, detail="AI predictions are no longer available")


# ---- Phase 1: Availability (TZ-aware, horizon-clamped) ----
@router.get("/tenants/{tenant}/professionals/{professional}/availability", response_model=List[AvailabilityItem])
async def get_availability(
        tenant: str,
        professional: str,
        from_date: str = Query(..., alias="from", description="Start date (YYYY-MM-DD)"),
        to_date: str = Query(..., alias="to", description="End date (YYYY-MM-DD), inclusive"),
        channel: str = Query(..., regex="^(whatsapp|admin)$", description="Booking channel: whatsapp|admin"),
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled(["salon.professionals", "salon.professionals.view"])),
):
    """Return availability slots for the professional between from/to (inclusive)."""
    try:
        raw = await get_slot_service().get_availability(
            tenant=tenant,
            professional=professional,
            from_date=from_date,
            to_date=to_date,
            channel=channel,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return [
        AvailabilityItem(
            start=item["start"],
            end=item["end"],
            capacity=item.get("capacity", 1),
            remaining=item.get("remaining", 0),
            bookable=item.get("bookable", False),
            blocked=item.get("blocked", False),
        )
        for item in raw
    ]
