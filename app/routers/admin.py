from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from .deps import get_current_user, ensure_tenant_active, ensure_super_admin
from ..helpers.constants_roles import ROLE_TENANT_ADMIN, ROLE_STAFF
from ..models.schemas import AnalyticsResponse
from ..core.container import get_reports_service
from ..services.storage_mongo import Storage

router = APIRouter()


@router.get("/tenants/{tenant}/analytics", response_model=AnalyticsResponse)
async def get_analytics(tenant: str, user: dict = Depends(get_current_user)) -> AnalyticsResponse:
    ensure_tenant_active(tenant)
    role = str(user.get("role") or "admin").lower()
    if role in (ROLE_TENANT_ADMIN, ROLE_STAFF):
        token_tenant = (user.get("tenant") or "").strip()
        if not token_tenant or token_tenant != tenant:
            raise HTTPException(status_code=403, detail="Tenant scope violation")

    data = await get_reports_service().get_tenant_analytics(tenant)
    return AnalyticsResponse(**data)


@router.get("/tenants/{tenant}/dashboard/summary")
async def get_dashboard_summary_route(tenant: str, user: dict = Depends(get_current_user)):
    ensure_tenant_active(tenant)
    role = str(user.get("role") or "admin").lower()
    if role in (ROLE_TENANT_ADMIN, ROLE_STAFF):
        token_tenant = (user.get("tenant") or "").strip()
        if not token_tenant or token_tenant != tenant:
            raise HTTPException(status_code=403, detail="Tenant scope violation")

    return await get_reports_service().get_dashboard_summary(tenant)


@router.get("/admin/tenants/overview")
def get_tenants_overview(
        _user: dict = Depends(get_current_user),
        _super_admin: bool = Depends(ensure_super_admin),
):
    """Super Admin only: list all tenants with plan, payment, WhatsApp inbound count, trial, status. Optionally revenue_30d."""
    tenants = Storage.list_tenants_basic()
    inbound_counts = Storage.get_whatsapp_inbound_counts()
    outbound_counts = Storage.get_whatsapp_outbound_counts()
    reports = get_reports_service()
    out = []
    for t in tenants:
        tenant_id = t.get("tenant") or t.get("_id")
        row = {
            "tenant": tenant_id,
            "plan": t.get("plan"),
            "trial_ends_at": t.get("trial_ends_at"),
            "active": bool(t.get("active", True)),
            "payment_config": t.get("payment_config") or {},
            "whatsapp_inbound_count": inbound_counts.get(tenant_id, 0),
            "whatsapp_outbound_count": outbound_counts.get(tenant_id, 0),
            "owner_email": t.get("owner_email"),
            "owner_phone": t.get("owner_phone"),
            "category": t.get("category", "salon"),
        }
        try:
            sales = reports.sales_timeseries(tenant=tenant_id, days=30)
            row["revenue_30d"] = sum(
                float(d.get("total_revenue") or d.get("store_revenue") or 0) for d in (sales or []))
        except Exception:
            row["revenue_30d"] = 0.0
        out.append(row)
    return {"tenants": out}
