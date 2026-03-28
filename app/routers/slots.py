from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Any

from ..helpers.constants import SLOT_STATUS_AVAILABLE
from ..models.schemas import (Slot as SlotModel, PredictRequest, Professional as ProfessionalModel,
                              ProfessionalCreate, AvailabilityItem)
from ..core.container import get_tenant_service, get_professional_service, get_slot_service, get_user_service
from .deps import (ensure_tenant_active, ensure_module_enabled, ensure_capability_any_enabled,
                   ensure_tenant_scope)
from .deps import get_current_user, check_professional_patch_capability
from pydantic import BaseModel, Field
from typing import Union
import datetime as dt

from ..services.storage import Slot

router = APIRouter()


def _default_business_slots(start_hour: int = 9, end_hour: int = 19) -> List[Slot]:
    slots: List[Slot] = []
    for h in range(start_hour, end_hour):
        slots.append(Slot(time=f"{h:02d}:00", status=SLOT_STATUS_AVAILABLE))
        slots.append(Slot(time=f"{h:02d}:30", status=SLOT_STATUS_AVAILABLE))
    return slots


class UpdateSlotsBody(BaseModel):
    slots: Union[List[str], List[SlotModel]] = Field(default_factory=list,
                                                     description="List of HH:MM strings or Slot objects")
    date: Optional[str] = Field(None, description="YYYY-MM-DD for date-specific override")


def _normalize_slots(raw: Optional[Any]) -> List[Slot]:
    if not raw:
        return []
    out: List[Slot] = []
    for item in raw:
        if isinstance(item, str):
            t = item.strip()
            if t:
                out.append(Slot(time=t, status=SLOT_STATUS_AVAILABLE))
            continue
        if isinstance(item, dict):
            t = (item.get("time") or "").strip()
            status = (item.get("status") or SLOT_STATUS_AVAILABLE).strip() or SLOT_STATUS_AVAILABLE
            if t:
                out.append(Slot(time=t, status=status))
            continue
        # pydantic model
        t = getattr(item, "time", None)
        s = getattr(item, "status", SLOT_STATUS_AVAILABLE)
        if isinstance(t, str) and t.strip():
            out.append(Slot(time=t.strip(), status=s))
    return out


@router.get("/tenants/{tenant}/professionals", response_model=List[str])
def list_professionals(
        tenant: str,
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _scope_ok: bool = Depends(ensure_tenant_scope()),
        _cap_ok: bool = Depends(ensure_capability_any_enabled(["salon.professionals", "salon.professionals.view"])),
) -> List[str]:
    return [p.name for p in get_professional_service().get_professionals(tenant)]


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
    slots = _normalize_slots(body.slots)
    if not slots:
        slots = _default_business_slots(9, 19)
    try:
        created = get_professional_service().add_professional(
            tenant=tenant,
            name=body.name,
            price=body.price or 0.0,
            slots=slots,
            active=body.active,
            user_id=user_id,
            availability_criteria=body.availability_criteria or "daily",
            available_days=body.available_days,
        )
    except ValueError as e:
        msg = str(e)
        if msg == "Professional already exists":
            raise HTTPException(status_code=409, detail=msg)
        if msg == "Tenant not found":
            raise HTTPException(status_code=404, detail=msg)
        raise
    return ProfessionalModel(
        name=created.name,
        price=created.price,
        slots=[SlotModel(time=s.time, status=s.status) for s in created.slots],
        active=created.active,
        availability_criteria=created.availability_criteria,
        available_days=created.available_days,
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
    slots = _normalize_slots(body.slots)
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
    return ProfessionalModel(
        name=getattr(updated, "name", professional),
        price=getattr(updated, "price", 0.0),
        slots=[SlotModel(time=s.time, status=s.status) for s in slots_out],
        active=getattr(updated, "active", True),
        availability_criteria=getattr(updated, "availability_criteria", "daily"),
        available_days=getattr(updated, "available_days", []),
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class StatusPatch(BaseModel):
    active: Optional[bool] = None
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
        updated = get_professional_service().update_professional(tenant=tenant, name=name, patch=patch, user_id=user_id)
        raw_slots = updated.get("slots") or []
        slots_out = [
            SlotModel(time=s.get("time", ""), status=s.get("status", SLOT_STATUS_AVAILABLE))
            for s in raw_slots
            if isinstance(s, dict) and s.get("time")
        ]
        return ProfessionalModel(
            name=updated.get("name") or name,
            price=float(updated.get("price") if updated.get("price") is not None else 0),
            slots=slots_out,
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
