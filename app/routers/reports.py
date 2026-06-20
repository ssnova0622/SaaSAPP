from __future__ import annotations
from datetime import date
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, RedirectResponse, Response

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


@router.get(
    "/tenants/{tenant}/reports/daily",
    dependencies=[
        Depends(ensure_tenant_scope()),
        Depends(ensure_capability_any_enabled(["core.reports", "core.reports.view"])),
    ],
)
def list_daily_reports(
        tenant: str,
        page: int = Query(1, ge=1),
        size: int = Query(50, ge=1, le=200),
        from_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
        to_date: Optional[str] = Query(default=None, description="YYYY-MM-DD"),
) -> Dict[str, Any]:
    try:
        f_date = date.fromisoformat(from_date) if from_date else None
        t_date = date.fromisoformat(to_date) if to_date else None
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid date format; expected YYYY-MM-DD")
    return get_reports_service().list_reports(tenant, page=page, size=size, from_date=f_date, to_date=t_date)


@router.get(
    "/tenants/{tenant}/reports/{date_str}/download",
    dependencies=[
        Depends(ensure_tenant_scope()),
        Depends(ensure_capability_any_enabled(["core.reports", "core.reports.view"])),
    ],
)
def download_report(tenant: str, date_str: str):
    """
    Download the daily/range PDF.
    The PDF is built fresh from live data on every request so the downloaded file always
    uses the current report format and theme — no stale cached files are ever served.
    The freshly-built PDF is also saved/overwritten in storage so the archive stays current.
    """
    from app.services.storage_mongo import Storage
    from app.services.reports.reports import build_daily_report
    from app.services.reports.reports_store import generate_and_store_report
    import logging
    _log = logging.getLogger(__name__)

    # Parse and validate the date key
    try:
        if "_to_" in date_str:
            d1_str, d2_str = date_str.split("_to_", 1)
            day    = date.fromisoformat(d1_str.strip())
            to_day = date.fromisoformat(d2_str.strip())
        else:
            day    = date.fromisoformat(date_str.strip())
            to_day = None
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format; expected YYYY-MM-DD or YYYY-MM-DD_to_YYYY-MM-DD",
        )

    # Build snapshot (live DB query) and PDF bytes in memory — same path as the daily send
    try:
        snapshot  = Storage.get_report_snapshot(tenant, day, to_day)
        fname, pdf_bytes = build_daily_report(tenant, day, snapshot, to_day)
    except Exception as exc:
        _log.exception("PDF generation failed for tenant=%s date=%s: %s", tenant, date_str, exc)
        raise HTTPException(status_code=500, detail="Failed to generate report PDF.")

    # Persist the freshly-built PDF to storage asynchronously (best-effort; non-fatal)
    try:
        generate_and_store_report(tenant, day, to_day, _snapshot=snapshot)
    except Exception as exc:
        _log.warning("Report storage update failed for tenant=%s date=%s: %s", tenant, date_str, exc)

    # Stream the in-memory PDF directly to the browser — zero dependency on stored files
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


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
