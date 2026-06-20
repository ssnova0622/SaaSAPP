from __future__ import annotations
from typing import Optional, Callable, List
from fastapi import Depends, HTTPException, Header, Cookie
import jwt
from settings import env

from app.core.container import get_tenant_service
from app.helpers.constants_roles import ROLE_SUPER_ADMIN, ROLE_TENANT_ADMIN, ROLE_STAFF
from app.helpers.constants_capabilities import (
    CAP_SALON_PROFESSIONALS,
    CAP_SALON_PROFESSIONALS_EDIT,
    CAP_SALON_PROFESSIONALS_EDIT_SENSITIVE,
    CAP_SALON_PROFESSIONALS_MANAGE,
)

# ---------------------------------------------------------------------------
# Token / identity
# ---------------------------------------------------------------------------

def get_current_user(
    authorization: Optional[str] = Header(default=None),
    access_token: Optional[str] = Cookie(default=None),
) -> dict:
    token: Optional[str] = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif access_token:
        token = access_token.strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    secret = env.str("JWT_SECRET", "dev-secret-change-me")
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])  # type: ignore[arg-type]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "role": str(payload.get("role", "admin")).lower(),
        "tenant": payload.get("tenant"),
        "caps": payload.get("caps") or [],
    }


# ---------------------------------------------------------------------------
# Tenant / module guards
# ---------------------------------------------------------------------------

def ensure_tenant_active(tenant: str) -> bool:
    """Raise 404/403 when tenant is missing or inactive."""
    doc = get_tenant_service().get_tenant(tenant)
    if not doc:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if not bool(doc.get("active", True)):
        raise HTTPException(status_code=403, detail="Tenant is inactive")
    return True


def ensure_module_enabled(module_id: str) -> Callable[[str], bool]:
    """Ensure the given module is enabled for the tenant."""
    required = str(module_id).strip().lower()

    def _dep(tenant: str) -> bool:
        t = get_tenant_service().get_tenant_settings(tenant)
        if not t:
            raise HTTPException(status_code=404, detail="Tenant not found")
        mods = [str(m).lower() for m in (t.get("modules") or [])]
        if required not in mods:
            raise HTTPException(status_code=403, detail=f"Module '{module_id}' is not enabled for this tenant")
        return True

    return _dep


# ---------------------------------------------------------------------------
# Role guards
# ---------------------------------------------------------------------------

def ensure_super_admin(user: dict = Depends(get_current_user)) -> bool:
    if str(user.get("role") or "").lower() != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super Admin privileges required")
    return True


def ensure_tenant_admin_or_super(user: dict = Depends(get_current_user)) -> bool:
    if str(user.get("role") or "").lower() not in (ROLE_TENANT_ADMIN, ROLE_SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="Only tenant admin or super admin can perform this action")
    return True


# ---------------------------------------------------------------------------
# Tenant-scope guard  (prevent cross-tenant access)
# ---------------------------------------------------------------------------

def ensure_tenant_scope_dep(tenant: str, user: dict = Depends(get_current_user)) -> bool:
    """Block tenant_admin/staff from accessing another tenant's data."""
    role = str(user.get("role") or "").lower()
    if role in (ROLE_TENANT_ADMIN, ROLE_STAFF):
        token_tenant = (user.get("tenant") or "").strip()
        if not token_tenant or token_tenant != tenant:
            raise HTTPException(status_code=403, detail="Tenant scope violation")
    return True


def ensure_tenant_scope() -> Callable[[str, dict], bool]:
    """Dependency factory for tenant scope enforcement."""
    return ensure_tenant_scope_dep


# ---------------------------------------------------------------------------
# Capability guards  (tenant cap + user cap for staff)
# ---------------------------------------------------------------------------

def _user_has_any(user: dict, caps: List[str]) -> bool:
    user_caps = [str(c).lower() for c in (user.get("caps") or [])]
    return any(c in user_caps for c in caps)


def _tenant_has_any(tenant: str, caps: List[str]) -> bool:
    t = get_tenant_service().get_tenant_settings(tenant)
    if not t:
        return False
    tenant_caps = [str(c).lower() for c in (t.get("capabilities") or [])]
    return any(c in tenant_caps for c in caps)


def ensure_capability_any_enabled(capability_ids: List[str]) -> Callable[[str, dict], bool]:
    """Ensure at least one of the given caps is enabled for tenant AND (if staff) for the user."""
    allowed = [str(c).lower() for c in capability_ids]

    def _dep(tenant: str, user: dict = Depends(get_current_user)) -> bool:
        role = str(user.get("role") or "").lower()
        # Super admin and tenant admin bypass cap checks
        if role in (ROLE_TENANT_ADMIN, ROLE_SUPER_ADMIN):
            return True
        if not _tenant_has_any(tenant, allowed):
            raise HTTPException(status_code=403, detail=f"None of capabilities {capability_ids} enabled for this tenant")
        if role == ROLE_STAFF and not _user_has_any(user, allowed):
            raise HTTPException(status_code=403, detail="User lacks required capability")
        return True

    return _dep


def ensure_capability_enabled(capability_id: str) -> Callable[[str, dict], bool]:
    """Single-cap shorthand for ensure_capability_any_enabled."""
    return ensure_capability_any_enabled([capability_id])


# ---------------------------------------------------------------------------
# Action-level dependency factories  (the clean new API)
#
# These encode the view/edit/delete/sensitive naming convention from the
# capability registry so each router only needs one import.
#
# Usage:
#   @router.get(...)
#   async def list_something(
#       _: bool = Depends(require_view("salon.appointments")),
#       _s: bool = Depends(ensure_tenant_scope()),
#   ): ...
# ---------------------------------------------------------------------------

def _action_dep(caps: List[str]) -> Callable[[str, dict], bool]:
    """Internal: build a dependency that checks any of the given caps."""
    return ensure_capability_any_enabled(caps)


def require_view(module_cap: str) -> Callable[[str, dict], bool]:
    """Require *.view (or legacy alias) for reading data."""
    base = module_cap.rstrip(".")
    return _action_dep([base, f"{base}.view", f"{base}.edit"])


def require_edit(module_cap: str) -> Callable[[str, dict], bool]:
    """Require *.edit for creating / updating records."""
    base = module_cap.rstrip(".")
    return _action_dep([base, f"{base}.edit"])


def require_delete(module_cap: str) -> Callable[[str, dict], bool]:
    """Require *.delete for hard deletes."""
    base = module_cap.rstrip(".")
    return _action_dep([base, f"{base}.delete", f"{base}.edit"])


def require_sensitive(module_cap: str) -> Callable[[str, dict], bool]:
    """Require *.edit_sensitive for financial / PII data."""
    base = module_cap.rstrip(".")
    return _action_dep([base, f"{base}.edit_sensitive"])


# ---------------------------------------------------------------------------
# Field-level professional patch guard
# ---------------------------------------------------------------------------

PROFESSIONAL_SENSITIVE_KEYS = {"price", "degree", "phone", "address", "bio", "services"}
CAPS_EDIT_SENSITIVE_PROFESSIONALS = [
    CAP_SALON_PROFESSIONALS_EDIT_SENSITIVE,
    CAP_SALON_PROFESSIONALS_MANAGE,
    CAP_SALON_PROFESSIONALS,
]
CAPS_EDIT_PROFESSIONALS = [CAP_SALON_PROFESSIONALS_EDIT, CAP_SALON_PROFESSIONALS]


def check_professional_patch_capability(tenant: str, user: dict, patch: dict) -> None:
    """Raise 403 if staff lacks capability to patch the given professional fields."""
    role = str(user.get("role") or "").lower()
    if role in (ROLE_TENANT_ADMIN, ROLE_SUPER_ADMIN):
        return
    t = get_tenant_service().get_tenant_settings(tenant)
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    caps = [str(c).lower() for c in (t.get("capabilities") or [])]
    user_caps = [str(c).lower() for c in (user.get("caps") or [])]
    patch_keys = set(patch.keys()) if patch else set()
    has_sensitive = bool(patch_keys & PROFESSIONAL_SENSITIVE_KEYS)
    if has_sensitive:
        if not any(c in caps for c in CAPS_EDIT_SENSITIVE_PROFESSIONALS):
            raise HTTPException(status_code=403, detail="Tenant lacks capability to update professional sensitive details")
        if not any(c in user_caps for c in CAPS_EDIT_SENSITIVE_PROFESSIONALS):
            raise HTTPException(status_code=403, detail="User cannot update professional sensitive details (fees, education, contact)")
    else:
        if not any(c in caps for c in CAPS_EDIT_PROFESSIONALS):
            raise HTTPException(status_code=403, detail="Tenant lacks capability to update professionals")
        if not any(c in user_caps for c in CAPS_EDIT_PROFESSIONALS):
            raise HTTPException(status_code=403, detail="User lacks capability to update professionals")
