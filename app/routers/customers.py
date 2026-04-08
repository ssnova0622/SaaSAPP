from __future__ import annotations
import csv
from io import StringIO
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from pydantic import BaseModel, Field

from .deps import get_current_user, ensure_tenant_active, ensure_tenant_scope, ensure_capability_any_enabled
from app.core.container import get_customer_service, get_user_service
from app.services.core.tenant_service import TenantService
from app.helpers.phone_util import PhoneUtil

router = APIRouter()


# ---- Schemas ----
class CustomerUpsert(BaseModel):
    name: str = Field(default="")
    phone: str
    email: Optional[str] = None
    tags: Optional[List[str]] = None
    active: Optional[bool] = Field(default=None, description="Defaults to true when omitted")


class CustomerListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    size: int


# ---- Endpoints (JWT protected) ----
@router.get("/tenants/{tenant}/customers", response_model=CustomerListResponse,
            dependencies=[Depends(get_current_user)])
def list_customers(
        tenant: str,
        _active_ok: bool = Depends(ensure_tenant_active),
        _scope_ok: bool = Depends(ensure_tenant_scope()),
        _cap_ok: bool = Depends(
            ensure_capability_any_enabled(["core.customers", "core.customers.view", "core.customers.edit"])),
        search: Optional[str] = Query(default=None),
        tag: Optional[str] = Query(default=None),
        active: Optional[bool] = Query(default=None),
        page: int = Query(default=1, ge=1),
        size: int = Query(default=50, ge=1, le=200),
):
    data = get_customer_service().list_customers(
        tenant=tenant, search=search, tag=tag, active=active, page=page, size=size
    )
    return CustomerListResponse(**data)


@router.post("/tenants/{tenant}/customers", dependencies=[Depends(get_current_user)])
def upsert_customer(
        tenant: str,
        body: CustomerUpsert,
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _scope_ok: bool = Depends(ensure_tenant_scope()),
        _cap_ok: bool = Depends(
            ensure_capability_any_enabled(["core.customers", "core.customers.view", "core.customers.edit"])),
) -> Dict[str, Any]:
    user_id = user.get("sub") or user.get("email")
    try:
        doc = get_customer_service().upsert_customer(
            tenant=tenant,
            name=(body.name or "").strip(),
            phone=body.phone,
            email=(body.email or "").strip() if body.email else None,
            tags=[t.strip() for t in (body.tags or []) if t and isinstance(t, str)],
            active=body.active,
            user_id=user_id,
        )
        dial = TenantService._get_tenant_country_code(tenant) or PhoneUtil.DEFAULT_DIAL_DIGITS
        doc = PhoneUtil.enrich_document(dict(doc), tenant_dial_digits=dial, phone_field="phone_number", legacy_plain_field="phone")
        # Resolve created_by/updated_by to display names for UI
        user_ids = {doc.get("created_by"), doc.get("updated_by")} - {None}
        if user_ids:
            names = get_user_service().resolve_user_names(list(user_ids))
            if doc.get("created_by"):
                doc["created_by"] = names.get(doc["created_by"]) or doc["created_by"] or "system"
            doc["updated_by"] = names.get(doc["updated_by"]) or doc.get("updated_by") or "-"
        return doc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class StatusPatch(BaseModel):
    active: bool


@router.patch("/tenants/{tenant}/customers/{phone}/status", dependencies=[Depends(get_current_user)])
def patch_customer_status(
        tenant: str,
        phone: str,
        body: StatusPatch,
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _scope_ok: bool = Depends(ensure_tenant_scope()),
        _cap_ok: bool = Depends(
            ensure_capability_any_enabled(["core.customers", "core.customers.view", "core.customers.edit"])),
) -> Dict[str, Any]:
    user_id = user.get("sub") or user.get("email")
    doc = get_customer_service().set_customer_active(
        tenant=tenant, phone=phone, active=bool(body.active), user_id=user_id
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Customer not found")
    dial = TenantService._get_tenant_country_code(tenant) or PhoneUtil.DEFAULT_DIAL_DIGITS
    doc = PhoneUtil.enrich_document(dict(doc), tenant_dial_digits=dial, phone_field="phone_number", legacy_plain_field="phone")
    user_ids = {doc.get("created_by"), doc.get("updated_by")} - {None}
    if user_ids:
        names = get_user_service().resolve_user_names(list(user_ids))
        if doc.get("created_by"):
            doc["created_by"] = names.get(doc["created_by"]) or doc["created_by"] or "system"
        doc["updated_by"] = names.get(doc["updated_by"]) or doc.get("updated_by") or "-"
    return doc


@router.post("/tenants/{tenant}/customers/import", dependencies=[Depends(get_current_user)])
async def import_customers(
        tenant: str,
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        file: UploadFile = File(..., description="CSV file with headers: name,phone,email,tags"),
) -> Dict[str, Any]:
    user_id = user.get("sub") or user.get("email")
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")
    content = (await file.read()).decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(StringIO(content))
    required_cols = {"phone"}
    headers = {(h or "").strip().lower() for h in (reader.fieldnames or []) if h}
    if not required_cols.issubset(headers):
        raise HTTPException(status_code=400, detail="CSV must include at least the 'phone' column")

    return get_customer_service().import_customers_csv(tenant, content, user_id=user_id)
