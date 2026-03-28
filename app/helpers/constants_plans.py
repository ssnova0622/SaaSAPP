# Plan ids exposed to API and UI
PLAN_BASIC = "basic"
PLAN_PRO = "pro"
PLAN_ENTERPRISE = "enterprise"
PLAN_TRIAL = "trial"  # 14-day Pro trial; same as Pro, tenant auto-deactivated after trial_ends_at
PLAN_IDS = [PLAN_BASIC, PLAN_PRO, PLAN_ENTERPRISE, PLAN_TRIAL]

# Default plan for existing tenants without a plan (backward compatibility)
DEFAULT_PLAN = PLAN_BASIC
