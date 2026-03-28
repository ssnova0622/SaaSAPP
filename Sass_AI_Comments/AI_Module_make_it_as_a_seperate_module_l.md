### Plan: Make AI a separate module with tenant-based enablement and context-specific features

#### 1) Define the AI module and capability flags
- Backend
  - Add module key `ai` to the tenant modules system (like `store`, `salon`).
  - Gate existing AI endpoints with `ensure_module_enabled("ai")` in addition to current guards.
  - Capabilities by vertical:
    - Common: `ai.predictions` (store analytics), `ai.appointment_recs` (clinic/salon recommendations)
  - Migration/compat: If a tenant already uses AI features, auto-enable `ai` module on first access.
- Admin UI
  - Read `modules` from `GET /tenants/{tenant}` and treat `ai` as a first-class module.
  - Add an AI entry in the Modules navigation, visible only if `ai` is enabled.

#### 2) Tenant settings UX to enable/disable AI module
- Admin UI → Settings → Modules
  - Add a switch “AI Module”. Toggling on adds `"ai"` to `modules` array for the tenant; toggling off removes it.
  - Show subordinate toggles depending on tenant vertical:
    - If tenant has `store` → “Store AI (predictions/forecasts)” → sets `ai.predictions` capability.
    - If tenant has `salon` or `clinic` → “Appointment AI (slot recommendations)” → sets `ai.appointment_recs` capability.
- Persist using existing `PUT /tenants/{tenant}` payload updating `modules` and `capabilities`.

#### 3) AI menu in Admin UI (left nav and pages)
- Add top-level “AI” menu visible when `ai` module is enabled.
  - If tenant has `store` module and `ai.predictions` → show AI → Predictions dashboard (existing `/ai/predictions`).
  - If tenant has `salon` or `clinic` and `ai.appointment_recs` → show AI → Appointments Assist page:
    - Brief description, toggle, and a quick test panel to fetch `recommend_slots` for a selected professional/date.
  - If both store and salon/clinic are present, show both sub-sections under AI.

#### 4) Route guarding and backend alignment
- Backend
  - Update `app/routers/ai.py`:
    - Add `Depends(ensure_module_enabled("ai"))` on all AI routes (including `recommend_slots`).
    - Keep existing `ensure_module_enabled("store")` where needed (store-specific endpoints).
  - Confirm WhatsApp integration checks `ai.appointment_recs` so behavior remains tenant-specific.
- Admin UI
  - Wrap AI pages in `RequireCapability` plus a module check:
    - Predictions page: require `ai` module + `ai.predictions`.
    - Appointment Assist page: require `ai` module + `ai.appointment_recs`.

#### 5) Conditional AI behavior by tenant vertical
- Store tenants
  - AI menu opens Predictions dashboard (already present at `/ai/predictions`).
  - Optional: add links to low stock, sales forecast, cart recovery.
- Salon/Clinic tenants
  - AI menu opens Appointments Assist (new page):
    - Displays “Recommended slots” pulled from `GET /tenants/{t}/ai/recommend_slots`.
    - Explain how WhatsApp booking already surfaces these recommendations.
- Mixed tenants (store + salon/clinic)
  - AI menu shows both tabs: “Predictions” and “Appointments Assist”.

#### 6) WhatsApp behavior
- No change for tenants without AI module or capability.
- With AI module + `ai.appointment_recs`, existing WhatsApp timeslot flow will continue to show “Recommended times” first (already implemented).

#### 7) Testing and verification
- Backend
  - Tests: access blocked when AI module is disabled; unblocked when enabled.
  - Store endpoints still require store module; clinic/salon recommendations require AI module + capability.
- Admin UI
  - Verify module toggle updates `modules`.
  - Verify AI menu visibility:
    - Only `store` + AI → show Predictions.
    - Only `salon/clinic` + AI → show Appointments Assist.
    - Both → show both tabs.
  - Verify WhatsApp flow still works as before for non-AI tenants and enhanced for AI-enabled tenants.

#### 8) Rollout and defaults
- Default: AI module off for all tenants.
- Super admin can enable per tenant; or seed rule enabling AI for selected demo tenants.
- Backward-compat guard: if a tenant already uses AI endpoints, set AI module on next read to prevent breaking existing flows.

#### 9) Deliverables
- Backend: route guard updates and optional migration hook.
- Admin UI: settings toggle, AI menu grouping, new Appointments Assist page, conditional navigation.
- Docs: brief section in README/admin guide on enabling AI module and what each vertical gets.
