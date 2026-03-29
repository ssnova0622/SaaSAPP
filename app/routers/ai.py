from __future__ import annotations
import logging
from typing import Any, Dict, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query

from .deps import (get_current_user, ensure_tenant_active, ensure_tenant_scope, ensure_module_enabled,
                   ensure_capability_enabled)
from app.helpers.constants_capabilities import CAP_AI_PREDICTIONS
from app.core.container import (get_professional_service, get_reports_service, get_ai_service, get_tenant_service,
                                get_appointment_service)
from app.services.ai.config_schema import (
    get_effective_ai_config,
    get_no_show_thresholds,
    get_dynamic_pricing_guardrails,
    MODULE_AI_CAPS,
)
from ..helpers.constants import SLOT_STATUS_AVAILABLE

logger = logging.getLogger(__name__)

# Mutable ref so lazy import can cache the class for subsequent requests
_ai_predictor_ref: Dict[str, Any] = {}
try:
    from app.services.ai import AIPredictor

    _ai_predictor_ref["cls"] = AIPredictor
except Exception as e:
    logger.warning("AIPredictor import failed at load time: %s", e, exc_info=True)

router = APIRouter()


def _list_available_slots_for_first_professional(tenant: str) -> Dict[str, Any]:
    pros = get_professional_service().get_professionals(tenant)
    for p in pros:
        times: List[str] = []
        for s in getattr(p, "slots", []) or []:
            try:
                st = getattr(s, "status", SLOT_STATUS_AVAILABLE)
                tm = getattr(s, "time", "")
            except Exception:
                st = (s.get("status") if isinstance(s, dict) else SLOT_STATUS_AVAILABLE)  # type: ignore[attr-defined]
                tm = (s.get("time") if isinstance(s, dict) else "")  # type: ignore[attr-defined]
            if str(st).lower() == SLOT_STATUS_AVAILABLE and tm:
                times.append(str(tm))
        if times:
            # dedupe preserve order
            seen: set[str] = set()
            ordered = []
            for t in times:
                if t not in seen:
                    seen.add(t)
                    ordered.append(t)
            return {"professional": getattr(p, "name", None) or getattr(p, "id", None) or "", "slots": ordered}
    return {"professional": None, "slots": []}


def _list_times_for_professional_label(tenant: str, professional: str, limit: int = 10) -> List[str]:
    from app.services.salon.professional_service import ProfessionalService

    try:
        resolved = ProfessionalService.resolve_professional_raw(tenant, professional)
        target_pid = str(resolved.get("professional_id") or "")
    except ValueError:
        target_pid = ""

    pros = get_professional_service().get_professionals(tenant)
    out: List[str] = []
    for p in pros:
        d = p.model_dump() if hasattr(p, "model_dump") else {}
        pid = str(d.get("professional_id") or "")
        nm = d.get("name") or getattr(p, "name", None) or ""
        if target_pid:
            if pid != target_pid:
                continue
        elif str(nm) != str(professional):
            continue
        for s in getattr(p, "slots", []) or []:
            try:
                st = getattr(s, "status", SLOT_STATUS_AVAILABLE)
                tm = getattr(s, "time", "")
            except Exception:
                st = (s.get("status") if isinstance(s, dict) else SLOT_STATUS_AVAILABLE)  # type: ignore[attr-defined]
                tm = (s.get("time") if isinstance(s, dict) else "")  # type: ignore[attr-defined]
            if str(st).lower() == SLOT_STATUS_AVAILABLE and tm:
                out.append(str(tm))
            if len(out) >= limit:
                break
        break
    # dedupe
    seen: set[str] = set()
    ordered: List[str] = []
    for t in out:
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return ordered


@router.post(
    "/tenants/{tenant}/events",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai"))],
)
def post_event(tenant: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Generic tenant-scoped analytics/event collector.

    Body shape (flexible):
    {
      "type": "add_to_cart|product_view|checkout_start|order_placed|...",
      "ts": 1700000000 (optional; server will fill if missing),
      "data": { ... arbitrary payload ... }
    }
    """
    try:
        doc = get_ai_service().insert_event(tenant=tenant, data=body or {})
        return {"status": "ok", "id": doc.get("id")}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---- AI config (tenant-level toggles and thresholds) ----
@router.get(
    "/tenants/{tenant}/ai/config",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai"))],
)
def get_ai_config(tenant: str) -> Dict[str, Any]:
    """Return effective AI config for the tenant (merged with defaults). Includes module→capability map for UI."""
    settings = get_tenant_service().get_tenant_settings(tenant)
    if not settings:
        raise HTTPException(status_code=404, detail="Tenant not found")
    config = get_effective_ai_config(settings)
    return {"tenant": tenant, "ai_config": config, "module_ai_caps": MODULE_AI_CAPS}


@router.put(
    "/tenants/{tenant}/ai/config",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai"))],
)
def put_ai_config(tenant: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Update tenant AI config (partial merge). Body: { ai_config: { no_show_reminder_threshold?: 0.5, ... } }."""
    payload = (body or {}).get("ai_config")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="body.ai_config must be an object")
    settings = get_tenant_service().get_tenant_settings(tenant)
    current = get_effective_ai_config(settings)
    merged = dict(current)
    for k, v in payload.items():
        if k == "features" and isinstance(v, dict):
            merged["features"] = {**(merged.get("features") or {}), **v}
        else:
            merged[k] = v
    get_tenant_service().update_tenant_settings(tenant, {"ai_config": merged})
    settings = get_tenant_service().get_tenant_settings(tenant)
    return {"tenant": tenant, "ai_config": get_effective_ai_config(settings)}


# AI keywords & training: use AI Assistant module (Super Admin only): GET/POST/DELETE /v1/ai-assistant/knowledge, /ai-assistant/training-data

@router.get(
    "/tenants/{tenant}/ai/forecast_low_stock",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai")), Depends(ensure_module_enabled("store")),
                  Depends(ensure_capability_enabled(CAP_AI_PREDICTIONS))],
)
def forecast_low_stock(
        tenant: str,
        days: Optional[int] = Query(default=None, ge=7, le=120),
        lead_time: Optional[int] = Query(default=None, ge=0, le=30, description="Supplier lead time in days"),
        safety_days: Optional[int] = Query(default=None, ge=0, le=30, description="Safety stock in days of demand"),
        top: int = Query(default=50, ge=1, le=200),
) -> Dict[str, Any]:
    """Return low-stock forecast for top SKUs. Uses tenant ai_config defaults when params omitted. Items include alert when days_to_stockout < config threshold."""
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    ai_cfg = get_effective_ai_config(settings)
    days = days if days is not None else int(ai_cfg.get("low_stock_days_default", 30))
    lead_time = lead_time if lead_time is not None else int(ai_cfg.get("low_stock_lead_time_days", 3))
    safety_days = safety_days if safety_days is not None else int(ai_cfg.get("low_stock_safety_days", 2))
    alert_days = int(ai_cfg.get("low_stock_alert_days", 7))
    try:
        items = get_reports_service().forecast_low_stock(tenant=tenant, days=days, lead_time=lead_time,
                                                         safety_days=safety_days, top=top)
        for it in items:
            it["alert"] = (it.get("days_to_stockout") is not None and it["days_to_stockout"] < alert_days)
        return {"items": items, "days": days, "lead_time": lead_time, "safety_days": safety_days,
                "alert_days": alert_days}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/tenants/{tenant}/ai/top_sellers",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai")), Depends(ensure_module_enabled("store")),
                  Depends(ensure_capability_enabled(CAP_AI_PREDICTIONS))],
)
def top_sellers(
        tenant: str,
        days: int = Query(default=30, ge=7, le=120),
        top: int = Query(default=20, ge=1, le=100),
) -> Dict[str, Any]:
    try:
        items = get_reports_service().top_sellers(tenant=tenant, days=days, top=top)
        return {"items": items, "days": days}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/tenants/{tenant}/ai/predictions/summary",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai")), Depends(ensure_capability_enabled(CAP_AI_PREDICTIONS))],
)
def predictions_summary(
        tenant: str,
        days: int = Query(default=30, ge=7, le=120),
) -> Dict[str, Any]:
    try:
        doc = get_ai_service().predictions_summary(tenant=tenant, days=days)
        return doc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Sales forecast (moving average) — store module + ai.predictions
@router.get(
    "/tenants/{tenant}/ai/sales_forecast",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai")), Depends(ensure_module_enabled("store")),
                  Depends(ensure_capability_enabled(CAP_AI_PREDICTIONS))],
)
def sales_forecast(
        tenant: str,
        days: int = Query(default=30, ge=7, le=120),
        horizon: int = Query(default=14, ge=1, le=90),
) -> Dict[str, Any]:
    try:
        doc = get_ai_service().sales_forecast(tenant=tenant, days=days, horizon=horizon)
        return doc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Cart recovery insights — store module + ai.predictions
@router.get(
    "/tenants/{tenant}/ai/cart_recovery",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai")), Depends(ensure_module_enabled("store")),
                  Depends(ensure_capability_enabled(CAP_AI_PREDICTIONS))],
)
def cart_recovery(
        tenant: str,
        window_hours: Optional[int] = Query(default=None, ge=1, le=168),
        top: int = Query(default=10, ge=1, le=100),
) -> Dict[str, Any]:
    """Cart recovery insights. Uses tenant ai_config.cart_recovery_window_hours when window_hours omitted."""
    if window_hours is None:
        settings = get_tenant_service().get_tenant_settings(tenant) or {}
        ai_cfg = get_effective_ai_config(settings)
        window_hours = int(ai_cfg.get("cart_recovery_window_hours", 24))
    try:
        doc = get_ai_service().cart_recovery(tenant=tenant, window_hours=window_hours, top=top)
        return doc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---- Appointment recommendations (clinic/salon) ----
@router.get(
    "/tenants/{tenant}/ai/recommend_slots",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai")), Depends(ensure_capability_enabled("ai.appointment_recs"))],
)
def recommend_slots(
        tenant: str,
        professional: Optional[str] = Query(default=None, description="Optional professional/stylist/doctor name"),
        top: int = Query(default=3, ge=1, le=10),
) -> Dict[str, Any]:
    """Return recommended appointment time labels and rationale.

    Response shape:
    {
      "recommended": ["10:30", "11:00", ...],
      "rationale": "...",
      "all_available": ["09:30", ...]
    }
    """
    try:
        AIPredictor = _ai_predictor_ref.get("cls")
        if AIPredictor is None:
            try:
                from app.services.ai import AIPredictor as _Lazy
                _ai_predictor_ref["cls"] = _Lazy
                AIPredictor = _Lazy
            except Exception as e:
                logger.warning("AIPredictor lazy import failed: %s", e, exc_info=True)
        if AIPredictor is None:
            recs, why = [], "AI recommendations not available"
        else:
            recs, why = AIPredictor().recommend(tenant=tenant, professional=professional, top_k=top)
        # Gather a simple deduped list of all currently available times across (optionally filtered) professionals
        pros = get_professional_service().get_professionals(tenant)
        if professional:
            from app.services.salon.professional_service import ProfessionalService

            try:
                resolved = ProfessionalService.resolve_professional_raw(tenant, professional)
                target_pid = str(resolved.get("professional_id") or "")
            except ValueError:
                target_pid = ""

            filtered: List[Any] = []
            for p in pros:
                d = p.model_dump() if hasattr(p, "model_dump") else {}
                pid = str(d.get("professional_id") or "")
                nm = d.get("name") or getattr(p, "name", None)
                if target_pid:
                    if pid == target_pid:
                        filtered.append(p)
                elif str(nm) == str(professional):
                    filtered.append(p)
            pros = filtered
        avail: dict[str, None] = {}
        for p in pros:
            for s in getattr(p, "slots", []) or []:
                try:
                    st = getattr(s, "status", SLOT_STATUS_AVAILABLE)
                    tm = getattr(s, "time", "")
                except Exception:
                    st = (
                        s.get("status") if isinstance(s, dict) else SLOT_STATUS_AVAILABLE)  # type: ignore[attr-defined]
                    tm = (s.get("time") if isinstance(s, dict) else "")  # type: ignore[attr-defined]
                if str(st).lower() == SLOT_STATUS_AVAILABLE and tm:
                    avail[str(tm)] = None
        all_available = sorted(avail.keys())
        # Ensure frontend always receives list/string (avoids crash when AI recs are disabled)
        recommended = list(recs) if recs else []
        rationale_str = str(why) if why is not None else ""

        return {"recommended": recommended, "rationale": rationale_str, "all_available": all_available}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---- No-show prediction (salon/clinic) ----
@router.get(
    "/tenants/{tenant}/ai/no_show/scores",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai")), Depends(ensure_capability_enabled("ai.no_show"))],
)
def no_show_scores(tenant: str, window_days: int = Query(default=7, ge=1, le=60)) -> Dict[str, Any]:
    """Return heuristic no-show risk scores for upcoming appointments in window_days.
    Uses tenant ai_config for reminder/high-risk thresholds. Response includes suggest_reminder and high_risk flags.
    """
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    ai_cfg = get_effective_ai_config(settings)
    reminder_threshold, high_risk_threshold = get_no_show_thresholds(ai_cfg)
    try:
        appts = get_ai_service().list_upcoming_appointments(tenant=tenant, window_days=window_days)
    except Exception:
        appts = []
    items: List[Dict[str, Any]] = []
    for a in appts or []:
        past = 0
        try:
            past = get_ai_service().count_customer_noshows(tenant=tenant, customer_id=getattr(a, 'customer_id', None))
        except Exception:
            past = 0
        lead_minutes = 1440
        try:
            lead_minutes = int(getattr(a, 'lead_minutes', 1440))
        except Exception:
            pass
        score = min(0.95, 0.2 + 0.15 * past + (0.1 if lead_minutes < 180 else 0))
        score_rounded = round(float(score), 2)
        items.append({
            "appointment_id": getattr(a, 'id', None) or getattr(a, '_id', None),
            "customer_id": getattr(a, 'customer_id', None),
            "time": getattr(a, 'time', None) or getattr(a, 'start', None),
            "professional": getattr(a, 'professional', None),
            "score": score_rounded,
            "rationale": "Based on past no-shows and short lead time",
            "suggest_reminder": score_rounded >= reminder_threshold,
            "high_risk": score_rounded >= high_risk_threshold,
        })
    return {
        "items": items,
        "window_days": window_days,
        "config": {"reminder_threshold": reminder_threshold, "high_risk_threshold": high_risk_threshold},
    }


# ---- Auto-rescheduling proposals (salon/clinic) ----
@router.post(
    "/tenants/{tenant}/ai/reschedule/propose",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai")), Depends(ensure_capability_enabled("ai.reschedule"))],
)
def reschedule_propose(tenant: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Propose alternative slots for one or more appointments.
    Body: { appointments: [{ id, professional?, time }], reason?: string }
    Response: { proposals: [{ appointment_id, current_time, options: [time...] }]} """
    appts = (body or {}).get("appointments") or []
    proposals: List[Dict[str, Any]] = []
    for a in appts:
        prof = str((a.get("professional") or "")).strip() or None
        # list available slots for (same) professional as options
        opts: List[str] = []
        if prof:
            opts = _list_times_for_professional_label(tenant, prof, limit=5)
        else:
            found = _list_available_slots_for_first_professional(tenant)
            opts = (found.get("slots") or [])[:5]
        proposals.append({
            "appointment_id": a.get("id"),
            "current_time": a.get("time"),
            "options": opts,
        })
    return {"proposals": proposals}


@router.post(
    "/tenants/{tenant}/ai/reschedule/confirm",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai")), Depends(ensure_capability_enabled("ai.reschedule"))],
)
async def reschedule_confirm(tenant: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """One-click reschedule: confirm moving an appointment to a proposed slot. Body: { appointment_id, new_time, new_date? }."""
    appointment_id = (body or {}).get("appointment_id")
    new_time = (body or {}).get("new_time")
    new_date = (body or {}).get("new_date")
    if not appointment_id or not new_time:
        raise HTTPException(status_code=400, detail="appointment_id and new_time are required")
    user_id = "AI-Reschedule"
    try:
        appt = await get_appointment_service().reschedule_appointment(
            tenant=tenant,
            appointment_id=str(appointment_id),
            new_time=str(new_time).strip(),
            new_date=str(new_date).strip() if new_date else None,
            user_id=user_id,
        )
        return {"ok": True, "appointment": appt, "message": "Appointment rescheduled successfully."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---- Personalized service recommendations (salon/clinic) ----
@router.get(
    "/tenants/{tenant}/ai/personalize/services",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai")), Depends(ensure_capability_enabled("ai.personalize"))],
)
def personalize_services(tenant: str, customer_id: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    """Return next-best service recommendations (top add-ons by popularity; optional customer_id for future personalization)."""
    try:
        items = get_ai_service().top_services(tenant=tenant, days=30, top=5)
    except Exception:
        items = []
    rationale = "Popular add-ons in the last 30 days. Enable more data to get 'customers who booked X also booked Y' style recommendations."
    return {"items": items, "customer_id": customer_id, "rationale": rationale}


# ---- Staff load balancing (salon/clinic) ----
@router.get(
    "/tenants/{tenant}/ai/workload/balance",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai")), Depends(ensure_capability_enabled("ai.staff_balance"))],
)
def workload_balance(tenant: str, date: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    """Return recommended weighting per professional to balance workload (stub)."""
    pros = get_professional_service().get_professionals(tenant)
    # simple even split baseline
    n = max(1, len(pros) or 1)
    weights = {getattr(p, 'name', 'P'): round(1.0 / n, 2) for p in pros}
    return {"weights": weights, "date": date}


# ---- Dynamic pricing (store or salon) ----
@router.get(
    "/tenants/{tenant}/ai/pricing/quote",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai")), Depends(ensure_capability_enabled("ai.dynamic_pricing"))],
)
def pricing_quote(tenant: str, service_id: str = Query(...), time: Optional[str] = Query(default=None)) -> Dict[
    str, Any]:
    """Suggest a price adjustment with tenant ai_config guardrails (min/max multiplier, max discount %)."""
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    ai_cfg = get_effective_ai_config(settings)
    min_mult, max_mult, max_discount_pct = get_dynamic_pricing_guardrails(ai_cfg)
    base = get_ai_service().get_service_base_price(tenant=tenant, service_id=service_id) or 0.0
    adj = -0.1 if (time and time.endswith(":30")) else 0.0
    raw = base * (1.0 + adj)
    suggested = max(base * min_mult, min(base * max_mult, raw))
    discount_pct = ((base - suggested) / base * 100.0) if base > 0 else 0.0
    if discount_pct > max_discount_pct:
        suggested = round(base * (1.0 - max_discount_pct / 100.0), 2)
    else:
        suggested = round(max(0.0, suggested), 2)
    return {
        "service_id": service_id,
        "base_price": base,
        "suggested_price": suggested,
        "rationale": "Off-peak discount (capped)" if adj < 0 else "Standard",
        "guardrails": {"min_multiplier": min_mult, "max_multiplier": max_mult, "max_discount_pct": max_discount_pct},
    }


# ---- WhatsApp follow-up queue (all) ----
@router.post(
    "/tenants/{tenant}/ai/followup/queue",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai")), Depends(ensure_capability_enabled("ai.whatsapp_followup"))],
)
def followup_queue(tenant: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Queue follow-up messages (stub enqueues events)."""
    items = (body or {}).get("items") or []
    queued = 0
    for it in items:
        try:
            get_ai_service().insert_event(tenant=tenant, data={"type": "followup.queue", "data": it})
            queued += 1
        except Exception:
            pass
    return {"queued": queued}


# ---- Treatment history & insights (clinic) ----
@router.get(
    "/tenants/{tenant}/ai/insights/treatments",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai")), Depends(ensure_capability_enabled("ai.treatment_insights"))],
)
def treatment_insights(tenant: str, days: int = Query(default=90, ge=7, le=365)) -> Dict[str, Any]:
    try:
        doc = get_ai_service().treatment_insights(tenant=tenant, days=days)
    except Exception:
        doc = {"top_treatments": [], "repeat_rate": 0.0}
    return {"days": days, **doc}


# ---- Business insights summary (owner) ----
@router.get(
    "/tenants/{tenant}/ai/insights/summary",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai")), Depends(ensure_capability_enabled("ai.biz_insights"))],
)
def ai_insights_summary(tenant: str, range_days: int = Query(default=28, ge=7, le=120)) -> Dict[str, Any]:
    try:
        kpis = get_ai_service().ai_insights_summary(tenant=tenant, days=range_days)
    except Exception:
        kpis = {"utilization": 0.0, "no_show_risk": 0.0, "revenue_at_risk": 0.0, "top_services": [], "staff_load": {}}
    return {"tenant": tenant, "days": range_days, **kpis}


# ---- Voice notes → actions (all) ----
@router.post(
    "/tenants/{tenant}/ai/voice/ingest",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("ai")), Depends(ensure_capability_enabled("ai.voice_actions"))],
)
def voice_ingest(tenant: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """Accept a voice note reference (URL or provider id) and create a task for offline processing (stub)."""
    ref = (body or {}).get("ref") or (body or {}).get("url")
    if not ref:
        raise HTTPException(status_code=422, detail="ref/url is required")
    try:
        task = get_ai_service().insert_event(tenant=tenant, data={"type": "voice.ingest", "data": {"ref": ref}})
    except Exception:
        task = {"id": None}
    return {"status": "queued", "id": task.get("id")}
