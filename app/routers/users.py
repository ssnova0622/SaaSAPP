# app/routers/users.py
"""
User management API: list, create, update, and password reset.
Enforces role-based access (super_admin, tenant_admin, staff).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from pydantic import BaseModel, Field
from .deps import get_current_user
from app.core.container import get_tenant_service, get_user_service
from app.core.cache import cache_get_user, cache_set_user, cache_delete_user
from app.modules.registry import ids_map, is_capability

logger = logging.getLogger(__name__)
router = APIRouter()

# When tenant has a legacy "full access" cap, staff can be assigned granular caps under it (view/edit/etc.)
LEGACY_IMPLIED_GRANULAR: Dict[str, List[str]] = {
    "salon.appointments": ["salon.appointments.view", "salon.appointments.edit", "salon.appointments.delete"],
    "salon.services": ["salon.services.view", "salon.services.edit"],
    "salon.professionals": [
        "salon.professionals.view", "salon.professionals.edit", "salon.professionals.edit_sensitive",
        "salon.professionals.manage", "salon.professionals.create", "salon.professionals.delete",
    ],
    "salon.no_show_blocked": ["salon.no_show_blocked.view", "salon.no_show_blocked.edit"],
    "store.orders": ["store.orders.view", "store.orders.edit", "store.orders.edit_sensitive", "store.orders.delete"],
    "core.dashboard": ["core.dashboard.view"],
    "core.settings": ["core.settings.view", "core.settings.edit", "core.settings.edit_sensitive"],
    "core.users": ["core.users.view", "core.users.edit", "core.users.edit_sensitive"],
    "core.customers": ["core.customers.view", "core.customers.edit", "core.customers.edit_sensitive"],
    "core.reports": ["core.reports.view"],
}


def _sanitize_caps_for_tenant(tenant: str, caps: Optional[List[str]]) -> List[str]:
    """
    Return only capability IDs that are valid, enabled for the tenant (or implied by a legacy cap), and normalized.
    When the tenant has a legacy cap (e.g. salon.appointments), staff can be assigned granular caps (e.g. salon.appointments.view, .edit).
    """
    if not caps:
        return []
    m = ids_map()
    tcfg = get_tenant_service().get_tenant_settings(tenant) or {}
    t_caps = {str(c).lower() for c in (tcfg.get("capabilities") or [])}
    out: List[str] = []

    def _allowed(cid: str) -> bool:
        if cid not in m or not is_capability(cid):
            return False
        if cid in t_caps:
            return True
        for legacy, granular_list in LEGACY_IMPLIED_GRANULAR.items():
            if legacy in t_caps and cid in granular_list:
                return True
        return False

    for c in caps:
        cid = str(c).lower().strip()
        if _allowed(cid):
            out.append(cid)
    return sorted(set(out))


def _ensure_can_manage_target(user: Dict[str, Any], target: Dict[str, Any], action: str) -> None:
    """
    Raise HTTP 403 if the current user is not allowed to perform the given action on the target user.
    Super admins can manage anyone; tenant admins only staff in their tenant; staff cannot manage.
    """
    role = str(user.get("role") or "admin").lower()
    if role == "super_admin":
        return
    if role == "tenant_admin":
        my_tenant = (user.get("tenant") or "").strip()
        tgt_role = str(target.get("role") or "staff").lower()
        tgt_tenant = (target.get("tenant") or "").strip()
        if tgt_role == "super_admin" or not tgt_tenant or my_tenant != tgt_tenant:
            logger.warning("Tenant admin %s denied %s on target in tenant %s", user.get("sub"), action, tgt_tenant)
            raise HTTPException(status_code=403, detail="Insufficient role")
        return
    logger.warning("User %s with role %s denied %s (staff cannot manage users)", user.get("sub"), role, action)
    raise HTTPException(status_code=403, detail="Insufficient role")


@router.get("/users", dependencies=[Depends(get_current_user)])
def list_users(
        user: Dict[str, Any] = Depends(get_current_user),
        tenant: Optional[str] = Query(default=None,
                                      description="Filter by tenant (super_admin only; tenant_admin implicit)"),
        search: Optional[str] = Query(default=None),
        role: Optional[str] = Query(default=None),
        page: int = Query(default=1, ge=1),
        size: int = Query(default=50, ge=1, le=200),
) -> Dict[str, Any]:
    """List users with optional tenant/role/search filters. Access depends on caller role."""
    urole = str(user.get("role") or "admin").lower()
    if urole == "staff":
        raise HTTPException(status_code=403, detail="Insufficient role")
    q_tenant: Optional[str] = None
    if urole == "tenant_admin":
        q_tenant = (user.get("tenant") or "").strip()
    else:
        q_tenant = (tenant or None)
    data = get_user_service().list_users(tenant=q_tenant, role=(role or None), search=(search or None), page=page,
                                         size=size)
    return data


@router.post("/users", dependencies=[Depends(get_current_user)])
def create_user(
        body: Dict[str, Any] = Body(...),
        user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create a new user. Super admin can create any role; tenant admin only staff in own tenant."""
    urole = str(user.get("role") or "admin").lower()
    email = str((body.get("email") or "")).strip().lower()
    password = str((body.get("password") or "")).strip()
    role = str((body.get("role") or "staff")).strip().lower()
    tenant = (body.get("tenant") or None)
    caps = body.get("caps") or []
    display_name = body.get("display_name") or ""
    phone = (body.get("phone") or "").strip() or None
    if not email or not password:
        logger.debug("Create user rejected: missing email or password")
        raise HTTPException(status_code=400, detail="email and password are required")
    try:
        if urole == "super_admin":
            # super admin can create any role; tenant must come from set tenant (frontend sends it)
            if role in ("tenant_admin", "staff"):
                if not tenant or not str(tenant).strip():
                    raise HTTPException(status_code=400,
                                        detail="Select a tenant first (use the tenant selector), then create the user.")
                if role == "staff":
                    caps = _sanitize_caps_for_tenant(tenant, caps)
            return get_user_service().create_user(email=email, password=password, role=role, tenant=tenant,
                                                  display_name=display_name, phone=phone, caps=caps)
        if urole == "tenant_admin":
            # tenant admin can create staff in own tenant only
            if role != "staff":
                raise HTTPException(status_code=403, detail="Tenant admin can only create staff users")
            my_tenant = (user.get("tenant") or "").strip()
            if not tenant:
                tenant = my_tenant
            if tenant != my_tenant:
                raise HTTPException(status_code=403, detail="Tenant scope violation")
            caps = _sanitize_caps_for_tenant(tenant, caps)
            return get_user_service().create_user(email=email, password=password, role="staff", tenant=tenant,
                                                  display_name=display_name, phone=phone, caps=caps)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    raise HTTPException(status_code=403, detail="Insufficient role")


@router.get("/users/{user_id}", dependencies=[Depends(get_current_user)])
def get_user(user_id: str, user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Return a single user by ID. Respects role-based visibility."""
    cached = cache_get_user(user_id)
    if cached is not None:
        _ensure_can_manage_target(user, cached, action="read")
        return cached
    doc = get_user_service().get_user_by_id(user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    _ensure_can_manage_target(user, doc, action="read")
    doc.pop("password_hash", None)
    cache_set_user(user_id, {k: v for k, v in doc.items() if k != "password_hash"})
    return doc


@router.patch("/users/{user_id}", dependencies=[Depends(get_current_user)])
def update_user(user_id: str, body: Dict[str, Any] = Body(...), user: Dict[str, Any] = Depends(get_current_user)) -> \
        Dict[str, Any]:
    """Partially update a user (role, tenant, display_name, status, caps, password). Enforces role rules."""
    existing = get_user_service().get_user_by_id(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    _ensure_can_manage_target(user, existing, action="update")
    patch: Dict[str, Any] = {}
    # role and tenant changes
    if "role" in body:
        new_role = str((body.get("role") or existing.get("role") or "staff")).lower()
        # tenant_admin cannot promote/demote to super_admin
        if str(user.get("role")).lower() == "tenant_admin" and new_role != "staff":
            raise HTTPException(status_code=403, detail="Tenant admin can only manage staff")
        patch["role"] = new_role
    if "tenant" in body:
        new_tenant = (body.get("tenant") or existing.get("tenant"))
        if str(user.get("role")).lower() == "tenant_admin":
            # must remain in own tenant
            my_tenant = (user.get("tenant") or "").strip()
            if new_tenant != my_tenant:
                raise HTTPException(status_code=403, detail="Tenant scope violation")
        patch["tenant"] = new_tenant
    if "display_name" in body:
        patch["display_name"] = body.get("display_name")
    if "phone" in body:
        patch["phone"] = (body.get("phone") or "").strip() or None
    if "status" in body:
        patch["status"] = body.get("status")
    # caps
    if "caps" in body:
        tgt_tenant = (patch.get("tenant") or existing.get("tenant"))
        if not tgt_tenant:
            patch["caps"] = []
        else:
            patch["caps"] = _sanitize_caps_for_tenant(str(tgt_tenant), body.get("caps") or [])
    # password change (admin-initiated)
    if "password" in body and body.get("password"):
        patch["password"] = body.get("password")
    try:
        updated = get_user_service().update_user(user_id=user_id, patch=patch)
    except ValueError as e:
        logger.warning("Update user %s failed: %s", user_id, e)
        raise HTTPException(status_code=400, detail=str(e))
    cache_delete_user(user_id)
    updated.pop("password_hash", None)
    return updated


class PasswordBody(BaseModel):
    password: str = Field(..., min_length=8, description="New password (min 8 chars)")


@router.patch("/users/{user_id}/password", dependencies=[Depends(get_current_user)])
def set_password(user_id: str, body: PasswordBody = Body(...), user: Dict[str, Any] = Depends(get_current_user)) -> \
        Dict[str, Any]:
    """Set or change password for a user. Caller may change own password or have admin rights on target."""
    pwd = str((body.password or "")).strip()
    if len(pwd) < 8:
        raise HTTPException(status_code=400, detail="password must be at least 8 characters")
    # Allow self password change or admin per rules
    if user.get("sub") != user_id:
        target = get_user_service().get_user_by_id(user_id)
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        _ensure_can_manage_target(user, target, action="password")
    try:
        updated = get_user_service().update_user(user_id=user_id, patch={"password": pwd})
    except ValueError as e:
        logger.warning("Set password for user %s failed: %s", user_id, e)
        raise HTTPException(status_code=400, detail=str(e))
    cache_delete_user(user_id)
    updated.pop("password_hash", None)
    return updated
