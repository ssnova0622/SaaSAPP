"""
AI module configuration schema and defaults.
Tenant-level toggles and thresholds for AI features (salon, clinic, store, core).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Default AI config merged into tenant settings when missing
DEFAULT_AI_CONFIG: Dict[str, Any] = {
    # No-show prediction (salon/clinic)
    "no_show_reminder_threshold": 0.5,  # suggest reminder when score >= this (0-1)
    "no_show_high_risk_threshold": 0.7,  # high risk when score >= this
    "no_show_reminder_lead_hours": 24,  # suggest reminder N hours before
    "no_show_block_threshold": 3,  # block booking when customer no_show_count >= this (0 = disabled)

    # Low-stock forecast (store)
    "low_stock_days_default": 30,
    "low_stock_lead_time_days": 3,
    "low_stock_safety_days": 2,
    "low_stock_alert_days": 7,  # alert when days_to_stockout < this

    # Cart recovery (store)
    "cart_recovery_window_hours": 24,
    "cart_recovery_max_messages_per_cart": 2,

    # Dynamic pricing guardrails (store/salon)
    "dynamic_pricing_min_multiplier": 0.8,  # never suggest below base * this
    "dynamic_pricing_max_multiplier": 1.2,  # never suggest above base * this
    "dynamic_pricing_max_discount_pct": 20.0,

    # Slot recommendations (salon/clinic)
    "slot_recs_prefer_morning": False,
    "slot_recs_prefer_afternoon": False,

    # Feature toggles (override capability; if false, feature is off even when cap enabled)
    "features": {
        "no_show_scores": True,
        "appointment_recs": True,
        "reschedule_propose": True,
        "personalize_services": True,
        "staff_balance": True,
        "dynamic_pricing": True,
        "low_stock_forecast": True,
        "cart_recovery": True,
        "sales_forecast": True,
        "whatsapp_followup": True,
        "treatment_insights": True,
        "biz_insights": True,
    },

    # WhatsApp intents (AI Pro): configurable keywords per intent. Tenant can add phrases via ai_config.intent_keywords.
    # Example: { "refund_policy": ["where is my amount", "my money"], "delivery_eta": ["when will it come"] }
    "intent_keywords": {
        "book_appointment": ["book", "appointment", "schedule", "timing", "slot", "reserve"],
        "cancel_appointment": ["cancel", "delete", "remove", "stop", "cancel appointment"],
        "reschedule_appointment": ["reschedule", "change time", "new time", "different time", "change", "move"],
        "suggest_professional": ["suggest", "recommend", "best", "available", "professional", "doctor", "stylist"],
        "professional_details": ["professional", "doctor", "stylist", "expert", "who is", "tell me about",
                                 "check doctor"],
        "check_price": ["price", "cost", "how much", "how many", "buy", "product", "catalog", "item", "service",
                        "facial", "haircut", "consultation", "dental", "test drive"],
        "show_offers": ["offer", "discount", "promo", "deal", "coupon", "sale"],
        "refund_policy": ["refund", "return policy", "return money", "money back", "cancel order", "where is my amount",
                          "my money", "get money back"],
        "delivery_eta": ["delivery time", "how long", "expect order", "when expect", "when order", "arrive",
                         "shipping time", "delivery days", "when will it come"],
        "order_status": ["order", "track", "status", "where is my", "shipped", "dispatch", "my order"],
        "product_recommendation": ["show", "need", "want", "looking for", "recommend", "suggest", "find", "get me",
                                   "cheap", "affordable", "best", "cake", "shoes", "product", "item"],
        "faq": ["hour", "open", "close", "contact", "phone", "address", "policy", "faq", "help"],
    },
    # Order of intent checks (first match wins). Tenant cannot change order.
    "intent_keywords_order": [
        "cancel_appointment", "reschedule_appointment", "book_appointment",
        "suggest_professional", "professional_details",
        "check_price", "show_offers",
        "refund_policy", "delivery_eta", "order_status", "product_recommendation", "faq",
    ],
    # Fallback when no intent matches or menu has no option. Shown to Pro users so they can try again or use menu.
    "whatsapp_intent_fallback_message": "I didn't quite get that. You can ask about *refund*, *delivery*, *order status*, or *products*. Or type *menu* for options.",
}


def get_effective_ai_config(tenant_settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return merged AI config from tenant settings with defaults."""
    if not tenant_settings:
        return dict(DEFAULT_AI_CONFIG)
    raw = tenant_settings.get("ai_config")
    if not isinstance(raw, dict):
        return dict(DEFAULT_AI_CONFIG)
    out = dict(DEFAULT_AI_CONFIG)
    for k, v in raw.items():
        if k == "features" and isinstance(v, dict):
            out["features"] = {**out.get("features", {}), **v}
        elif k == "intent_keywords" and isinstance(v, dict):
            # Merge: default phrases + tenant-added phrases per intent (tenant can add e.g. "where is my amount" for refund_policy)
            default_kw = out.get("intent_keywords") or {}
            merged = {}
            for intent, phrases in default_kw.items():
                merged[intent] = list(phrases) if isinstance(phrases, list) else []
            for intent, phrases in v.items():
                if not isinstance(phrases, list):
                    continue
                base = merged.get(intent, [])
                merged[intent] = list(base) + [p for p in phrases if p and str(p).strip()]
            out["intent_keywords"] = merged
        elif k in out:
            out[k] = v
    return out


def get_no_show_thresholds(config: Dict[str, Any]) -> tuple[float, float]:
    """Return (reminder_threshold, high_risk_threshold)."""
    return (
        float(config.get("no_show_reminder_threshold", 0.5)),
        float(config.get("no_show_high_risk_threshold", 0.7)),
    )


def get_dynamic_pricing_guardrails(config: Dict[str, Any]) -> tuple[float, float, float]:
    """Return (min_multiplier, max_multiplier, max_discount_pct)."""
    return (
        float(config.get("dynamic_pricing_min_multiplier", 0.8)),
        float(config.get("dynamic_pricing_max_multiplier", 1.2)),
        float(config.get("dynamic_pricing_max_discount_pct", 20.0)),
    )


# Module -> suggested AI capabilities (for docs and UI)
MODULE_AI_CAPS: Dict[str, List[str]] = {
    "core": ["ai.biz_insights", "ai.whatsapp_followup", "ai.voice_actions"],
    "store": ["ai.predictions", "ai.dynamic_pricing"],
    "salon": ["ai.appointment_recs", "ai.no_show", "ai.reschedule", "ai.personalize", "ai.staff_balance",
              "ai.whatsapp_intents"],
    "clinic": ["ai.appointment_recs", "ai.no_show", "ai.reschedule", "ai.personalize", "ai.staff_balance",
               "ai.treatment_insights", "ai.whatsapp_intents"],
}
