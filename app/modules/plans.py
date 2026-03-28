"""Subscription plan definitions: default modules and capabilities per plan.

AI behavior (plan + modules + AI_ENABLED, see app.services.ai.feature_gate):
- basic: No AI unless Super Admin enables AI module for testing; then limited AI (Enterprise-like).
- enterprise: Limited AI (no NL) when AI module and capabilities are enabled. No AI_ENABLED flag.
- pro: Full AI + NL when AI module + capabilities + AI_ENABLED. If AI_ENABLED=false, behaves as Enterprise (limited AI, menu-based).

Super Admin can assign extra modules/capabilities to any tenant.
"""
from __future__ import annotations
from typing import Dict, List, Any

from app.helpers.constants_modules import SALON_MODULE, CORE_MODULE, STORE_MODULE, CLINIC_MODULE, AI_MODULE
from app.helpers.constants_plans import DEFAULT_PLAN, PLAN_TRIAL, PLAN_PRO, PLAN_IDS, PLAN_BASIC, PLAN_ENTERPRISE
from app.helpers.constants_capabilities import (
    CAP_CORE_SETTINGS,
    CAP_CORE_CUSTOMERS,
    CAP_CORE_STAFF,
    CAP_CORE_PROMOTIONS,
    CAP_CORE_FOLLOWUPS,
    CAP_CORE_REPORTS,
    CAP_CORE_RETENTION,
    CAP_CORE_WHATSAPP_MENU,
    CAP_SALON_PROFESSIONALS,
    CAP_SALON_APPOINTMENTS,
    CAP_SALON_SERVICES_VIEW,
    CAP_STORE_ORDERS,
    CAP_STORE_PAYMENTS,
    CAP_STORE_CATALOG,
    CAP_STORE_INVENTORY,
    CAP_AI_APPOINTMENT_RECS,
    CAP_AI_RESCHEDULE,
    CAP_AI_NO_SHOW,
    CAP_AI_PERSONALIZE,
    CAP_AI_STAFF_BALANCE,
    CAP_AI_DYNAMIC_PRICING,
    CAP_AI_WHATSAPP_FOLLOWUP,
    CAP_AI_TREATMENT_INSIGHTS,
    CAP_AI_VOICE_ACTIONS,
    CAP_AI_BIZ_INSIGHTS,
    CAP_AI_WHATSAPP_INTENTS,
)


def get_plan_defaults(plan_id: str) -> Dict[str, Any]:
    """Return default modules and capabilities for a plan. Unknown plan -> basic defaults. Trial uses Pro defaults."""
    plan = (plan_id or "").strip().lower() or DEFAULT_PLAN
    if plan == PLAN_TRIAL:
        plan = PLAN_PRO
    if plan not in _PLAN_DEFAULTS:
        plan = DEFAULT_PLAN
    return dict(_PLAN_DEFAULTS[plan])


def get_plan_metadata(plan_id: str) -> Dict[str, Any]:
    """Return label and description for a plan (for UI)."""
    plan = (plan_id or "").strip().lower()
    return dict(_PLAN_META.get(plan, _PLAN_META.get(DEFAULT_PLAN, {})))


def list_plans() -> List[Dict[str, Any]]:
    """Return all plans with defaults and metadata for Super Admin UI."""
    return [
        {
            "id": pid,
            **get_plan_metadata(pid),
            "modules": get_plan_defaults(pid)["modules"],
            "capabilities": get_plan_defaults(pid)["capabilities"],
        }
        for pid in PLAN_IDS
    ]


_PLAN_META = {
    PLAN_BASIC: {
        "label": "Basic",
        "description": "Rule-based only. No AI. User follows WhatsApp menu to book, cancel, or reschedule.",
    },
    PLAN_ENTERPRISE: {
        "label": "Enterprise",
        "description": "AI for slot suggestions, no-show detection, low stock. Appointment flow still menu-based.",
    },
    PLAN_PRO: {
        "label": "Pro",
        "description": "Full AI/NL: customer can type anything (book, cancel, product under 200, order status).",
    },
    PLAN_TRIAL: {
        "label": "14-day Trial (Pro)",
        "description": "Full Pro access for 14 days. Tenant is deactivated automatically after the trial ends.",
    },
}

# Default modules and capabilities per plan
_PLAN_DEFAULTS = {
    PLAN_BASIC: {
        "modules": [CORE_MODULE, SALON_MODULE],
        "capabilities": [
            CAP_CORE_SETTINGS,
            CAP_CORE_CUSTOMERS,
            CAP_CORE_STAFF,
            CAP_CORE_PROMOTIONS,
            CAP_CORE_FOLLOWUPS,
            CAP_SALON_PROFESSIONALS,
            CAP_SALON_APPOINTMENTS,
            CAP_SALON_SERVICES_VIEW,
        ],
    },
    # Enterprise: AI for assistive features only (slot recs, no-show, low stock). No NL intents; flows are menu-based.
    PLAN_ENTERPRISE: {
        "modules": [CORE_MODULE, SALON_MODULE, STORE_MODULE, CLINIC_MODULE, AI_MODULE],
        "capabilities": [
            CAP_CORE_SETTINGS,
            CAP_CORE_CUSTOMERS,
            CAP_CORE_STAFF,
            CAP_CORE_PROMOTIONS,
            CAP_CORE_FOLLOWUPS,
            CAP_CORE_REPORTS,
            CAP_CORE_RETENTION,
            CAP_CORE_WHATSAPP_MENU,
            CAP_SALON_PROFESSIONALS,
            CAP_SALON_APPOINTMENTS,
            CAP_SALON_SERVICES_VIEW,
            CAP_STORE_ORDERS,
            CAP_STORE_PAYMENTS,
            CAP_STORE_CATALOG,
            CAP_STORE_INVENTORY,
            CAP_AI_APPOINTMENT_RECS,
            CAP_AI_RESCHEDULE,
            CAP_AI_NO_SHOW,
            CAP_AI_PERSONALIZE,
            CAP_AI_STAFF_BALANCE,
            CAP_AI_DYNAMIC_PRICING,
            CAP_AI_WHATSAPP_FOLLOWUP,
            CAP_AI_TREATMENT_INSIGHTS,
            CAP_AI_VOICE_ACTIONS,
            CAP_AI_BIZ_INSIGHTS,
        ],
    },
    # Pro: Full NL (ai.whatsapp_intents). When AI_ENABLED=false, degrades to menu-based without errors.
    PLAN_PRO: {
        "modules": [CORE_MODULE, SALON_MODULE, STORE_MODULE, CLINIC_MODULE, AI_MODULE],
        "capabilities": [
            CAP_CORE_SETTINGS,
            CAP_CORE_CUSTOMERS,
            CAP_CORE_STAFF,
            CAP_CORE_PROMOTIONS,
            CAP_CORE_FOLLOWUPS,
            CAP_CORE_REPORTS,
            CAP_CORE_RETENTION,
            CAP_CORE_WHATSAPP_MENU,
            CAP_SALON_PROFESSIONALS,
            CAP_SALON_APPOINTMENTS,
            CAP_SALON_SERVICES_VIEW,
            CAP_STORE_ORDERS,
            CAP_STORE_PAYMENTS,
            CAP_STORE_CATALOG,
            CAP_STORE_INVENTORY,
            CAP_AI_WHATSAPP_INTENTS,
            CAP_AI_APPOINTMENT_RECS,
            CAP_AI_RESCHEDULE,
            CAP_AI_NO_SHOW,
            CAP_AI_PERSONALIZE,
            CAP_AI_STAFF_BALANCE,
            CAP_AI_DYNAMIC_PRICING,
            CAP_AI_WHATSAPP_FOLLOWUP,
            CAP_AI_TREATMENT_INSIGHTS,
            CAP_AI_VOICE_ACTIONS,
            CAP_AI_BIZ_INSIGHTS,
        ],
    },
}
