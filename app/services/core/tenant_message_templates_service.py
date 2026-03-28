# app/services/core/tenant_message_templates_service.py
"""
Tenant message templates stored in MongoDB (tenant_message_templates collection).
Overrides per tenant; merged with platform defaults from ``default_message`` collection.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.helpers.audit_utils import audit_fields_for_create, audit_fields_for_update
from app.services.db import get_db, tenant_message_templates_collection
from app.services.core.default_message_service import get_default_templates_merged


def get_templates_for_tenant(tenant_id: str) -> Dict[str, str]:
    """
    Return merged message templates: platform (``default_message``), then tenant overrides.
    """
    platform = get_default_templates_merged()
    col = tenant_message_templates_collection()
    doc = col.find_one({"tenant_id": tenant_id}, projection={"_id": 0, "templates": 1})
    overrides = (doc.get("templates") or {}) if doc else {}
    if not isinstance(overrides, dict):
        overrides = {}
    return {**platform, **overrides}


def upsert_tenant_templates(
    tenant_id: str,
    templates: Dict[str, str],
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Upsert message template overrides for the tenant. Only provided keys are stored.
    Returns the full merged template dict after save.
    """
    col = tenant_message_templates_collection()
    existing = col.find_one({"tenant_id": tenant_id})
    if existing:
        # Update: merge existing overrides with new, then set only updated_at/updated_by
        current = existing.get("templates") or {}
        if not isinstance(current, dict):
            current = {}
        merged_overrides = {**current, **templates}
        platform = get_default_templates_merged()
        # Remove keys that match platform default (so we don't store redundant data)
        for k in list(merged_overrides.keys()):
            if merged_overrides.get(k) == platform.get(k):
                merged_overrides.pop(k, None)
        audit = audit_fields_for_update(user_id)
        col.update_one(
            {"tenant_id": tenant_id},
            {"$set": {"templates": merged_overrides, **audit}},
        )
    else:
        # Insert
        platform = get_default_templates_merged()
        overrides = {k: v for k, v in templates.items() if v != platform.get(k)}
        audit = audit_fields_for_create(user_id)
        col.insert_one({
            "tenant_id": tenant_id,
            "templates": overrides,
            "created_at": audit["created_at"],
            "updated_at": audit["updated_at"],
            "created_by": audit["created_by"],
            "updated_by": audit["updated_by"],
        })
    return get_templates_for_tenant(tenant_id)


def seed_tenant_templates(tenant_id: str, templates: Dict[str, str]) -> bool:
    """
    Seed templates for a tenant if no document exists. Used for initial data (e.g. ss_business_salon).
    Returns True if document was created, False if already existed.
    """
    col = tenant_message_templates_collection()
    if col.find_one({"tenant_id": tenant_id}):
        return False
    platform = get_default_templates_merged()
    overrides = {k: v for k, v in templates.items() if v != platform.get(k)}
    audit = audit_fields_for_create("system")
    col.insert_one({
        "tenant_id": tenant_id,
        "templates": overrides,
        "created_at": audit["created_at"],
        "updated_at": audit["updated_at"],
        "created_by": audit["created_by"],
        "updated_by": audit["updated_by"],
    })
    return True


def seed_tenant_with_all_defaults(tenant_id: str) -> bool:
    """
    Create an empty tenant_message_templates document (overrides only).
    Effective text comes from ``default_message`` platform defaults merged in memory.
    """
    col = tenant_message_templates_collection()
    if col.find_one({"tenant_id": tenant_id}):
        return False
    audit = audit_fields_for_create("system")
    col.insert_one({
        "tenant_id": tenant_id,
        "templates": {},
        "created_at": audit["created_at"],
        "updated_at": audit["updated_at"],
        "created_by": audit["created_by"],
        "updated_by": audit["updated_by"],
    })
    return True


def ensure_all_tenants_have_default_templates() -> int:
    """
    For every tenant, ensure a tenant_message_templates document exists (empty overrides unless edited).
    Returns the number of documents created.
    """
    db = get_db()
    tenants_col = db.get_collection("tenants")
    created = 0
    for doc in tenants_col.find({}, {"_id": 1}):
        tenant_id = doc.get("_id")
        if not tenant_id:
            continue
        if seed_tenant_with_all_defaults(str(tenant_id)):
            created += 1
    return created
