### Current status
Here’s a concise snapshot of what’s done vs. pending based on the latest implementation and plan.

#### Completed (high‑level)
- Unified tenant context utilities added and used where implemented:
  - `useEffectiveTenant` hook (JWT tenant for non‑super; persisted selector for Super Admin)
  - `TenantBadge` (read‑only) and `TenantSelector` (Super Admin)
  - `withTenantParam()` helper
- Store module pages refactored to the new tenant pattern:
  - Store → Products
  - Store → Categories
- WhatsApp module in place and aligned:
  - Menus (versioned view + fork), Menu Editor (visual + validations), Config (Twilio + Meta dummy, prefix normalization)
  - Triggers UI (multi‑value matches), backend triggers, dummy Twilio webhook, provider‑aware submenu rendering
  - Action registry and dispatcher (MVP), option‑B enforcement

### Pending items
Below are the remaining tasks, grouped by priority. Items marked with asterisks are near‑term next steps.

1) Catalog module refactor to unified tenant context (Day‑1 remainder) — in progress
- Apply `useEffectiveTenant` + header TenantSelector/TenantBadge to all Catalog pages (if separate from current Store pages).
- Verify/adjust all Catalog API calls to include the effective tenant.
- Confirm capability gating (`store.catalog`) per Option B (Tenant Admin auto‑access; Staff need per‑user caps).

2) Audit and standardize capability gating across UI
- Ensure every tenant‑scoped page uses `RequireCapability` with Option B logic:
  - Super Admin → allow
  - Tenant Admin → tenant must have capability
  - Staff → tenant must have capability AND user token has that cap

3) Day‑2 scope: Appointments/Slots and Promotions/Followups
- Appointments/Slots (Salon/Clinic):
  - Refactor pages to use `useEffectiveTenant` and correct tenant path params
  - Verify gating (e.g., `salon.professionals`, `salon.appointments`)
- Promotions & Followups:
  - Refactor to unified tenant handling and capability gating

4) Day‑3 scope: Reports, Retention, Staff (pages beyond Users list already refactored)
- Apply unified tenant pattern + capability gating
- Ensure all navigations append `?tenant=<id>` for Super Admin

5) WhatsApp interactive (Meta Cloud) — next enhancement
- Add inbound Meta webhook to parse `button_reply` / `list_reply` and map to submenu options
- Accept interactive reply IDs in the engine (advance flow without typing numbers)
- Keep Twilio text/TwiML fallback as-is

6) Admin UI: Action Registry integration (visual picker)
- Menu Editor: render an Action Picker based on `/v1/whatsapp/actions`, filtered by tenant business type, modules, and capabilities; show dynamic parameter forms and validations
- Triggers: support `invoke_action` via the same picker + params form

7) Backend actions + session UX
- Enhance action handlers:
  - Store: `check_product` (prompt for query), `track_order` (prompt for order_id) with simple FSM in session
  - Salon/Clinic: cancellation handlers (MVP acknowledgements)
- Session helpers to collect inputs (order id / query) and proceed; TTL configurable

8) Security hardening (post‑MVP)
- Optional Twilio signature validation (env‑gated) using tenant’s `auth_token`
- Basic rate‑limiting per From number; structured logs with PII redaction in prod

9) Tests & docs
- Unit tests: `useEffectiveTenant`, `withTenantParam`, `RequireCapability`; trigger parsing; action registry filter/validation
- Integration tests: WhatsApp draft→publish→versioned view; webhook step; triggers multi‑value contains; Meta webhook parsing when added
- Admin/Dev docs: tenant context behavior, Option‑B, WhatsApp setup (Twilio/Meta), menus/versioning/triggers, adding new actions

### Immediate next actions
- Finish Catalog refactor to unified tenant context and verify capability gating.
- Run a quick audit of `RequireCapability` usage across the UI to ensure Option‑B consistency.

If you want, I can start by completing the Catalog refactor now and report back with a short verification checklist (pages touched, API calls confirmed, and a quick demo of role‑based behavior).