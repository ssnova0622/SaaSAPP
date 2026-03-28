### Objective
Design and implement a flexible WhatsApp Menu Action system that:
- Supports different business types (salon, clinic, store, etc.).
- Lets Super Admin enable modules/capabilities per tenant.
- Lets Tenant Admin build menus visually and choose from a filtered list of actions appropriate for their business type and enabled capabilities.
- Adds new actions like track order, check product/search catalog, etc.

---

### High‑level approach
- Introduce a first‑class Action Registry that describes all available action types, their parameters, required capabilities, and which business types they apply to.
- Update backend to dispatch actions via a common handler interface.
- Update Admin UI Menu Editor to render an Action Picker based on the registry and the tenant’s enabled modules/capabilities and business type.
- Add new store actions (track_order, check_product, browse_catalog, order_status, cancel_order) and enrich salon/clinic actions (book, cancel, enquiry).
- Keep Option B RBAC: Tenant Admin auto‑access to tenant‑enabled capabilities; Staff require per‑user caps.

---

### Detailed plan

1) Action Registry (backend)
- Define a static registry in code (can move to DB later) with entries:
  - `id`: machine name (e.g., `store.track_order`)
  - `label`: human label
  - `business_types`: array of strings (e.g., `['store']`, `['salon','clinic']`, or `['*']`)
  - `module`: module id (`store`, `salon`, `core`)
  - `requires_caps`: array of capability ids needed by the action
  - `params_schema`: simple JSON schema (shape + required fields) for Admin UI form rendering
  - `preview`: optional function/flag for sample output in editor
- Add endpoint `GET /v1/whatsapp/actions` that returns the registry. Guarded by `ensure_capability_enabled('core.whatsapp_menu')`.
- Map business types: from tenant settings `category` (e.g., `salon | clinic | store`). Default `core` actions apply to all.

2) Action handler interface (backend)
- Implement a dispatcher `run_action(tenant, action_id, params, ctx, locale)`:
  - Performs capability check via `requires_caps` from registry (we already have `_tenant_has_caps`).
  - Calls the concrete handler (function) for that `action_id`.
  - Returns reply text (MVP) or interactive payload (later for Meta Cloud real buttons).
- Refactor existing handlers to use registry ids:
  - `salon.select_timeslot` (existing `_action_select_timeslot`)
  - `core.open_ticket` (existing `_action_open_ticket`)
  - `core.show_offers` (existing `_action_show_offers`)
  - `core.open_url` (existing `_action_open_url`)

3) New store actions (backend)
- Add handlers (MVP):
  - `store.track_order` (params: `{ order_id?: string }`)
    - If no `order_id` in params or message context, prompt for it; else fetch order status (stub now) and reply.
  - `store.check_product` (params: `{ query?: string }`)
    - If `query` present, search in catalog (stub) and reply top 3; else prompt for query.
  - `store.browse_catalog` (params: `{ category?: string }`) → list a few items with prices.
  - `store.order_status` (alias of track_order, optional).
  - `store.cancel_order` (params: `{ order_id?: string }`) → acknowledge (MVP; no persistence yet).
- All require module `store` and appropriate caps like `store.catalog`, `store.orders`.

4) Clinic/Salon enhancements (backend)
- Add `clinic.book_doctor` mirroring `salon.select_timeslot` but reading doctors/departments.
- Add `salon.cancel_appointment` and `clinic.cancel_appointment` (MVP acknowledgement).
- Optional: unify as `appointments.cancel` with business type filter.

5) Session/context improvements (backend)
- Extend `whatsapp_sessions` `ctx` to store step‑by‑step input:
  - For `track_order`: remember awaiting `order_id` → next input fills it → run action.
  - For `check_product`: remember awaiting `query` → next input runs search.
- Add simple prompts and state machine helpers per action: `needs_more_input(ctx)`, `apply_input(ctx, text)`.

6) Admin UI — Action Picker & parameter forms
- Add `GET /v1/whatsapp/actions` client and types.
- In Menu Editor → when node type = Action:
  - Load registry.
  - Compute tenant filters: business type (tenant.category), enabled modules (`tenant.modules`), and tenant capabilities (`tenant.capabilities`).
  - Show dropdown grouped by module/business type; hide actions the tenant cannot use (or show disabled with a tooltip “Enable module/capability in Settings”).
  - Render dynamic parameter form from `params_schema` (e.g., text fields for `order_id`, `query`, `category`).
  - Persist selected `action_id` and `params` in the node.
- Backward compatibility: map old `action` strings to new `action_id`s on load (e.g., `select_timeslot` → `salon.select_timeslot`).

7) Templates per business type (Admin UI)
- Provide starter templates that include the new actions:
  - Salon: Book appointment, Offers, Enquiry, Cancel appointment.
  - Clinic: Book doctor, Enquiry, Cancel appointment.
  - Store: Browse catalog, Check product, Track order, Order status, Enquiry.
- Template import buttons already exist; update JSON to use `action_id`s and default `params`.

8) Validation
- Backend menu validation: if a node has `action_id`, verify it exists in registry and that `params` pass a lightweight schema check (types+required).
- UI validation: show inline errors for missing/invalid params; for disabled actions (missing module/cap), display guidance.

9) Triggers alignment
- Triggers `invoke_action` should reference `action_id` (and optionally `params`).
- Update backend trigger evaluation to support `invoke_action` by id.
- UI Trigger Edit: when action kind = `invoke_action`, show Action dropdown (registry‑based) and parameter form.

10) Meta Cloud interactive (future‑ready)
- Keep dummy interactive for now.
- When we add a Meta webhook, map `button_reply`/`list_reply` `id` to submenu options (we already generate rows from options) and dispatch to the correct `next` node.
- For actions that prompt for input (order id, search query), still accept free text replies; optional future: quick reply templates.

11) Security & RBAC
- Continue enforcing:
  - Tenant scope via `ensure_tenant_scope`.
  - Option B in `ensure_capability_enabled`: Tenant Admin auto‑access; Staff require per‑user caps.
  - Action capability requirements via registry `requires_caps` (checked server‑side at dispatch time).

12) Observability
- Add structured logs when actions run: `tenant`, `action_id`, latency, success/error.
- Optional: telemetry counters per action for analytics in the future.

13) Tests
- Unit tests for action registry filtering and param validation.
- Unit tests for handlers: timeslot, track order, check product (stubs OK), open ticket, open url, show offers.
- Integration tests: build menu with new actions → publish → simulate webhook inputs that exercise number selection, prompts, and final replies.
- UI tests: Action Picker renders correctly per business type; param forms validate and save; Trigger Edit supports `invoke_action` and multi‑value match.

14) Rollout
- Phase 1 (MVP): registry + new actions + UI picker + backend dispatch + basic sessions for prompts.
- Phase 2: real catalog/order integrations; Meta webhook for real interactive buttons; richer appointment flows.
- Migration: load existing menus, map old `action` strings to new `action_id` automatically in editor load; re‑publish unaffected.

---

### Initial action set by business type
- Core (all):
  - `core.open_ticket`, `core.show_offers`, `core.open_url`.
- Salon:
  - `salon.select_timeslot`, `salon.cancel_appointment` (MVP).
- Clinic:
  - `clinic.book_doctor`, `clinic.cancel_appointment` (MVP).
- Store:
  - `store.browse_catalog`, `store.check_product`, `store.track_order`, `store.order_status`, `store.cancel_order` (MVP stubs).

Each action declares its `module` and `requires_caps` so the UI can filter and the backend can enforce permissions.

---

### Acceptance criteria
- Admin UI Menu Editor shows an Action Picker filtered by tenant business type, enabled modules, and capabilities.
- Tenant Admin can add new actions (track order, check product, etc.) to their menus without JSON editing, fill parameters through forms, and publish.
- Bot/webhook executes selected actions, handles multi‑step prompts (order id, query), and returns appropriate replies.
- Existing menus remain compatible; old action strings are mapped to new `action_id`s on load.

---

### What I need from you
- Confirm the initial action list per business type and any specific parameters you want for each (e.g., `store.track_order` should ask for `order_id` and optionally `phone`?).
- Confirm capability mapping if different from defaults (e.g., `store.track_order` requires `store.orders`).
- Any custom business types beyond salon/clinic/store to include now.

Once confirmed, I will implement Phase 1 (registry + handlers + UI picker) and deliver a testable build.