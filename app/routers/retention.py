from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .deps import get_current_user, ensure_tenant_active, ensure_tenant_scope
from ..services import retention as svc

router = APIRouter()


class RetentionSummaryResponse(BaseModel):
    tenant: str
    date: str
    active: int
    at_risk: int
    churned: int


class RetentionListResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    size: int


@router.get("/tenants/{tenant}/customers/retention/summary", response_model=RetentionSummaryResponse,
            dependencies=[Depends(get_current_user)])
def retention_summary(tenant: str, _active_ok: bool = Depends(ensure_tenant_active),
                      _scope_ok: bool = Depends(ensure_tenant_scope())):
    data = svc.get_summary(tenant, use_cached=True)
    if not data:
        raise HTTPException(status_code=404, detail="Tenant not found or no data")
    return data


@router.get("/tenants/{tenant}/customers/retention/list", response_model=RetentionListResponse,
            dependencies=[Depends(get_current_user)])
def retention_list(
        tenant: str,
        _active_ok: bool = Depends(ensure_tenant_active),
        _scope_ok: bool = Depends(ensure_tenant_scope()),
        segment: str = Query(..., description="active|at_risk|churned"),
        days: Optional[int] = Query(default=None,
                                    description="Override days boundary for filtering (used for at_risk/churned)"),
        page: int = Query(default=1, ge=1),
        size: int = Query(default=50, ge=1, le=200),
):
    if segment not in ("active", "at_risk", "churned"):
        raise HTTPException(status_code=400, detail="segment must be one of active|at_risk|churned")
    data = svc.list_by_segment(tenant, segment=segment, days=days, page=page, size=size)
    return RetentionListResponse(**data)
