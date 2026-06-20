"""
Permission profile presets for staff access management.

A profile is a named shortcut that maps to a set of capability IDs.
The Access Manager UI exposes these profiles for tenant admins, so they can
assign a role like "Viewer" or "Editor" instead of manually picking 20 caps.

All IDs here must exist in app/modules/registry.py.  Profiles are always
intersected with the tenant's own enabled capabilities before being stored —
staff can never exceed what the tenant is licensed for.
"""
from __future__ import annotations
from typing import Dict, List, Any

# All granular capability IDs that appear in the registry and can be assigned to staff.
# Ordered by logical group for display purposes.
ASSIGNABLE_CAPS: List[str] = [
    # Core
    "core.dashboard.view",
    "core.customers.view",
    "core.customers.edit",
    "core.customers.edit_sensitive",
    "core.staff",
    "core.promotions",
    "core.followups",
    "core.reports.view",
    "core.retention",
    "core.settings.view",
    "core.settings.edit",
    "core.settings.edit_sensitive",
    "core.users.view",
    "core.users.edit",
    "core.users.edit_sensitive",
    "core.whatsapp_menu",
    # Salon / Appointments
    "salon.services.view",
    "salon.services.edit",
    "salon.professionals.view",
    "salon.professionals.edit",
    "salon.professionals.edit_sensitive",
    "salon.professionals.create",
    "salon.professionals.delete",
    "salon.appointments.view",
    "salon.appointments.edit",
    "salon.appointments.delete",
    "salon.no_show_blocked.view",
    "salon.no_show_blocked.edit",
    # Store
    "store.orders.view",
    "store.orders.edit",
    "store.orders.edit_sensitive",
    "store.orders.delete",
    "store.catalog",
    "store.inventory",
]

# Caps granted per profile (always intersected with tenant caps before storage)
_VIEWER_CAPS: List[str] = [
    "core.dashboard.view",
    "core.customers.view",
    "core.reports.view",
    "core.settings.view",
    "salon.services.view",
    "salon.professionals.view",
    "salon.appointments.view",
    "salon.no_show_blocked.view",
    "store.orders.view",
]

_EDITOR_CAPS: List[str] = _VIEWER_CAPS + [
    "core.customers.edit",
    "core.promotions",
    "core.followups",
    "core.retention",
    "salon.services.edit",
    "salon.professionals.edit",
    "salon.appointments.edit",
    "salon.appointments.delete",
    "salon.no_show_blocked.edit",
    "store.orders.edit",
    "store.catalog",
]

_MANAGER_CAPS: List[str] = _EDITOR_CAPS + [
    "core.customers.edit_sensitive",
    "core.staff",
    "core.users.view",
    "core.users.edit",
    "core.settings.edit",
    "core.whatsapp_menu",
    "salon.professionals.edit_sensitive",
    "salon.professionals.create",
    "salon.professionals.delete",
    "store.orders.edit_sensitive",
    "store.orders.delete",
    "store.inventory",
]

PROFILES: Dict[str, Dict[str, Any]] = {
    "viewer": {
        "label": "Viewer",
        "description": "Can see all pages but cannot make any changes",
        "caps": _VIEWER_CAPS,
    },
    "editor": {
        "label": "Editor",
        "description": "Can view and create/edit records — no sensitive data or admin functions",
        "caps": _EDITOR_CAPS,
    },
    "manager": {
        "label": "Manager",
        "description": "Full operational access. Can manage staff and settings. No super-admin functions",
        "caps": _MANAGER_CAPS,
    },
    "custom": {
        "label": "Custom",
        "description": "Individually configured permissions",
        "caps": [],  # caps set directly on the user
    },
}


def list_profiles() -> List[Dict[str, Any]]:
    """Return all profiles as a list (id added to each dict)."""
    return [{"id": pid, **pdata} for pid, pdata in PROFILES.items()]


def caps_for_profile(profile_id: str) -> List[str]:
    """Return the cap list for a named profile."""
    return list(PROFILES.get(profile_id, {}).get("caps") or [])


def intersect_with_tenant(caps: List[str], tenant_caps: List[str]) -> List[str]:
    """Remove caps the tenant isn't licensed for, so staff never exceed tenant limits."""
    tenant_set = {str(c).lower() for c in tenant_caps}
    return [c for c in caps if c.lower() in tenant_set]


def detect_profile(user_caps: List[str], tenant_caps: List[str]) -> str:
    """
    Best-effort: infer which named profile a user's cap list matches.
    Returns 'custom' when caps don't cleanly match any preset.
    """
    effective = set(intersect_with_tenant(user_caps, tenant_caps))
    for pid in ("manager", "editor", "viewer"):
        profile_effective = set(intersect_with_tenant(caps_for_profile(pid), tenant_caps))
        if effective == profile_effective:
            return pid
    return "custom"
