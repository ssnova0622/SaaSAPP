from __future__ import annotations
from typing import Any, Dict, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .deps import get_current_user, ensure_tenant_active
from ..core.container import get_user_service
from ..services.core.promotions import promotions as svc

router = APIRouter()


# ---- Schemas ----
class Segment(BaseModel):
    type: str = Field(..., description="active|at_risk|churned")
    days: Optional[int] = None


class Audience(BaseModel):
    type: str = Field(default="all", description="all|tags|custom|segment")
    tags: Optional[list[str]] = None
    phones: Optional[list[str]] = None
    emails: Optional[list[str]] = None
    segment: Optional[Segment] = None


class Attachment(BaseModel):
    type: str = Field(..., description="image|video|link|document")
    url: str
    name: Optional[str] = None


class Button(BaseModel):
    id: str
    title: str
    url: Optional[str] = None


class ListRow(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None


class ListSection(BaseModel):
    title: Optional[str] = None
    rows: list[ListRow]


class CtaEntry(BaseModel):
    id: Optional[str] = None
    display_text: str = Field(default="Link", description="Button label (first row) or line prefix in body")
    url: str


class PromotionCreate(BaseModel):
    name: str
    channel: str = Field(default="both", description="whatsapp|email|both")
    message: str
    html_message: Optional[str] = None
    media_url: Optional[str] = None
    attachments: Optional[list[Attachment]] = None
    interactive_type: Optional[str] = Field(default=None, description="button|list|cta_url")
    buttons: Optional[list[Button]] = None
    list_sections: Optional[list[ListSection]] = None
    cta_url: Optional[str] = None
    cta_display_text: Optional[str] = Field(default=None, description="CTA button label, max ~20 chars for Meta")
    cta_footer: Optional[str] = None
    cta_entries: Optional[list[CtaEntry]] = None
    cta_append_urls_to_body: Optional[bool] = Field(
        default=None,
        description="When true, append Label: url lines to the message body. Default true if omitted.",
    )
    offer_code: Optional[str] = None
    audience: Audience = Field(default_factory=Audience)
    schedule_at: Optional[datetime] = Field(default=None, description="UTC ISO datetime to schedule sending")


class PromotionUpdate(BaseModel):
    name: Optional[str] = None
    channel: Optional[str] = None
    message: Optional[str] = None
    html_message: Optional[str] = None
    media_url: Optional[str] = None
    attachments: Optional[list[Attachment]] = None
    interactive_type: Optional[str] = None
    buttons: Optional[list[Button]] = None
    list_sections: Optional[list[ListSection]] = None
    cta_url: Optional[str] = None
    cta_display_text: Optional[str] = None
    cta_footer: Optional[str] = None
    cta_entries: Optional[list[CtaEntry]] = None
    cta_append_urls_to_body: Optional[bool] = None
    offer_code: Optional[str] = None
    audience: Optional[Audience] = None
    schedule_at: Optional[datetime] = None
    status: Optional[str] = Field(default=None, description="draft|scheduled|canceled")


class PromotionResponse(BaseModel):
    id: str
    tenant: str
    name: str
    channel: str
    message: str
    html_message: Optional[str] = None
    media_url: Optional[str] = None
    attachments: Optional[list[Attachment]] = None
    interactive_type: Optional[str] = None
    buttons: Optional[list[Button]] = None
    list_sections: Optional[list[ListSection]] = None
    cta_url: Optional[str] = None
    cta_display_text: Optional[str] = None
    cta_footer: Optional[str] = None
    cta_entries: Optional[list[CtaEntry]] = None
    cta_append_urls_to_body: Optional[bool] = None
    offer_code: Optional[str] = None
    audience: Dict[str, Any]
    status: str
    schedule_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None


class PromotionSendResponse(BaseModel):
    id: str
    tenant: str
    status: str
    total: int
    sent: int
    failed: int


class PromotionLogsResponse(BaseModel):
    items: list[Dict[str, Any]]
    total: int
    page: int
    size: int


# ---- Endpoints (JWT protected) ----
@router.post("/tenants/{tenant}/promotions", response_model=PromotionResponse, dependencies=[Depends(get_current_user)])
def create_promotion(tenant: str, body: PromotionCreate, user: dict = Depends(get_current_user),
                     _active_ok: bool = Depends(ensure_tenant_active)):
    user_id = user.get("sub") or user.get("email")
    doc = svc.create_promotion(
        tenant=tenant,
        name=body.name,
        channel=body.channel,
        message=body.message,
        html_message=body.html_message,
        media_url=body.media_url,
        attachments=[a.model_dump() for a in body.attachments] if body.attachments else None,
        interactive_type=body.interactive_type,
        buttons=[b.model_dump() for b in body.buttons] if body.buttons else None,
        list_sections=[s.model_dump() for s in body.list_sections] if body.list_sections else None,
        cta_url=body.cta_url,
        cta_display_text=body.cta_display_text,
        cta_footer=body.cta_footer,
        cta_entries=[e.model_dump() for e in body.cta_entries] if body.cta_entries else None,
        cta_append_urls_to_body=body.cta_append_urls_to_body,
        offer_code=body.offer_code,
        audience=body.audience.model_dump() if isinstance(body.audience, Audience) else (body.audience or {}),
        schedule_at=body.schedule_at,
        user_id=user_id,
    )

    # Resolve names
    user_ids = set()
    if doc.get("created_by"): user_ids.add(doc["created_by"])
    if doc.get("updated_by"): user_ids.add(doc["updated_by"])
    user_names = get_user_service().resolve_user_names(list(user_ids)) if user_ids else {}
    doc["created_by"] = user_names.get(doc.get("created_by")) or doc.get("created_by") or 'system'
    doc["updated_by"] = user_names.get(doc.get("updated_by")) or doc.get("updated_by") or '-'
    return doc


@router.get("/tenants/{tenant}/promotions", dependencies=[Depends(get_current_user)])
def list_promotions(tenant: str, _active_ok: bool = Depends(ensure_tenant_active)):
    items = svc.list_promotions(tenant)

    # Resolve names
    user_ids = set()
    for item in items:
        if item.get("created_by"): user_ids.add(item["created_by"])
        if item.get("updated_by"): user_ids.add(item["updated_by"])

    user_names = get_user_service().resolve_user_names(list(user_ids)) if user_ids else {}
    for item in items:
        item["created_by"] = user_names.get(item.get("created_by")) or item.get("created_by") or 'system'
        item["updated_by"] = user_names.get(item.get("updated_by")) or item.get("updated_by") or '-'

    return items


@router.get("/tenants/{tenant}/promotions/{promotion_id}", response_model=PromotionResponse,
            dependencies=[Depends(get_current_user)])
def get_promotion(tenant: str, promotion_id: str, _active_ok: bool = Depends(ensure_tenant_active)):
    doc = svc.get_promotion(tenant, promotion_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Promotion not found")

    # Resolve names
    user_ids = set()
    if doc.get("created_by"): user_ids.add(doc["created_by"])
    if doc.get("updated_by"): user_ids.add(doc["updated_by"])
    user_names = get_user_service().resolve_user_names(list(user_ids)) if user_ids else {}
    doc["created_by"] = user_names.get(doc.get("created_by")) or doc.get("created_by") or 'system'
    doc["updated_by"] = user_names.get(doc.get("updated_by")) or doc.get("updated_by") or '-'

    return doc


@router.put("/tenants/{tenant}/promotions/{promotion_id}", response_model=PromotionResponse,
            dependencies=[Depends(get_current_user)])
def update_promotion(tenant: str, promotion_id: str, body: PromotionUpdate, user: dict = Depends(get_current_user),
                     _active_ok: bool = Depends(ensure_tenant_active)):
    user_id = user.get("sub") or user.get("email")
    try:
        doc = svc.update_promotion(tenant, promotion_id, (body.model_dump(exclude_none=True)), user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not doc:
        raise HTTPException(status_code=404, detail="Promotion not found")

    # Resolve names
    user_ids = set()
    if doc.get("created_by"): user_ids.add(doc["created_by"])
    if doc.get("updated_by"): user_ids.add(doc["updated_by"])
    user_names = get_user_service().resolve_user_names(list(user_ids)) if user_ids else {}
    doc["created_by"] = user_names.get(doc.get("created_by")) or doc.get("created_by") or 'system'
    doc["updated_by"] = user_names.get(doc.get("updated_by")) or doc.get("updated_by") or '-'

    return doc


@router.delete("/tenants/{tenant}/promotions/{promotion_id}", dependencies=[Depends(get_current_user)])
def delete_promotion(tenant: str, promotion_id: str, _active_ok: bool = Depends(ensure_tenant_active)):
    ok = svc.delete_promotion(tenant, promotion_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Promotion not found")
    return {"ok": True}


@router.post("/tenants/{tenant}/promotions/{promotion_id}/send", response_model=PromotionSendResponse,
             dependencies=[Depends(get_current_user)])
def send_promotion(tenant: str, promotion_id: str, _active_ok: bool = Depends(ensure_tenant_active)):
    try:
        res = svc.send_promotion_now(tenant, promotion_id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tenants/{tenant}/promotions/{promotion_id}/logs", response_model=PromotionLogsResponse,
            dependencies=[Depends(get_current_user)])
def get_promotion_logs(
        tenant: str,
        promotion_id: str,
        page: int = Query(1, ge=1),
        size: int = Query(50, ge=1, le=200),
        status: Optional[str] = Query(default=None, description="sent|failed"),
        channel: Optional[str] = Query(default=None, description="whatsapp|email"),
        from_ts: Optional[datetime] = Query(default=None, description="ISO datetime inclusive lower bound"),
        to_ts: Optional[datetime] = Query(default=None, description="ISO datetime inclusive upper bound"),
        _active_ok: bool = Depends(ensure_tenant_active),
):
    return svc.list_logs(tenant, promotion_id, page=page, size=size, status=status, channel=channel, from_ts=from_ts,
                         to_ts=to_ts)
