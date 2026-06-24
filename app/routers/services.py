from __future__ import annotations
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from .deps import get_current_user, ensure_tenant_active, ensure_tenant_scope, ensure_module_enabled, \
    ensure_capability_any_enabled
from ..core.container import get_salon_services

router = APIRouter()


class ServiceIn(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = 0.0
    duration: int = 30
    active: bool = True
    start_time: Optional[str] = None   # "HH:MM" — booking window open
    end_time: Optional[str] = None     # "HH:MM" — booking window close


class ServiceOut(ServiceIn):
    tenant: str


@router.post("/tenants/{tenant}/services", response_model=ServiceOut)
def create_service(
        tenant: str,
        body: ServiceIn,
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _scope_ok: bool = Depends(ensure_tenant_scope()),
        _cap_ok: bool = Depends(ensure_capability_any_enabled(["salon.services", "salon.services.edit"])),
):
    user_id = (user.get("sub") or user.get("email") or "system")
    try:
        return get_salon_services().create_service(
            tenant=tenant,
            name=body.name,
            description=body.description,
            price=body.price,
            duration=body.duration,
            active=body.active,
            start_time=body.start_time,
            end_time=body.end_time,
            user_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tenants/{tenant}/services", response_model=List[ServiceOut])
def list_services(
        tenant: str,
        active: Optional[bool] = None,
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _scope_ok: bool = Depends(ensure_tenant_scope()),
        _cap_ok: bool = Depends(
            ensure_capability_any_enabled(["salon.services", "salon.services.view", "salon.services.edit"])),
):
    return get_salon_services().list_services(tenant, active=active)


@router.patch("/tenants/{tenant}/services/{name}", response_model=ServiceOut)
def update_service(
        tenant: str,
        name: str,
        body: Dict[str, Any],
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _scope_ok: bool = Depends(ensure_tenant_scope()),
        _cap_ok: bool = Depends(ensure_capability_any_enabled(["salon.services", "salon.services.edit"])),
):
    user_id = (user.get("sub") or user.get("email") or "system")
    res = get_salon_services().update_service(tenant, name, body, user_id=user_id)
    if not res:
        raise HTTPException(status_code=404, detail="Service not found")
    return res


@router.delete("/tenants/{tenant}/services/{name}")
def delete_service(
        tenant: str,
        name: str,
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("salon")),
        _scope_ok: bool = Depends(ensure_tenant_scope()),
        _cap_ok: bool = Depends(ensure_capability_any_enabled(["salon.services", "salon.services.edit"])),
):
    if not get_salon_services().delete_service(tenant, name):
        raise HTTPException(status_code=404, detail="Service not found")
    return {"ok": True}
