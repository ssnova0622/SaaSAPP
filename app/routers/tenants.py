from fastapi import APIRouter, HTTPException, Depends, Response
from typing import List, Optional, Any, Dict

from app.models.schemas import TenantCreate, TenantCreateResponse, Professional as ResponseProfessional
from app.core.container import get_tenant_service, get_user_service, get_professional_service, get_appointment_service
from app.core.cache import cache_get_list_tenants, cache_set_list_tenants, cache_delete_list_tenants
from app.helpers.constants_roles import ROLE_SUPER_ADMIN
from app.helpers.constants import DEFAULT_TIMEZONE
from app.helpers.constants import SLOT_STATUS_AVAILABLE
from app.helpers.professional_slots import normalize_slots, default_business_slots, slots_from_schedule
from .deps import get_current_user, ensure_super_admin, ensure_tenant_scope
from app.modules.registry import list_registry
from ..helpers.constants_capabilities import CAP_AI_PREDICTIONS, CAP_AI_APPOINTMENT_RECS

router = APIRouter()


# ---- Admin (JWT) endpoints for tenant settings ----
@router.get("/tenants", dependencies=[Depends(get_current_user)])
def list_tenants(user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict]:
    """List tenants visible to the current user.
    - super_admin: sees all tenants
    - tenant_admin/staff: sees only their own tenant
    """
    tenant_svc = get_tenant_service()
    role = str(user.get("role") or "admin").lower()
    cached = cache_get_list_tenants()
    if cached is not None:
        if role == ROLE_SUPER_ADMIN:
            return cached
        my_tenant = (user.get("tenant") or "").strip()
        if not my_tenant:
            raise HTTPException(status_code=403, detail="Tenant scope violation")
        return [t for t in cached if t.get("tenant") == my_tenant]
    data = tenant_svc.list_tenants()
    cache_set_list_tenants(data)
    if role == ROLE_SUPER_ADMIN:
        return data
    my_tenant = (user.get("tenant") or "").strip()
    if not my_tenant:
        raise HTTPException(status_code=403, detail="Tenant scope violation")
    return [t for t in data if t.get("tenant") == my_tenant]


@router.get("/tenants/{tenant}", dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope())])
def get_tenant_settings(tenant: str) -> Dict:
    doc = get_tenant_service().get_tenant_settings(tenant)
    if not doc:
        raise HTTPException(status_code=404, detail="Tenant not found")
    # normalize keys for response: ensure 'tenant' field exists
    if "tenant" not in doc:
        doc["tenant"] = tenant
    # Normalize modules/capabilities via registry and derive AI capabilities
    try:
        from app.modules.registry import normalize_selection
    except Exception:
        normalize_selection = None  # type: ignore
    mods = [str(m).lower() for m in (doc.get("modules") or [])]
    caps = [str(c).lower() for c in (doc.get("capabilities") or [])]
    try:
        if normalize_selection:
            # Tenant creation — seed defaults so the tenant starts with sensible caps
            mods, caps = normalize_selection(mods, caps, add_defaults=True)
    except Exception:
        pass
    try:
        # derive ai.* from modules and ai toggle
        caps = _normalize_ai_caps(mods, caps)
    except Exception:
        pass
    doc["modules"] = mods
    doc["capabilities"] = caps
    return doc


@router.put("/tenants/{tenant}", dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope())])
def update_tenant_settings(tenant: str, body: Dict[str, Any], user: Dict[str, Any] = Depends(get_current_user)) -> Dict:
    # Validate TZ if provided
    tz = body.get("tz") if isinstance(body, dict) else None
    if tz:
        try:
            from zoneinfo import ZoneInfo  # py3.9+
            _ = ZoneInfo(tz)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid timezone. Use an IANA tz like '{DEFAULT_TIMEZONE}'.")
    role = str((user or {}).get("role") or "admin").lower()
    is_super_admin = role == ROLE_SUPER_ADMIN
    # Super Admin guard when changing plan, modules, or capabilities
    if isinstance(body, dict) and any(k in body for k in ("plan", "modules", "capabilities")):
        if not is_super_admin:
            raise HTTPException(status_code=403,
                                detail="Super Admin privileges required to change Plan & Access")
    # Only Super Admin can change display_name; strip it for tenant admin/staff
    if isinstance(body, dict) and "display_name" in body and not is_super_admin:
        body = {k: v for k, v in body.items() if k != "display_name"}
    # Payments & Fulfillment settings are only available under the Store module
    # If the request attempts to change payment/delivery configuration, ensure 'store' is (or will be) enabled
    if isinstance(body, dict) and any(k in body for k in ("payment_config", "delivery_config", "store_enabled")):
        try:
            current = get_tenant_service().get_tenant_settings(tenant) or {}
            effective_mods = set([str(m).lower() for m in (current.get("modules") or [])])
            # If modules/capabilities are also included in the payload, compute effective modules after update
            if "modules" in body or "capabilities" in body:
                from app.modules.registry import normalize_selection
                nm, _nc = normalize_selection(body.get("modules") or [],
                                              body.get("capabilities") or (current.get("capabilities") or []))
                effective_mods = set(nm)
            if "store" not in effective_mods:
                raise HTTPException(status_code=403,
                                    detail="Payments and Fulfillment settings require the 'store' module to be enabled for this tenant")
        except HTTPException:
            raise
        except Exception:
            # If we cannot determine, be safe and forbid
            raise HTTPException(status_code=403,
                                detail="Payments and Fulfillment settings require the 'store' module to be enabled for this tenant")

    # Appointments settings validation (safe, optional block)
    # This does not require the Store module; it is independent (often used with Salon).
    if isinstance(body, dict) and "appointments" in body:
        appt = body.get("appointments") or {}
        if not isinstance(appt, dict):
            raise HTTPException(status_code=400, detail="appointments must be an object")

        # Coerce and clamp integers where applicable
        def _int_or(val, default):
            try:
                return int(val)
            except Exception:
                return int(default)

        enabled = bool(appt.get("enabled", False))
        whatsapp_enabled = bool(appt.get("whatsapp_enabled", False))
        whatsapp_max_days = _int_or(appt.get("whatsapp_max_days", 3), 3)
        admin_max_days = _int_or(appt.get("admin_max_days", 30), 30)
        slot_duration_minutes = _int_or(appt.get("slot_duration_minutes", 30), 30)
        buffer_minutes = _int_or(appt.get("buffer_minutes", 0), 0)
        tz_appt = appt.get("timezone")
        # Clamp ranges
        whatsapp_max_days = max(1, min(7, whatsapp_max_days))
        admin_max_days = max(7, min(60, admin_max_days))
        slot_duration_minutes = max(5, min(120, slot_duration_minutes))
        buffer_minutes = max(0, min(240, buffer_minutes))
        # Validate timezone if provided
        if tz_appt:
            try:
                from zoneinfo import ZoneInfo  # py3.9+
                _ = ZoneInfo(str(tz_appt))
            except Exception:
                raise HTTPException(status_code=400,
                                    detail=f"Invalid appointments.timezone. Use an IANA tz like '{DEFAULT_TIMEZONE}'.")
        # Normalize payload back
        body = dict(body)
        body["appointments"] = {
            "enabled": enabled,
            "whatsapp_enabled": whatsapp_enabled,
            "whatsapp_max_days": whatsapp_max_days,
            "admin_max_days": admin_max_days,
            "slot_duration_minutes": slot_duration_minutes,
            "buffer_minutes": buffer_minutes,
            **({"timezone": str(tz_appt)} if tz_appt else {}),
        }
    # Normalize modules/capabilities before persisting and derive AI capabilities
    payload: Dict[str, Any] = body if isinstance(body, dict) else {}
    if isinstance(payload, dict):
        try:
            from app.modules.registry import normalize_selection
            current_settings = get_tenant_service().get_tenant_settings(tenant) or {}
            # Use payload value when key is present (even if it is an empty list).
            # Fall back to current only when the key is absent entirely.
            if "modules" in payload:
                raw_mods = payload.get("modules") or []
            else:
                raw_mods = current_settings.get("modules") or []
            req_mods = [str(m).lower() for m in raw_mods]
            if "capabilities" in payload:
                raw_caps = payload.get("capabilities") or []
            else:
                raw_caps = current_settings.get("capabilities") or []
            req_caps = [str(c).lower() for c in raw_caps]
            # add_defaults=False so Super Admin can explicitly remove a default capability
            mods, caps = normalize_selection(req_mods, req_caps, add_defaults=False)
            caps = _normalize_ai_caps(mods, caps)
            payload = dict(payload)
            payload["modules"] = mods
            payload["capabilities"] = caps
        except Exception:
            # If normalization fails, proceed with provided payload
            pass
    try:
        user_id = user.get("sub") or user.get("email")
        updated = get_tenant_service().update_tenant_settings(tenant, payload, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    try:
        if isinstance(body, dict) and ("modules" in body or "capabilities" in body):
            role = str((user or {}).get("role") or "admin").lower()
            if role == ROLE_SUPER_ADMIN:
                caps = [str(c).lower() for c in (updated.get("capabilities") or [])]
                users_page = get_user_service().list_users(tenant=tenant, role="tenant_admin", search=None, page=1,
                                                           size=1000)
                items = list(users_page.get("items") or users_page.get("data") or []) if isinstance(users_page,
                                                                                                    dict) else (
                    users_page if isinstance(users_page, list) else [])
                for u in items:
                    uid = u.get("id") or u.get("_id") or u.get("sub")
                    if uid:
                        try:
                            get_user_service().update_user(user_id=str(uid), patch={"caps": caps})
                        except Exception:
                            pass
    except Exception:
        pass
    return updated


@router.get("/tenants/{tenant}/message-templates",
            dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope())])
def get_tenant_message_templates(tenant: str) -> Dict[str, Any]:
    """Return merged message templates for the tenant (defaults + overrides from tenant_message_templates collection)."""
    from app.services.core.tenant_message_templates_service import get_templates_for_tenant
    if not get_tenant_service().get_tenant_settings(tenant):
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"templates": get_templates_for_tenant(tenant)}


@router.put("/tenants/{tenant}/message-templates",
            dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope())])
def update_tenant_message_templates(
        tenant: str,
        body: Dict[str, Any],
        user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update message template overrides for the tenant. Body: { \"templates\": { \"key\": \"body\", ... } }."""
    from app.services.core.tenant_message_templates_service import upsert_tenant_templates
    if not get_tenant_service().get_tenant_settings(tenant):
        raise HTTPException(status_code=404, detail="Tenant not found")
    templates = body.get("templates") if isinstance(body.get("templates"), dict) else {}
    user_id = user.get("sub") or user.get("email")
    merged = upsert_tenant_templates(tenant, templates, user_id=user_id)
    from app.core.cache import cache_delete_tenant_settings
    cache_delete_tenant_settings(tenant)
    return {"templates": merged}


@router.get("/tenants/{tenant}/message-templates/whatsapp-bundle",
            dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope())])
def get_whatsapp_message_templates_bundle(tenant: str) -> Dict[str, Any]:
    """
    Default messages from ``default_message``, grouped by category; effective tenant text;
    ``customized`` when a row exists in ``tenant_message_templates``.
    """
    from app.services.core.tenant_message_templates_service import get_templates_for_tenant
    from app.services.db import tenant_message_templates_collection
    from app.services.core.default_message_service import (
        build_category_sections,
        get_default_message_bundle,
        list_all_default_message_keys,
    )

    if not get_tenant_service().get_tenant_settings(tenant):
        raise HTTPException(status_code=404, detail="Tenant not found")
    keys = list_all_default_message_keys()
    platform = get_default_message_bundle()
    platform_t: Dict[str, Any] = platform.get("templates") or {}
    labels: Dict[str, Any] = platform.get("labels") or {}
    merged = get_templates_for_tenant(tenant)
    doc = tenant_message_templates_collection().find_one({"tenant_id": tenant}, projection={"templates": 1})
    raw_o = (doc.get("templates") or {}) if doc else {}
    if not isinstance(raw_o, dict):
        raw_o = {}
    customized = {k: k in raw_o for k in keys}
    return {
        "keys": keys,
        "categories": build_category_sections(keys),
        "labels": {k: str(labels.get(k) or k) for k in keys},
        "defaults": {k: str(platform_t.get(k, "")) for k in keys},
        "templates": {k: str(merged.get(k, "")) for k in keys},
        "customized": customized,
    }


@router.put("/admin/default-messages")
def put_default_messages_admin(
        body: Dict[str, Any],
        _: bool = Depends(ensure_super_admin),
        user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Super Admin: update platform defaults in ``default_message`` (affects all tenants unless overridden).
    Body: { \"templates\": { \"key\": \"body\", ... }, \"labels\": { \"key\": \"Label\", ... } } (labels optional).
    """
    from app.services.core.default_message_service import upsert_default_messages

    templates = body.get("templates") if isinstance(body.get("templates"), dict) else {}
    labels = body.get("labels") if isinstance(body.get("labels"), dict) else None
    uid = user.get("sub") or user.get("email")
    bundle = upsert_default_messages(templates, labels_patch=labels, user_id=uid)
    return {"templates": bundle["templates"], "labels": bundle["labels"]}


@router.get("/modules", dependencies=[Depends(get_current_user)])
def list_modules_registry() -> Dict[str, Any]:
    """Return all available modules and capabilities for Super Admin UI."""
    items = list_registry()
    return {"items": items, "total": len(items)}


@router.get("/plans", dependencies=[Depends(get_current_user)])
def list_plans() -> Dict[str, Any]:
    """Return subscription plans with default modules and capabilities (for Settings and tenant creation)."""
    from app.modules.plans import list_plans as get_plans
    return {"plans": get_plans()}


def _normalize_ai_caps(modules: List[str], capabilities: List[str]) -> List[str]:
    """Return capabilities with AI caps normalized based on modules and AI module switch.

    Rules:
    - If 'ai' module is not enabled → strip all 'ai.*' caps.
    - If 'ai' is enabled → preserve any requested ai.* caps (e.g. ai.whatsapp_intents), and derive:
      - add 'ai.predictions' when 'store' module present
      - add 'ai.appointment_recs' when 'salon' or 'clinic' module present
    - Preserve non-AI caps as-is.
    """
    mods = [str(m).lower() for m in (modules or [])]
    caps = [str(c).lower() for c in (capabilities or [])]
    # Preserve requested ai.* caps before stripping (so e.g. ai.whatsapp_intents can be enabled via PUT)
    requested_ai = [c for c in caps if c.startswith("ai.")]
    caps = [c for c in caps if not c.startswith("ai.")]
    if "ai" not in mods:
        return sorted(list(dict.fromkeys(caps)))
    # Re-add requested AI caps plus derived ones
    ai_caps = list(dict.fromkeys(requested_ai))
    if "store" in mods:
        ai_caps.append(CAP_AI_PREDICTIONS)
    if "salon" in mods or "clinic" in mods:
        ai_caps.append(CAP_AI_APPOINTMENT_RECS)
    caps.extend(ai_caps)
    return sorted(list(dict.fromkeys(caps)))


@router.post("/tenants", response_model=TenantCreateResponse,
             dependencies=[Depends(get_current_user), Depends(ensure_super_admin)])
async def create_tenant(payload: TenantCreate):
    tenant = payload.tenant.strip()
    if not tenant:
        raise HTTPException(status_code=400, detail="tenant is required")

    if get_tenant_service().tenant_exists(tenant):
        raise HTTPException(status_code=409, detail=(
            "tenant already exists. Use a different 'tenant' id or delete/reset the existing tenant."
        ))

    if payload.tz:
        try:
            from zoneinfo import ZoneInfo
            _ = ZoneInfo(payload.tz)
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid timezone. Use an IANA tz like '{DEFAULT_TIMEZONE}'.")

    from app.modules.plans import PLAN_IDS, DEFAULT_PLAN, PLAN_TRIAL, PLAN_PRO
    from datetime import datetime, timezone, timedelta
    plan = (getattr(payload, "plan", None) or DEFAULT_PLAN).strip().lower()
    if plan not in PLAN_IDS:
        plan = DEFAULT_PLAN
    trial_ends_at = None
    if plan == PLAN_TRIAL:
        plan = PLAN_PRO
        trial_ends_at = datetime.now(timezone.utc) + timedelta(days=14)
    seed_data = {
        "category": (payload.category or "salon").lower(),
        "plan": plan,
        "appointments": [],
        "cancellations": 0,
        "revenue": 0.0,
        "active": True,
        "tenant_country": getattr(payload, "tenant_country", None) or "IN",
        "owner_email": (payload.owner_email or None),
        "owner_phone": (payload.owner_phone or None),
        "tz": (payload.tz or None),
        "whatsapp_config": (payload.whatsapp_config or None),
    }
    if trial_ends_at is not None:
        seed_data["trial_ends_at"] = trial_ends_at
    get_tenant_service().seed_if_absent(tenant, seed_data)

    if payload.professionals:
        for p in payload.professionals:
            slots = normalize_slots(p.slots) if p.slots else []
            if not slots:
                try:
                    slots = slots_from_schedule(p.work_start, p.work_end, p.slot_interval_minutes)
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))
            if not slots:
                slots = default_business_slots(9, 19)
            try:
                get_professional_service().add_professional(
                    tenant=tenant,
                    name=p.name,
                    employee_id=p.employee_id,
                    price=p.price or 0.0,
                    slots=slots,
                    active=p.active,
                    availability_criteria=p.availability_criteria or "daily",
                    available_days=p.available_days,
                    services=p.services or [],
                    phone=p.phone,
                    degree=p.degree,
                    address=p.address,
                    bio=p.bio,
                )
            except ValueError as e:
                msg = str(e)
                if msg.startswith("A professional with this ") or msg == "Professional id collision; retry":
                    raise HTTPException(status_code=409, detail=msg)
                raise HTTPException(status_code=400, detail=msg)

    email = str(payload.admin_email or "").strip().lower()
    pwd = str(payload.admin_password or "")
    if not email or not pwd:
        raise HTTPException(status_code=400, detail="admin_email and admin_password are required")
    if len(pwd) < 8:
        raise HTTPException(status_code=400, detail="admin_password must be at least 8 characters")
    existing = get_user_service().get_user_by_email(email)
    if existing:
        raise HTTPException(status_code=409, detail="admin email already exists")
    try:
        get_user_service().create_user(
            email=email,
            password=pwd,
            role="tenant_admin",
            tenant=tenant,
            display_name=payload.admin_display_name or "Tenant Admin",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    cache_delete_list_tenants()
    tenant_doc = get_tenant_service().get_tenant(tenant) or {}
    pros_models = get_professional_service().get_professionals(tenant)
    appts = await get_appointment_service().list_appointments(tenant=tenant)
    professionals_out: List[ResponseProfessional] = []
    for p in pros_models:
        pd = p.model_dump() if hasattr(p, "model_dump") else p.dict()
        professionals_out.append(
            ResponseProfessional.model_validate(
                {
                    "name": p.name,
                    "professional_id": str(pd.get("professional_id") or ""),
                    "employee_id": str(pd.get("employee_id") or ""),
                    "price": float(p.price or 0.0),
                    "slots": [
                        {
                            "time": getattr(s, "time", ""),
                            "status": getattr(s, "status", SLOT_STATUS_AVAILABLE),
                        }
                        for s in (p.slots or [])
                    ],
                    "active": bool(getattr(p, "active", True)),
                    "availability_criteria": str(getattr(p, "availability_criteria", None) or "daily"),
                    "available_days": list(getattr(p, "available_days", None) or []),
                    "services": list(getattr(p, "services", None) or []),
                    "phone": getattr(p, "phone", None),
                    "degree": getattr(p, "degree", None),
                    "address": getattr(p, "address", None),
                    "bio": getattr(p, "bio", None),
                }
            )
        )
    return TenantCreateResponse(
        tenant=tenant,
        category=tenant_doc.get("category", "salon"),
        professionals=professionals_out,
        appointments=len(appts),
        revenue=float(tenant_doc.get("revenue", 0.0)),
    )


@router.delete(
    "/tenants/{tenant}",
    status_code=204,
    response_class=Response,
)
def delete_tenant(tenant: str, user: dict = Depends(get_current_user),
                  _super: bool = Depends(ensure_super_admin)) -> Response:
    """Delete tenant and cascade to professionals, appointments, customers, staff."""
    user_id = user.get("sub") or user.get("email")
    ok = False
    try:
        ok = get_tenant_service().delete_tenant(tenant, user_id=user_id)
    except AttributeError:
        raise HTTPException(status_code=501, detail="Tenant deletion not implemented")
    if not ok:
        raise HTTPException(status_code=404, detail="Tenant not found")
    cache_delete_list_tenants()
    return Response(status_code=204)


@router.patch("/tenants/{tenant}/status", dependencies=[Depends(get_current_user)])
def patch_tenant_status(tenant: str, body: Dict[str, Any], user: Dict[str, Any] = Depends(get_current_user)) -> Dict:
    """Toggle active status for a tenant. Body: {"active": bool}. Returns updated settings."""
    if not isinstance(body, dict) or "active" not in body:
        raise HTTPException(status_code=400, detail="Body must include 'active': true|false")
    user_id = user.get("sub") or user.get("email")
    try:
        updated = get_tenant_service().update_tenant_settings(tenant, {"active": bool(body["active"])}, user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return updated
