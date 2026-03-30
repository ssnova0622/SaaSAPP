from __future__ import annotations
from datetime import date
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, RedirectResponse

from .deps import get_current_user, ensure_tenant_active, ensure_tenant_scope, ensure_capability_any_enabled
from ..core.container import get_reports_service

router = APIRouter()


@router.post(
    "/tenants/{tenant}/reports/daily/run",
    dependencies=[
        Depends(get_current_user),
        Depends(ensure_tenant_scope()),
        Depends(ensure_tenant_active),
        Depends(ensure_capability_any_enabled(["core.reports", "core.reports.view"])),
    ],
    summary="Generate PDF and send Email + WhatsApp",
    description="Retrigger anytime: builds the report for the tenant-local day (or optional date_str) and pushes to owner per invoice_delivery. Independent of scheduler schedule.",
)
def run_daily_report(
        tenant: str,
        date_str: Optional[str] = Query(default=None, description="YYYY-MM-DD; omit = tenant-local today"),
        to_date_str: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
) -> Dict[str, Any]:
    try:
        day = date.fromisoformat(date_str) if date_str else None
        to_day = date.fromisoformat(to_date_str) if to_date_str else None
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date; expected YYYY-MM-DD")
    return get_reports_service().run_daily_report(tenant, day=day, to_day=to_day)


@router.get("/tenants/{tenant}/reports/daily", dependencies=[Depends(get_current_user)])
def list_daily_reports(
        tenant: str,
        page: int = Query(1, ge=1),
        size: int = Query(50, ge=1, le=200),
        from_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
        to_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
) -> Dict[str, Any]:
    f_date = date.fromisoformat(from_date) if from_date else None
    t_date = date.fromisoformat(to_date) if to_date else None
    return get_reports_service().list_reports(tenant, page=page, size=size, from_date=f_date, to_date=t_date)


@router.get("/tenants/{tenant}/reports/{date_str}/download", dependencies=[Depends(get_current_user)])
def download_report(tenant: str, date_str: str):
    """
    Unified download endpoint used by the Admin UI. It reads the report record from the
    collection and either streams the local file or redirects to a presigned S3 URL.
    """
    # Validate date format (support single date or YYYY-MM-DD_to_YYYY-MM-DD)
    try:
        if "_to_" in date_str:
            d1, d2 = date_str.split("_to_")
            date.fromisoformat(d1)
            date.fromisoformat(d2)
        else:
            date.fromisoformat(date_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format")
    doc = get_reports_service().ensure_report_downloadable(tenant, date_str)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Report could not be generated or found for this period.",
        )

    res = get_reports_service().resolve_report_download(doc)
    if isinstance(res, RedirectResponse):
        return res
    if isinstance(res, StreamingResponse):
        return res
    # Fallback when storage reference is missing or unreadable
    raise HTTPException(status_code=404, detail="Report file not available")


# ---------- Analytics endpoints for graphs ----------

@router.get(
    "/tenants/{tenant}/reports/period_summary",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_capability_any_enabled(["core.reports", "core.reports.view"]))],
)
def period_summary(
        tenant: str,
        days: Optional[int] = Query(default=None, ge=7, le=120),
        from_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
        to_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
):
    """One response with KPI totals and plain-language highlights for the selected window (fewer round trips)."""
    try:
        f_date = date.fromisoformat(from_date) if from_date else None
        t_date = date.fromisoformat(to_date) if to_date else None
        return get_reports_service().period_summary(tenant=tenant, days=days, from_date=f_date, to_date=t_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/tenants/{tenant}/reports/sales_timeseries",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_capability_any_enabled(["core.reports", "core.reports.view"]))],
)
def sales_timeseries(
        tenant: str,
        days: Optional[int] = Query(default=None, ge=7, le=120),
        interval: str = Query(default="day", description="Currently only 'day' supported"),
        from_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
        to_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
) -> Dict[str, Any]:
    try:
        f_date = date.fromisoformat(from_date) if from_date else None
        t_date = date.fromisoformat(to_date) if to_date else None
        items = get_reports_service().sales_timeseries(tenant=tenant, days=days, interval=interval, from_date=f_date,
                                                       to_date=t_date)
        return {"items": items, "days": days, "interval": "day"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/tenants/{tenant}/reports/orders_by_status",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_capability_any_enabled(["core.reports", "core.reports.view"]))],
)
def orders_by_status(
        tenant: str,
        days: Optional[int] = Query(default=None, ge=7, le=120),
        from_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
        to_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
) -> Dict[str, Any]:
    try:
        f_date = date.fromisoformat(from_date) if from_date else None
        t_date = date.fromisoformat(to_date) if to_date else None
        items = get_reports_service().orders_by_status(tenant=tenant, days=days, from_date=f_date, to_date=t_date)
        return {"items": items, "days": days}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/tenants/{tenant}/reports/category_mix",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_capability_any_enabled(["core.reports", "core.reports.view"]))],
)
def category_mix(
        tenant: str,
        days: Optional[int] = Query(default=None, ge=7, le=120),
        from_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
        to_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
) -> Dict[str, Any]:
    try:
        f_date = date.fromisoformat(from_date) if from_date else None
        t_date = date.fromisoformat(to_date) if to_date else None
        items = get_reports_service().category_mix(tenant=tenant, days=days, from_date=f_date, to_date=t_date)
        return {"items": items, "days": days}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/tenants/{tenant}/reports/professional_performance",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_capability_any_enabled(["core.reports", "core.reports.view"]))],
)
def professional_performance(
        tenant: str,
        days: Optional[int] = Query(default=None, ge=7, le=120),
        from_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
        to_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
) -> Dict[str, Any]:
    try:
        f_date = date.fromisoformat(from_date) if from_date else None
        t_date = date.fromisoformat(to_date) if to_date else None
        items = get_reports_service().professional_performance(tenant=tenant, days=days, from_date=f_date,
                                                               to_date=t_date)
        return {"items": items, "days": days}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/tenants/{tenant}/reports/customers_timeseries",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_capability_any_enabled(["core.reports", "core.reports.view"]))],
)
def customers_timeseries(
        tenant: str,
        days: Optional[int] = Query(default=None, ge=7, le=120),
        from_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
        to_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
) -> Dict[str, Any]:
    try:
        f_date = date.fromisoformat(from_date) if from_date else None
        t_date = date.fromisoformat(to_date) if to_date else None
        items = get_reports_service().customers_timeseries(tenant=tenant, days=days, from_date=f_date, to_date=t_date)
        return {"items": items, "days": days}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
