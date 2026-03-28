"""
Tenant capability names (tenant settings: capabilities[]).
All capability strings used in plans and across the app. Use these instead of hardcoding.
Shared across routers (store, admin, tenants), services (action_registry, whatsapp), and modules (plans).
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
CAP_CORE_SETTINGS = "core.settings"
CAP_CORE_CUSTOMERS = "core.customers"
CAP_CORE_STAFF = "core.staff"
CAP_CORE_PROMOTIONS = "core.promotions"
CAP_CORE_FOLLOWUPS = "core.followups"
CAP_CORE_REPORTS = "core.reports"
CAP_CORE_RETENTION = "core.retention"
CAP_CORE_WHATSAPP_MENU = "core.whatsapp_menu"

# ---------------------------------------------------------------------------
# Salon / clinic
# ---------------------------------------------------------------------------
CAP_SALON_PROFESSIONALS = "salon.professionals"
CAP_SALON_PROFESSIONALS_EDIT = "salon.professionals.edit"
CAP_SALON_PROFESSIONALS_EDIT_SENSITIVE = "salon.professionals.edit_sensitive"
CAP_SALON_PROFESSIONALS_MANAGE = "salon.professionals.manage"
CAP_SALON_APPOINTMENTS = "salon.appointments"
CAP_SALON_APPOINTMENTS_VIEW = "salon.appointments.view"
CAP_SALON_APPOINTMENTS_EDIT = "salon.appointments.edit"
CAP_SALON_SERVICES_VIEW = "salon.services.view"
CAP_SALON_NO_SHOW_BLOCKED = "salon.no_show_blocked"
CAP_SALON_NO_SHOW_BLOCKED_VIEW = "salon.no_show_blocked.view"
CAP_SALON_NO_SHOW_BLOCKED_EDIT = "salon.no_show_blocked.edit"

# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------
CAP_STORE_CATALOG = "store.catalog"
CAP_STORE_ORDERS = "store.orders"
CAP_STORE_ORDERS_VIEW = "store.orders.view"
CAP_STORE_ORDERS_EDIT = "store.orders.edit"
CAP_STORE_PAYMENTS = "store.payments"
CAP_STORE_INVENTORY = "store.inventory"

# ---------------------------------------------------------------------------
# AI
# ---------------------------------------------------------------------------
CAP_AI_APPOINTMENT_RECS = "ai.appointment_recs"
CAP_AI_NO_SHOW = "ai.no_show"
CAP_AI_PREDICTIONS = "ai.predictions"
CAP_AI_WHATSAPP_INTENTS = "ai.whatsapp_intents"
CAP_AI_RESCHEDULE = "ai.reschedule"
CAP_AI_PERSONALIZE = "ai.personalize"
CAP_AI_STAFF_BALANCE = "ai.staff_balance"
CAP_AI_DYNAMIC_PRICING = "ai.dynamic_pricing"
CAP_AI_WHATSAPP_FOLLOWUP = "ai.whatsapp_followup"
CAP_AI_TREATMENT_INSIGHTS = "ai.treatment_insights"
CAP_AI_VOICE_ACTIONS = "ai.voice_actions"
CAP_AI_BIZ_INSIGHTS = "ai.biz_insights"
