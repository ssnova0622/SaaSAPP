from __future__ import annotations
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .deps import get_current_user, ensure_tenant_active, ensure_tenant_scope
from ..services import followups as svc

router = APIRouter()


class FollowupListResponse(BaseModel):
    items: list[Dict[str, Any]]
    total: int
    page: int
    size: int


@router.get("/tenants/{tenant}/followups", response_model=FollowupListResponse,
            dependencies=[Depends(get_current_user)])
def list_followups(
        tenant: str,
        _active_ok: bool = Depends(ensure_tenant_active),
        _scope_ok: bool = Depends(ensure_tenant_scope()),
        status: Optional[str] = Query(default=None, description="scheduled|sent|failed|canceled"),
        customer_name: Optional[str] = Query(default=None),
        customer_phone: Optional[str] = Query(default=None),
        from_ts: Optional[datetime] = Query(default=None),
        to_ts: Optional[datetime] = Query(default=None),
        page: int = Query(default=1, ge=1),
        size: int = Query(default=50, ge=1, le=200),
):
    data = svc.list_followups(
        tenant=tenant,
        status=status,
        customer_name=customer_name,
        customer_phone=customer_phone,
        from_ts=from_ts,
        to_ts=to_ts,
        page=page,
        size=size
    )
    return FollowupListResponse(**data)


@router.post("/tenants/{tenant}/followups/{followup_id}/cancel", dependencies=[Depends(get_current_user)])
def cancel_followup(tenant: str, followup_id: str, _active_ok: bool = Depends(ensure_tenant_active),
                    _scope_ok: bool = Depends(ensure_tenant_scope())):
    ok = svc.cancel_followup(tenant, followup_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Follow-up not found or not cancelable")
    return {"status": "ok"}
