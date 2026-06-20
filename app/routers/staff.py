from __future__ import annotations
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends, Query, Response, UploadFile, File
from pydantic import BaseModel, Field

from .deps import (
    get_current_user, ensure_tenant_active, ensure_tenant_admin_or_super,
    ensure_tenant_scope, require_view, require_edit, require_delete,
)
from ..core.container import get_staff_service

router = APIRouter()


# ---- Schemas ----
class StaffCreate(BaseModel):
    name: str
    role: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    skills: Optional[List[str]] = Field(default_factory=list)
    active: bool = True


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    skills: Optional[List[str]] = None
    active: Optional[bool] = None


class StaffListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    size: int


# ---- Endpoints (JWT protected) ----
@router.get(
    "/tenants/{tenant}/staff",
    response_model=StaffListResponse,
    dependencies=[
        Depends(ensure_tenant_scope()),
        Depends(require_view("core.staff")),
    ],
)
def list_staff(
        tenant: str,
        _active_ok: bool = Depends(ensure_tenant_active),
        search: Optional[str] = Query(default=None),
        role: Optional[str] = Query(default=None),
        active: Optional[bool] = Query(default=None),
        page: int = Query(default=1, ge=1),
        size: int = Query(default=50, ge=1, le=200),
):
    data = get_staff_service().list_staff(tenant=tenant, search=search, role=role, active=active, page=page, size=size)
    return StaffListResponse(**data)


@router.post("/tenants/{tenant}/staff", status_code=201)
def create_staff(
        tenant: str,
        body: StaffCreate,
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _scope: bool = Depends(ensure_tenant_scope()),
        _cap: bool = Depends(require_edit("core.staff")),
) -> Dict[str, Any]:
    user_id = (user.get("sub") or user.get("email") or "system")
    try:
        doc = get_staff_service().create_staff(
            tenant=tenant,
            name=body.name,
            role=body.role or "",
            position=(body.position or "").strip() or None,
            phone=(body.phone or '').strip() or None,
            email=(body.email or '').strip() or None,
            skills=[s.strip() for s in (body.skills or []) if isinstance(s, str) and s.strip()],
            active=bool(body.active),
            user_id=user_id,
        )
        return doc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/tenants/{tenant}/staff/{staff_id}",
    dependencies=[Depends(ensure_tenant_scope()), Depends(require_view("core.staff"))],
)
def get_staff(tenant: str, staff_id: str, _active_ok: bool = Depends(ensure_tenant_active)) -> Dict[str, Any]:
    doc = get_staff_service().get_staff(tenant=tenant, staff_id=staff_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Staff not found")
    return doc


@router.put("/tenants/{tenant}/staff/{staff_id}")
def update_staff(
        tenant: str,
        staff_id: str,
        body: StaffUpdate,
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _scope: bool = Depends(ensure_tenant_scope()),
        _cap: bool = Depends(require_edit("core.staff")),
) -> Dict[str, Any]:
    user_id = (user.get("sub") or user.get("email") or "system")
    try:
        updates: Dict[str, Any] = {}
        for field in ["name", "role", "position", "phone", "email", "skills", "active"]:
            val = getattr(body, field)
            if val is not None:
                updates[field] = val
        doc = get_staff_service().update_staff(tenant=tenant, staff_id=staff_id, updates=updates, user_id=user_id)
        return doc
    except ValueError as e:
        msg = str(e)
        if msg == "Staff not found":
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@router.post("/tenants/{tenant}/staff/import")
async def import_staff_csv(
        tenant: str,
        file: UploadFile = File(..., description="CSV file. Required columns: name, role. Optional: phone, email, skills, active"),
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _admin_ok: bool = Depends(ensure_tenant_admin_or_super),
) -> Dict[str, Any]:
    """
    Bulk-import staff from a CSV file.
    - Staff with an existing email are updated (no duplicate created).
    - Staff without an email always create a new record.
    - Returns {inserted, updated, failed, errors[]}.
    """
    user_id = (user.get("sub") or user.get("email") or "system")
    try:
        content = (await file.read()).decode("utf-8-sig", errors="ignore")
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to read file. Make sure it is a valid UTF-8 CSV.")

    # Validate required headers
    import csv
    from io import StringIO
    reader = csv.DictReader(StringIO(content))
    headers = {(h or "").strip().lower() for h in (reader.fieldnames or []) if h}
    if not {"name", "role"}.issubset(headers):
        raise HTTPException(status_code=400, detail="CSV must contain at least 'name' and 'role' columns.")

    try:
        result = get_staff_service().import_staff_csv(tenant=tenant, csv_content=content, user_id=user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/tenants/{tenant}/staff/{staff_id}",
    status_code=204,
    response_class=Response,
)
def delete_staff(
        tenant: str,
        staff_id: str,
        user: dict = Depends(get_current_user),
        _active_ok: bool = Depends(ensure_tenant_active),
        _scope: bool = Depends(ensure_tenant_scope()),
        _admin_ok: bool = Depends(ensure_tenant_admin_or_super),
        _cap: bool = Depends(require_delete("core.staff")),
) -> Response:
    user_id = (user.get("sub") or user.get("email") or "system")
    ok = get_staff_service().delete_staff(tenant=tenant, staff_id=staff_id, user_id=user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Staff not found")
    # Return an empty 204 No Content response (no body allowed for 204)
    return Response(status_code=204)
