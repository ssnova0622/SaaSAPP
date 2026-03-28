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


def get_current_user(authorization: Optional[str] = Header(default=None),
                     access_token: Optional[str] = Cookie(default=None)) -> dict:
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
    # Normalize known claims
    return {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "role": str(payload.get("role", "admin")).lower(),
        "tenant": payload.get("tenant"),
        "caps": payload.get("caps") or [],
    }


def ensure_tenant_active(tenant: str):
    """Dependency to ensure a tenant exists and is active. Raises 403 if inactive or 404 if missing."""
    tenant_svc = get_tenant_service()
    doc = tenant_svc.get_tenant(tenant)
    if not doc:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if not bool(doc.get("active", True)):
        raise HTTPException(status_code=403, detail="Tenant is inactive")
    return True


def ensure_module_enabled(module_id: str) -> Callable[[str], bool]:
    """Ensure the given module is enabled for the tenant.
    Usage: _ok = Depends(ensure_module_enabled("store"))
    """
    required = str(module_id).strip().lower()

    def _dep(tenant: str) -> bool:
        tenant_svc = get_tenant_service()
        t = tenant_svc.get_tenant_settings(tenant)
        if not t:
            raise HTTPException(status_code=404, detail="Tenant not found")
        mods = [str(m).lower() for m in (t.get("modules") or [])]
        if required not in mods:
            raise HTTPException(status_code=403, detail=f"Module '{module_id}' is not enabled for this tenant")
        return True

    return _dep


def ensure_super_admin(user: dict = Depends(get_current_user)) -> bool:
    """Ensure the current user is a Super Admin."""
    role = str(user.get("role") or "admin").lower()
    if role != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super Admin privileges required")
    return True


def ensure_tenant_admin_or_super(user: dict = Depends(get_current_user)) -> bool:
    """Ensure the current user is Tenant Admin or Super Admin. Used for creating staff and portal access."""
    role = str(user.get("role") or "admin").lower()
    if role not in (ROLE_TENANT_ADMIN, ROLE_SUPER_ADMIN):
        raise HTTPException(status_code=403, detail="Only tenant admin or super admin can perform this action")
    return True


def ensure_capability_enabled(capability_id: str) -> Callable[[str, dict], bool]:
    """Factory that returns a dependency function ensuring the given capability is enabled for the tenant.
    Usage: _ok = Depends(ensure_capability_enabled("store.orders"))
    """
    return ensure_capability_any_enabled([capability_id])


def ensure_capability_any_enabled(capability_ids: List[str]) -> Callable[[str, dict], bool]:
    """Ensure at least one of the given capabilities is enabled for tenant and (if staff) for user.
    Use for backward compat: e.g. [\"salon.professionals\", \"salon.professionals.view\"].
    """
    allowed = [str(c).lower() for c in capability_ids]

    def _dep(tenant: str, user: dict = Depends(get_current_user)) -> bool:
        role = str(user.get("role") or "admin").lower()
        if role in (ROLE_TENANT_ADMIN, ROLE_SUPER_ADMIN):
            return True
        tenant_svc = get_tenant_service()
        t = tenant_svc.get_tenant_settings(tenant)
        if not t:
            raise HTTPException(status_code=404, detail="Tenant not found")
        caps = [str(c).lower() for c in (t.get("capabilities") or [])]
        tenant_has_any = any(c in caps for c in allowed)
        if not tenant_has_any:
            raise HTTPException(status_code=403,
                                detail=f"None of capabilities {capability_ids} enabled for this tenant")
        if role == "staff":
            user_caps = [str(c).lower() for c in (user.get("caps") or [])]
            user_has_any = any(c in user_caps for c in allowed)
            if not user_has_any:
                raise HTTPException(status_code=403, detail="User lacks required capability")
        return True

    return _dep


def ensure_permission(scope: str, action: str = "access") -> Callable[[str, dict], bool]:
    """
    Ensure the user has permission for scope and action (role-based / plugin-style).
    scope: module or module.feature (e.g. 'salon.appointments', 'store.orders').
    action: 'read' | 'create' | 'update' | 'delete' | 'access'.
    Currently maps to tenant + user capabilities: having the scope cap grants all actions.
    Use: Depends(ensure_permission("salon.appointments", "create")).
    """
    scope_lower = str(scope).strip().lower()
    cap_list = [scope_lower]
    if "." in scope_lower:
        base = scope_lower.rsplit(".", 1)[0]
        cap_list.extend([f"{base}.view", f"{base}.edit", f"{base}.create", f"{base}.delete"])
    return ensure_capability_any_enabled(cap_list)


def require_role(*roles: str) -> Callable[[dict], bool]:
    allowed = {str(r).lower() for r in roles}

    def _dep(user: dict = Depends(get_current_user)) -> bool:
        role = str(user.get("role") or "admin").lower()
        if role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return True

    return _dep


def ensure_tenant_scope_dep(tenant: str, user: dict = Depends(get_current_user)) -> bool:
    """Restrict tenant access for tenant_admin and staff to their own tenant."""
    role = str(user.get("role") or "admin").lower()
    if role in (ROLE_TENANT_ADMIN, ROLE_STAFF):
        token_tenant = (user.get("tenant") or "").strip()
        if not token_tenant or token_tenant != tenant:
            raise HTTPException(status_code=403, detail="Tenant scope violation")
    return True


def ensure_tenant_scope() -> Callable[[str, dict], bool]:
    """Restrict tenant access for tenant_admin and staff to their own tenant."""
    return ensure_tenant_scope_dep


# Sensitive professional fields: require .edit_sensitive or legacy .manage or legacy full-access cap
PROFESSIONAL_SENSITIVE_KEYS = {"price", "degree", "phone", "address", "bio", "services"}
CAPS_EDIT_SENSITIVE_PROFESSIONALS = [CAP_SALON_PROFESSIONALS_EDIT_SENSITIVE, CAP_SALON_PROFESSIONALS_MANAGE,
                                     CAP_SALON_PROFESSIONALS]
CAPS_EDIT_PROFESSIONALS = [CAP_SALON_PROFESSIONALS_EDIT, CAP_SALON_PROFESSIONALS]


def check_professional_patch_capability(tenant: str, user: dict, patch: dict) -> None:
    """Raise 403 if staff lacks the required capability for the given PATCH body.
    Sensitive fields require .edit_sensitive or .manage; operational fields require .edit.
    Tenant admin and super_admin have full access.
    """
    role = str(user.get("role") or "admin").lower()
    if role in (ROLE_TENANT_ADMIN, ROLE_SUPER_ADMIN):
        return
    tenant_svc = get_tenant_service()
    t = tenant_svc.get_tenant_settings(tenant)
    if not t:
        raise HTTPException(status_code=404, detail="Tenant not found")
    caps = [str(c).lower() for c in (t.get("capabilities") or [])]
    user_caps = [str(c).lower() for c in (user.get("caps") or [])]
    patch_keys = set(patch.keys()) if patch else set()
    has_sensitive = bool(patch_keys & PROFESSIONAL_SENSITIVE_KEYS)
    if has_sensitive:
        tenant_ok = any(c in caps for c in CAPS_EDIT_SENSITIVE_PROFESSIONALS)
        user_ok = any(c in user_caps for c in CAPS_EDIT_SENSITIVE_PROFESSIONALS)
        if not tenant_ok or not user_ok:
            raise HTTPException(status_code=403,
                                detail="User cannot update professional sensitive details (fees, education, contact)")
    else:
        tenant_ok = any(c in caps for c in CAPS_EDIT_PROFESSIONALS)
        user_ok = any(c in user_caps for c in CAPS_EDIT_PROFESSIONALS)
        if not tenant_ok or not user_ok:
            raise HTTPException(status_code=403, detail="User lacks capability to update professionals")
