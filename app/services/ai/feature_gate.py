"""
Central AI feature gating: plan + modules + AI_ENABLED.

- Basic: No AI unless super admin enables AI (adds "ai" module) for testing.
- Enterprise: Limited AI (no NL) when "ai" module and relevant capabilities are enabled. No AI_ENABLED flag.
- Pro: Full AI + NL when "ai" module + capabilities + AI_ENABLED. If AI_ENABLED=false, behaves as Enterprise (limited AI, no NL).
"""
from __future__ import annotations

from app.helpers.constants_plans import DEFAULT_PLAN, PLAN_PRO, PLAN_BASIC, PLAN_ENTERPRISE


def _get_tenant_settings(tenant: str) -> dict:
    from app.core.container import get_tenant_service
    return get_tenant_service().get_tenant_settings(tenant) or {}


def get_plan(tenant: str) -> str:
    """Return tenant plan: basic | enterprise | pro. Default pro."""
    settings = _get_tenant_settings(tenant)
    plan = (settings.get("plan") or DEFAULT_PLAN)
    if isinstance(plan, str):
        plan = plan.strip().lower()
    if plan in (PLAN_BASIC, PLAN_ENTERPRISE, PLAN_PRO):
        return plan
    return DEFAULT_PLAN


def ai_modules_enabled(tenant: str) -> bool:
    """True if tenant has the AI module enabled (required for any AI feature)."""
    settings = _get_tenant_settings(tenant)
    modules = [str(m).lower() for m in (settings.get("modules") or [])]
    return "ai" in modules


def has_ai_capability(tenant: str, capability_id: str) -> bool:
    """True if tenant has the given capability in capabilities list."""
    settings = _get_tenant_settings(tenant)
    caps = [str(c).lower() for c in (settings.get("capabilities") or [])]
    return str(capability_id).strip().lower() in caps


def is_ai_globally_enabled(tenant: str) -> bool:
    """
    True if tenant is allowed to use any AI (limited or full).
    - Basic: only when AI module is enabled (super admin enabled for testing).
    - Enterprise: when AI module is enabled.
    - Pro: when AI module is enabled (full AI also requires AI_ENABLED; this is for "any AI").
    """
    return ai_modules_enabled(tenant)


def is_ai_capability_enabled(tenant: str, capability_id: str) -> bool:
    """
    True if this tenant can use the given AI capability (e.g. ai.no_show, ai.appointment_recs).
    Combines plan + modules + capabilities:
    - Basic: only if AI module enabled (by super admin) and capability in capabilities.
    - Enterprise: AI module and capability in capabilities.
    - Pro: AI module and capability in capabilities.
    """
    if not ai_modules_enabled(tenant):
        return False
    return has_ai_capability(tenant, capability_id)


def is_ai_nl_enabled(tenant: str) -> bool:
    """
    True only for Pro with AI module + AI_ENABLED + ai.whatsapp_intents capability.
    When False, WhatsApp uses menu-only (Enterprise/Basic behavior).
    """
    from settings import env
    plan = get_plan(tenant)
    if plan != PLAN_PRO:
        return False
    if not env.bool("AI_ENABLED", False):
        return False
    if not ai_modules_enabled(tenant):
        return False
    return has_ai_capability(tenant, "ai.whatsapp_intents")


def should_use_ai_in_flow(tenant: str) -> bool:
    """
    True if AI can be used inside flows (slot recs, no-show, time parsing, etc.).
    - Basic: when AI module enabled (testing).
    - Enterprise: when AI module enabled.
    - Pro: when AI module enabled (even if AI_ENABLED=false, limited AI in flow still works).
    """
    return ai_modules_enabled(tenant)
