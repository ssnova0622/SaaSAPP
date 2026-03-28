# Refactor & Optimization – Complete List of Changes

This document lists all changes implemented and the remaining recommendations for the items you requested.

---

## 1. Implemented in This Session

### 1.1 WhatsApp Config button removed from WhatsApp Menus page
- **File:** `admin_ui/src/pages/WhatsApp/MenusIndex.tsx`
- **Change:** Removed the "Config" button and `onConfig()` handler. WhatsApp config remains available only under **Settings → WhatsApp Config** tab (and the standalone `/whatsapp/config` route if needed).
- **Reason:** Config is already in tenant Settings; duplicate entry point removed.

### 1.2 Template-based messaging (configurable auto-replies)
- **New file:** `app/services/core/message_templates.py`
  - Single source of default message templates (WhatsApp generic, booking, follow-ups).
  - `get_message(tenant, key, **placeholders)` resolves from tenant settings (`message_templates` or `templates`) then falls back to defaults.
  - No hardcoded user-facing strings at call sites; all go through this service.
- **Backend**
  - `app/routers/whatsapp/routes.py`: Removed local `_DEFAULT_MESSAGE_TEMPLATES` and `_get_message_template`. All usage replaced with `msg_tpl.get_message(tenant, key, ...)`. Replaced hardcoded "Hello!", "Service offline", "Feature not available", "Processing...", "Done." with template keys `whatsapp_hello`, `whatsapp_service_offline`, `whatsapp_feature_not_available`, `whatsapp_processing`, `whatsapp_done`.
  - `app/services/core/followups_service.py`: Removed hardcoded `FOLLOWUP_TEMPLATES`. `format_message(tenant, ftype, payload)` now uses `message_templates.get_message(tenant, followup_confirm | followup_reminder24 | followup_reminder2 | followup_post | followup_recovery | followup_default)`.
- **Tenant storage:** `message_templates` added to allowed keys in `app/services/storage/tenant_storage.py` so tenants can override any template via Settings/API.

### 1.3 Follow-ups configurable per tenant (which events get messages)
- **Backend:** `app/services/core/followups_service.py`
  - Added `_followup_prefs_for_tenant(tenant)` reading `followup_prefs` from tenant settings (default: all event types enabled).
  - `schedule_for_appointment` now only creates follow-up tasks for event types where `followup_prefs[ftype]` is True (confirm, reminder24, reminder2, post).
- **Frontend:** `admin_ui/src/pages/Settings.tsx`
  - In **Notifications** tab: new subsection **Follow-up events** with checkboxes: Confirm (immediate), Reminder 24h before, Reminder 2h before, Post-visit (thanks). Each can be turned off per tenant.
  - "Save follow-up options" calls `updateTenantSettings(tenant, { followup_prefs: { confirm, reminder24, reminder2, post } })`.

---

## 2. Suggested Next Steps – Implemented

### 2.1a Actions consolidated (single registry)
- **`app/services/whatsapp/action_registry.py`** – single source: `ACTION_REGISTRY`, `get_actions_for_tenant(tenant)`, `get_action_meta(action_id)`.
- **`app/routers/whatsapp/routes.py`** – imports from action_registry; `list_whatsapp_actions` uses `get_actions_for_tenant(tenant)`.
- **`app/services/whatsapp/dispatcher_service.py`** – imports `ACTION_REGISTRY` from action_registry.
- **`app/services/whatsapp/admin_service.py`** – uses `get_actions_for_tenant` / `ACTION_REGISTRY` from action_registry.
- **`app/services/workflow/registry.py`** – imports `ACTION_REGISTRY` from action_registry.

### 2.2a Workflow engine docstrings and architecture doc
- **`app/services/workflow_engine.py`** – module docstring and class/method docstrings added.
- **`docs/WORKFLOW_ARCHITECTURE.md`** – high-level flow (triggers → workflow → FSM → menu), action registry, workflow engine.

### 2.3a Theme guidelines and one fix
- **`docs/UI_THEME_GUIDELINES.md`** – palette, do’s/avoid, theme provider.
- **`admin_ui/src/pages/Store/Products.tsx`** – placeholder SVG and Avatar border use theme-aligned colors.

### 2.4a Permission model (module.action)
- **Backend:** `app/routers/deps.py` – `ensure_permission(scope, action)` for route protection.
- **Frontend:** `admin_ui/src/hooks/useCapabilities.ts` – generic `can(scope, action)`.
- **`docs/PERMISSIONS.md`** – permission model, backend deps, frontend hook, scope naming.

### 2.5a Tests
- **`test/unit/services/test_message_templates.py`** – get_message defaults, placeholders, override, unknown key.
- **`test/unit/services/test_followups_service.py`** – followup_prefs default and tenant disables, format_message.
- **`test/unit/services/test_action_registry.py`** – ACTION_REGISTRY content, get_action_meta, get_actions_for_tenant (with mocked WorkflowEngine and get_tenant_service).
- **`test/conftest.py`** – conftest updated so tests run when `app_ref` is missing (use `app.services.db` + mongomock when available).

### 2.6a Payments: Stripe and Razorpay
- **`app/services/payments.py`** – `StripeProvider` and `RazorpayProvider`; `get_payments_provider(tenant)` returns them when `payment_config.provider` is `stripe`/`razorpay`. Credentials from `payment_config` (e.g. stripe_secret_key, razorpay_key_id/razorpay_key_secret). Optional deps: install `stripe` / `razorpay` to use.
- **`app/routers/store.py`** – `POST /payments/provider/stripe/webhook` and `POST /payments/provider/razorpay/webhook` to receive events and call `_payment_webhook_mark_done`.

---

## 3. Recommended / Partially Addressed (Further Work)

### 3.1 Code optimization, method descriptions, split large methods
- **Status:** Not done in this session.
- **Recommendation:** Add docstrings to all public functions in `app/routers/whatsapp/routes.py`, `app/services/workflow_engine.py`, `app/services/core/followups_service.py`, and key frontend pages. Split `routes.py` (2600+ lines) into modules, e.g. `whatsapp/triggers.py`, `whatsapp/menu_handlers.py`, `whatsapp/webhooks.py`, and keep a thin `routes.py` that imports and registers routes.

### 3.2 Remove unwanted code (frontend and backend)
- **Status:** Only Config button removed from Menus page.
- **Recommendation:** Audit nav items, buttons, and API endpoints; remove or hide any that are unused or deprecated. Run a dependency graph to find dead code.

### 3.3 Consolidate actions (done – see 2.1a)
- **Status:** Not done.
- **Current state:** Actions are defined in:
  - `app/routers/whatsapp/routes.py` (ACTION_REGISTRY, `_run_action`)
  - `app/services/whatsapp/dispatcher_service.py` (ACTION_REGISTRY, `run_action`)
  - `app/services/workflow/registry.py` (imports dispatcher’s registry)
  - `app/services/whatsapp/admin_service.py` (exposes registry)
- **Recommendation:** Introduce a single **action registry service** (or collection) that all callers use. Optionally store action definitions in a `whatsapp_actions` collection so new actions can be added without code. Refactor `_run_action` and dispatcher to call this single registry.

### 3.4 WhatsApp workflow engine (docstrings + doc done – see 2.2a) as “heart” – handle all cases, easy to understand
- **Status:** Not refactored.
- **Recommendation:** Document the flow (triggers → menu/FSM → workflow engine → actions). Extract conversation flow from `routes.py` into a dedicated `ConversationOrchestrator` or similar that delegates to workflow engine and action runner. Add high-level docstrings and a short architecture doc under `docs/`.

### 3.5 Theme consistency (guidelines + one fix – see 2.3a) (all pages, textboxes, labels, alerts)
- **Status:** Not audited.
- **Recommendation:** Use the existing `admin_ui/src/theme.ts` (e.g. MUI overrides) and ensure every page uses theme tokens (e.g. `sx`, `theme.palette`) for text, inputs, alerts, and selections. Replace any inline colors/fonts with theme values. Add a short “UI guidelines” section in docs.

### 3.6 Remove unwanted actions from screens and related code
- **Status:** Only Config button removed.
- **Recommendation:** List all buttons/actions per screen; remove or gate by role/capability any that are not required. Clean up related API/backend code.

### 3.7 Test cases (new unit tests – see 2.5a; expand for >80% coverage) – all scenarios, >80% code coverage
- **Status:** Not done.
- **Recommendation:** Add pytest tests for: message_templates (get_message, defaults), followups (schedule_for_appointment with followup_prefs, format_message), WhatsApp routes (trigger action with action_id, template resolution). Add frontend tests (e.g. React Testing Library) for Settings follow-up toggles and TriggerEdit. Aim for >80% coverage on new and touched modules first, then expand.

### 3.8 Remove duplication (frontend and backend)
- **Status:** Message template logic centralized; some duplication remains elsewhere.
- **Recommendation:** Identify repeated patterns (e.g. tenant resolution, error handling, list+paginate) and extract shared helpers or hooks. Backend: shared dependency for “get tenant settings” and “get message template.”

### 3.9 Nothing hardcoded – everything from collection/settings/env
- **Status:** User-facing WhatsApp and follow-up messages are now template-based and tenant-configurable. Defaults live in `message_templates.py` (could later be moved to a JSON file or env).
- **Recommendation:** Move default template text to a JSON file or env if you want zero hardcoded strings. Keep feature flags and URLs in env/settings.

### 3.10 Role-based access (ensure_permission + can() – see 2.4a) (plugin concept, read/create/edit/delete per page per role)
- **Status:** Not implemented.
- **Current state:** Backend uses `ensure_tenant_scope`, `ensure_super_admin`, `ensure_module_enabled`, `ensure_capability_*`. Frontend uses `RequireCapability` and Sidebar caps.
- **Recommendation:** Define a simple permission model (e.g. `module.action` like `core.settings.update`, `salon.appointments.create`). Backend: check permission in deps or per-route. Frontend: show/hide create/edit/delete buttons and routes by permission. Store permissions per role in DB or config.

### 2.11 SMS functionality (tenant preference: SMS only / email only / WhatsApp / mix)
- **Status:** Already supported. Tenant settings have **Notification channels** (Email, WhatsApp, SMS) and `sms_config`. Messaging service sends via configured channels; follow-ups use phone/email from the follow-up doc.
- **Recommendation:** No code change required; document in user guide. Optionally add “default channel for follow-ups” per tenant if you want to force one channel when both phone and email exist.

### 3.12 Payment integration (Stripe/Razorpay providers + webhooks – see 2.6a)
- **Status:** Placeholder only. `app/services/payments.py` has `DummyProvider`; Stripe/Razorpay are “coming soon” in Settings.
- **Recommendation:** Implement real providers in `payments.py` (e.g. `StripeProvider`, `RazorpayProvider`), add webhook routes, and wire checkout to use them when tenant selects Stripe/Razorpay.

### 2.13 Meta Direct (like Twilio) – tenant can choose
- **Status:** Already supported. Provider choice in WhatsApp config: Twilio or Meta Cloud. Routes: `POST /integrations/twilio/whatsapp/webhook` and `POST /integrations/meta/whatsapp/webhook`. Tenant selects provider in Settings → WhatsApp Config.
- **Recommendation:** Document in admin guide. No code change required for “tenant can prefer anything.”

---

## 3. Summary Table

| Item | Done | Notes |
|------|------|--------|
| Remove WhatsApp Config from Menus page | Yes | Button and handler removed |
| Template-based messaging (configurable replies) | Yes | message_templates service + defaults; WhatsApp & follow-ups use it |
| Follow-ups configurable per event type | Yes | followup_prefs in Settings; schedule_for_appointment respects it |
| Optimize code, docstrings, split large methods | No | Recommended as next step |
| Clean up unwanted code | Partial | Only Config button |
| Consolidate actions (single class/collection) | No | Recommended |
| Workflow engine cleanup / single entry | No | Recommended |
| Theme consistency | No | Recommended |
| Remove unwanted actions from screens | Partial | Only Config |
| Tests >80% coverage | No | Recommended |
| Remove duplication | Partial | Templates centralized |
| No hardcoding (collection/settings/env) | Partial | Messages via templates; other config already in settings |
| Role-based CRUD / plugin concept | No | Recommended |
| SMS (tenant preference) | Yes | Already supported |
| Payment integration | No | Placeholder only; real providers to be added |
| Meta Direct like Twilio | Yes | Already supported |

---

## 4. Files Touched in This Session

- `admin_ui/src/pages/WhatsApp/MenusIndex.tsx` – removed Config button
- `app/services/core/message_templates.py` – **new** central template service
- `app/services/core/followups_service.py` – use message_templates; followup_prefs for scheduling
- `app/services/storage/tenant_storage.py` – allowed `message_templates`; `followup_prefs` was already allowed
- `app/routers/whatsapp/routes.py` – use msg_tpl for all user-facing strings; removed local template dict and helper
- `admin_ui/src/pages/Settings.tsx` – Follow-up events subsection and save handler
- `docs/CHANGES_REFACTOR.md` – **new** this document
