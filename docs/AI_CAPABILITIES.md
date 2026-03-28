# AI Module – Capabilities by Module

Configurable AI features are gated by **tenant modules** and **capabilities**. Tenant-level thresholds and toggles live in **`ai_config`** (GET/PUT `/v1/tenants/{tenant}/ai/config`).

## Module → AI capabilities

| Module | AI capabilities |
|--------|------------------|
| **core** | `ai.biz_insights`, `ai.whatsapp_followup`, `ai.voice_actions` |
| **store** | `ai.predictions` (low-stock, top-sellers, cart recovery, sales forecast), `ai.dynamic_pricing` |
| **salon** | `ai.appointment_recs`, `ai.no_show`, `ai.reschedule`, `ai.personalize`, `ai.staff_balance`, `ai.whatsapp_intents` |
| **clinic** | Same as salon, plus `ai.treatment_insights` |

When **ai** module is enabled, the tenants API derives default capabilities from enabled modules (e.g. store → `ai.predictions`, salon/clinic → `ai.appointment_recs`). Super Admin can add or remove capabilities per tenant.

## AI config (`ai_config`)

Stored in tenant settings. Defaults are applied when missing. Key fields:

- **No-show:** `no_show_reminder_threshold` (e.g. 0.5), `no_show_high_risk_threshold` (e.g. 0.7), `no_show_reminder_lead_hours` (e.g. 24), `no_show_block_threshold` (e.g. 3 — block booking when customer no_show_count ≥ this; 0 = disabled).
- **Low-stock:** `low_stock_days_default`, `low_stock_lead_time_days`, `low_stock_safety_days`, `low_stock_alert_days` (alert when `days_to_stockout` < this).
- **Cart recovery:** `cart_recovery_window_hours`, `cart_recovery_max_messages_per_cart`.
- **Dynamic pricing:** `dynamic_pricing_min_multiplier`, `dynamic_pricing_max_multiplier`, `dynamic_pricing_max_discount_pct`.
- **Feature toggles:** `features.no_show_scores`, `features.appointment_recs`, etc. (can override capability for soft-disable).
- **WhatsApp:** `whatsapp_intent_fallback_message` (when intent is unclear).

## Endpoints using `ai_config`

- **No-show scores** – Uses reminder/high-risk thresholds; response includes `suggest_reminder`, `high_risk` and `config`.
- **Forecast low-stock** – Uses `low_stock_*` defaults when query params omitted; each item has `alert` when `days_to_stockout` < `low_stock_alert_days`.
- **Cart recovery** – Uses `cart_recovery_window_hours` when `window_hours` omitted.
- **Pricing quote** – Applies min/max multiplier and max discount % from config; response includes `guardrails`.

## One-click reschedule

- **POST** `/v1/tenants/{tenant}/ai/reschedule/confirm`  
  Body: `{ "appointment_id": "...", "new_time": "10:00", "new_date": "2026-03-05" }`  
  Confirms moving an appointment to a proposed slot (use after `/ai/reschedule/propose`).

## Recommended setup

1. Enable **ai** module and the modules you use (store, salon, clinic).
2. Set **capabilities** (or rely on derived defaults).
3. Adjust **ai_config** per tenant (thresholds, fallback message).
4. Use **suggest_reminder** from no-show scores to trigger reminders; use **alert** from low-stock to surface reorder prompts.
