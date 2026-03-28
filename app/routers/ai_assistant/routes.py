"""
AI Assistant – NEW MODULE. Super Admin only.

Configurable screen for all AI-related settings:
- Intent keywords (global + tenant): add/edit/delete phrases per intent
- Training data: labeled examples for train/learn
- Seed global keywords from defaults
- Fallback message and intent order (for UI)

All write operations require super_admin. Clean API for a dedicated "AI Assistant" admin screen.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.routers.deps import get_current_user, ensure_super_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-assistant", tags=["AI Assistant"])


def _require_super_admin(user: dict = Depends(get_current_user), _: bool = Depends(ensure_super_admin)) -> dict:
    return user


# ---------- Knowledge base (intent keywords) ----------

@router.get(
    "/knowledge",
    dependencies=[Depends(ensure_super_admin)],
    summary="List intent keywords (global + tenant)",
)
def list_knowledge(
        tenant: Optional[str] = Query(default=None,
                                      description="Filter by tenant for scope=tenant; omit to list global + all tenant entries"),
        scope: Optional[str] = Query(default=None, description="global | tenant"),
) -> Dict[str, Any]:
    """List ai_knowledge_base. Super Admin only. Use for AI Assistant screen."""
    from app.services.ai.knowledge_storage import list_knowledge_base
    if tenant:
        items = list_knowledge_base(scope=scope, tenant=tenant)
    else:
        items = list_knowledge_base(scope=scope or "global", tenant=None)
    return {"scope": scope, "tenant": tenant, "items": items, "total": len(items)}


@router.post(
    "/knowledge",
    dependencies=[Depends(ensure_super_admin)],
    summary="Add or update intent keywords",
)
def upsert_knowledge(body: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert one intent. Body: { scope, intent, phrases, response?, order? }. Super Admin only."""
    from app.services.ai.knowledge_storage import upsert_knowledge_base
    scope = (body.get("scope") or "global").strip().lower()
    if scope not in ("global", "tenant"):
        raise HTTPException(status_code=400, detail="scope must be global or tenant")
    intent = (body.get("intent") or "").strip()
    if not intent:
        raise HTTPException(status_code=400, detail="intent is required")
    phrases = body.get("phrases")
    if not isinstance(phrases, list):
        raise HTTPException(status_code=400, detail="phrases must be a list of strings")
    tenant = body.get("tenant") if scope == "tenant" else None
    if scope == "tenant" and not tenant:
        raise HTTPException(status_code=400, detail="tenant is required for scope=tenant")
    doc = upsert_knowledge_base(scope=scope, intent=intent, phrases=phrases, tenant=tenant,
                                response=body.get("response"), order=body.get("order"))
    return {"item": doc}


@router.delete(
    "/knowledge",
    dependencies=[Depends(ensure_super_admin)],
    summary="Delete intent keywords",
)
def delete_knowledge(
        scope: str = Query(...),
        intent: str = Query(...),
        tenant: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """Delete one intent. Super Admin only."""
    from app.services.ai.knowledge_storage import delete_knowledge_base
    if scope not in ("global", "tenant"):
        raise HTTPException(status_code=400, detail="scope must be global or tenant")
    if scope == "tenant" and not tenant:
        raise HTTPException(status_code=400, detail="tenant is required for scope=tenant")
    deleted = delete_knowledge_base(scope=scope, intent=intent.strip(), tenant=tenant)
    return {"deleted": deleted}


@router.post(
    "/knowledge/seed",
    dependencies=[Depends(ensure_super_admin)],
    summary="Seed global keywords from defaults",
)
def seed_knowledge() -> Dict[str, Any]:
    """Seed ai_knowledge_base with global (general) intent phrases. Idempotent. Super Admin only."""
    from app.services.ai.knowledge_storage import seed_global_intent_keywords
    count = seed_global_intent_keywords()
    return {"seeded": count,
            "message": "Global intent keywords seeded. Add tenant-specific via POST /knowledge with scope=tenant."}


# ---------- Config (for UI: fallback message, intent order) ----------

@router.get(
    "/config",
    dependencies=[Depends(ensure_super_admin)],
    summary="Get AI Assistant config for screen",
)
def get_config() -> Dict[str, Any]:
    """Return config for AI Assistant screen: fallback message, intent order, available intents. Super Admin only."""
    from app.services.ai.config_schema import DEFAULT_AI_CONFIG
    from app.services.ai.knowledge_storage import DEFAULT_INTENT_ORDER
    order = list(DEFAULT_AI_CONFIG.get("intent_keywords_order") or DEFAULT_INTENT_ORDER)
    intents = list(DEFAULT_AI_CONFIG.get("intent_keywords") or {}.keys())
    fallback = (DEFAULT_AI_CONFIG.get("whatsapp_intent_fallback_message") or "").strip()
    return {
        "intent_order": order,
        "intents": intents,
        "fallback_message": fallback,
    }


@router.put(
    "/config",
    dependencies=[Depends(ensure_super_admin)],
    summary="Update fallback message (stored in tenant ai_config or global)",
)
def put_config(body: Dict[str, Any]) -> Dict[str, Any]:
    """Update fallback message. Body: { fallback_message: string }. Applied via tenant ai_config; for global default, update config_schema or use tenant '*' in future."""
    fallback = (body.get("fallback_message") or "").strip()
    return {"fallback_message": fallback,
            "message": "Update tenant ai_config.whatsapp_intent_fallback_message via PUT /tenants/{tenant} for per-tenant message."}


# ---------- Training data ----------

@router.get(
    "/training-data",
    dependencies=[Depends(ensure_super_admin)],
    summary="List training data",
)
def list_training_data(
        tenant: Optional[str] = Query(default=None),
        intent: Optional[str] = Query(default=None),
        limit: int = Query(default=500, ge=1, le=2000),
) -> Dict[str, Any]:
    """List ai_training_data. Super Admin only."""
    from app.services.ai.knowledge_storage import list_training_data as _list
    items = _list(tenant=tenant, intent=intent, limit=limit)
    return {"tenant": tenant, "intent": intent, "items": items, "total": len(items)}


@router.post(
    "/training-data",
    dependencies=[Depends(ensure_super_admin)],
    summary="Add training example",
)
def add_training_data(body: Dict[str, Any]) -> Dict[str, Any]:
    """Add labeled example. Body: { scope, intent, text, source?, tenant? }. Super Admin only."""
    from app.services.ai.knowledge_storage import add_training_example
    scope = (body.get("scope") or "tenant").strip().lower()
    if scope not in ("global", "tenant"):
        raise HTTPException(status_code=400, detail="scope must be global or tenant")
    intent = (body.get("intent") or "").strip()
    text = (body.get("text") or "").strip()
    if not intent or not text:
        raise HTTPException(status_code=400, detail="intent and text are required")
    tenant = body.get("tenant") if scope == "tenant" else None
    doc = add_training_example(tenant=tenant, scope=scope, intent=intent, text=text, source=body.get("source"))
    return {"item": doc}


# ---------- Menu entry for frontend ----------

@router.get(
    "/menu",
    dependencies=[Depends(get_current_user)],
    summary="AI Assistant menu entry (show only for super_admin)",
)
def get_menu(user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """Return menu entry for AI Assistant. Frontend should show this item only when user is super_admin."""
    role = str(user.get("role") or "").lower()
    return {
        "id": "ai_assistant",
        "label": "AI Assistant",
        "description": "Configure AI keywords, intents, and training data (Super Admin only)",
        "visible": role == "super_admin",
        "path": "/ai-assistant",
    }
