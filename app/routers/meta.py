"""Public reference data for admin UI (countries, permission profiles, etc.)."""
from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.helpers.countries_data import list_countries_response
from app.helpers.permission_profiles import (
    list_profiles,
    ASSIGNABLE_CAPS,
    intersect_with_tenant,
)
from app.modules.registry import list_registry
from .deps import get_current_user
from app.core.container import get_tenant_service

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/meta/countries")
def get_countries() -> dict:
    return {"items": list_countries_response()}


@router.get("/meta/permission-profiles")
def get_permission_profiles(
    tenant: Optional[str] = Query(default=None, description="When provided, caps are filtered to this tenant's enabled capabilities"),
) -> dict:
    """
    Return named permission profiles + the assignable capability list.

    Profiles are used by the Access Manager UI so tenant admins can assign
    'Viewer', 'Editor', or 'Manager' instead of picking individual caps.

    When `tenant` is supplied, each profile's caps list and the
    `assignable_caps` list are filtered to only include capabilities that the
    tenant is actually licensed for — staff can never exceed tenant limits.
    """
    profiles = list_profiles()
    assignable = list(ASSIGNABLE_CAPS)
    registry = {e["id"]: e for e in list_registry() if e.get("type") == "capability"}

    if tenant:
        t = get_tenant_service().get_tenant_settings(tenant)
        tenant_caps = [str(c).lower() for c in ((t or {}).get("capabilities") or [])]
        assignable = intersect_with_tenant(assignable, tenant_caps)
        for p in profiles:
            if p.get("id") != "custom":
                p["caps"] = intersect_with_tenant(p.get("caps") or [], tenant_caps)

    # Enrich assignable caps with registry metadata for UI rendering
    enriched = []
    for cap_id in assignable:
        meta = registry.get(cap_id) or {}
        enriched.append({
            "id": cap_id,
            "label": meta.get("label", cap_id),
            "description": meta.get("description", ""),
            "group": meta.get("group", ""),
            "module": meta.get("module", ""),
        })

    return {
        "profiles": profiles,
        "assignable_caps": enriched,
    }
