### Plan: Super‑Admin controlled plug‑in/plug‑out modules for the whole SaaS

#### Objectives (what “done” means)
- Every feature area is modeled as a module/capability that can be enabled/disabled per tenant.
- If a module is disabled for a tenant:
  - UI hides its menus and routes (no entry points).
  - API endpoints for that module/capability return 403.
  - Background jobs for that module are not scheduled for the tenant.
- Only Super Admin can change module assignments; regular admins can only view.

---

### 1) Define a single source of truth: Module/Capability Registry (backend)
- Create `app/modules/registry.py` that enumerates modules and granular capabilities:
  - Top‑level modules: `salon`, `store`, potentially `showroom`, `clinic` (alias of salon), etc.
  - Capabilities (attach to modules):
    - salon: `salon.professionals`, `salon.appointments`
    - store: `store.orders`, `store.carts`, `store.payments`, `store.catalog` (future), `store.inventory` (future), `store.offers` (future)
    - core (optional toggles or always‑on): `core.customers`, `core.staff`, `core.promotions`, `core.followups`, `core.reports`, `core.retention`
- Each registry item contains: `id`, `group`, `label`, `description`, `type: 'module'|'capability'`, `defaults` (whether enabled when its parent module is enabled), and `dependsOn` (e.g., `store.orders` depends on `store`).
- Provide helpers:
  - `list_registry()` returns the entire catalog.
  - `normalize_selection(modules: string[], capabilities: string[])` → validates ids, removes duplicates, enforces dependencies.

Outcome: One transparent place to add/remove features without touching scattered code.

---

### 2) Persist enablement per tenant (backend)
- Storage shape (in tenants doc):
  - `modules: string[]` — enabled domain modules (e.g., `['salon']`).
  - `capabilities: string[]` — enabled fine‑grained capabilities.
- Extend `Storage.get_tenant_settings()`:
  - Always return normalized `modules` and `capabilities` using the registry (derive defaults if `capabilities` missing).
- Extend `Storage.update_tenant_settings()`:
  - Accept `modules` and `capabilities`; validate using the registry; enforce dependencies.
  - Only allow updates if the current user is Super Admin (see section 3).
- Migration/backfill:
  - Existing tenants without `modules` keep the current default derived from `category` (salon/clinic → `['salon']`, store → `['store']`).
  - Compute `capabilities` by enabling registry defaults for those modules.

---

### 3) Super Admin authorization (server‑side authority)
- JWT already carries `role` (we read `role` in `get_current_user`).
- Enforce that only `role === 'super_admin'` can update `modules` or `capabilities` fields:
  - In `PUT /v1/tenants/{tenant}`, if payload contains these fields and user is not super_admin → 403.
  - Optional: create a dedicated endpoint `PUT /v1/tenants/{tenant}/modules` and guard it with super_admin only.
- Read (GET) is allowed for admin users to render UI state, but cannot change.
- Audit trail: append an audit entry on module/capability changes (who changed what, when, old→new).

---

### 4) Strong enforcement (plug‑out means fully blocked)
- Keep `ensure_module_enabled(module_id)` for coarse gating (already applied to Salon/Store routes).
- Add `ensure_capability_enabled(cap_id)` for granular enforcement:
  - Store:
    - `/carts` & `/orders` → `store.orders`
    - Checkout ONLINE & payment intent & webhook association → `store.payments`
    - Future `/products` `/inventory` → `store.catalog`/`store.inventory`
  - Salon (optional now or later): split professionals vs appointments into `salon.professionals` / `salon.appointments`.
- Background jobs (scheduler): when iterating tenants, only register jobs for tenants with required module/capability enabled (e.g., store abandoned cart reminders only when `store.orders` enabled).

Result: When disabled, all entry points (UI/API/jobs) are closed.

---

### 5) Registry exposure API (for Admin UI)
- `GET /v1/modules` (Super Admin only): returns the registry list with `{ id, type, group, label, description, dependsOn, default }`.
- `GET /v1/tenants/{tenant}`: already returns settings — include `modules` and `capabilities`.
- `PUT /v1/tenants/{tenant}`: accept `modules` and `capabilities` updates (Super Admin only; otherwise 403).

---

### 6) Admin UI — Settings → Modules (Super Admin panel)
- Fetch `GET /v1/modules` and `GET /v1/tenants/{tenant}` on tenant change.
- UI design:
  - Show grouped lists with descriptions. Parent module checkbox controls immediate visibility of its child capabilities.
  - Capabilities checkboxes are enabled only if parent module is on.
  - “Restore defaults” button recalculates capability defaults for currently checked modules via the registry.
- Save button → `PUT /v1/tenants/{tenant}` with `{ modules, capabilities }`.
- Permissions:
  - If user is not Super Admin, render the state read‑only (disabled checkboxes, hide Save button).

---

### 7) UI navigation/route guards (full concealment)
- Maintain a UI registry mapping each page/route to a required module/capability id.
  - Example: `/store/orders` → `store.orders`. `/store/carts` → `store.orders` (or `store.carts` if split later).
- Menu rendering:
  - Only show items whose requirement is met by tenant’s settings.
- Route guards:
  - Wrap protected routes in `<RequireModule id="...">` / `<RequireCapability id="...">` components.
  - On deep links to disabled routes, show a friendly “This feature is not enabled for this tenant.” message.
- Page‑level conditional UI:
  - Hide ONLINE payment option on Checkout if `store.payments` is disabled (and block calls regardless).

---

### 8) Data safety and semantics
- Reading historic data when a capability is disabled:
  - Policy choice: either block completely (simplest) or allow read‑only access. Given your requirement ("can’t see anything"), plan to block both read and write: list/detail endpoints return 403 when the capability is off.
- Consistency: When disabling a parent module, force‑disable all its child capabilities on save (server normalization + UI feedback).

---

### 9) Testing & verification
- Backend tests/integration:
  - Validation of unknown module/capability ids rejected with 400.
  - Non‑super_admin updates to modules/capabilities → 403.
  - Tenants without a capability receive 403 on all guarded endpoints.
  - Enabling capability restores access immediately.
- UI manual tests:
  - As Super Admin: toggle modules/capabilities, menu changes instantly; deep links are blocked.
  - As Admin (non‑super): can’t toggle; sees only enabled features.

---

### 10) Rollout plan (incremental)
- Phase A (backend):
  - Implement registry + normalize/validate logic.
  - Enforce Super Admin check in `PUT /tenants/{tenant}` for modules/capabilities.
  - Introduce `ensure_capability_enabled` and apply to Store (orders/payments) and any other immediate targets.
  - Expose `GET /v1/modules` (super_admin only).
- Phase B (UI):
  - Build Settings → Modules panel (read/write for super_admin; read‑only otherwise).
  - Build UI registry + route guards + nav filtering.
  - Hide payment option ONLINE when `store.payments` disabled.
- Phase C (scheduler & polish):
  - Register jobs per tenant only for enabled modules/capabilities.
  - Add audit log entries for changes.

---

### Timeline estimate
- A: Backend registry + enforcement + Super Admin guard — 1 day
- B: Admin UI modules page + nav/route guards + payment option toggle — 1–1.5 days
- C: Scheduler filtering + audit + tests — 0.5 day

---

### Acceptance criteria
- Super Admin can toggle any module/capability for a tenant; non‑super_admin cannot.
- Disabled module/capability:
  - no menu, no route access (UI),
  - API returns 403 for all covered endpoints,
  - scheduler doesn’t run jobs for it.
- Changes take effect immediately for the current tenant after saving.

---

### Clarifications to confirm before implementation
- Should core features (Customers, Staff, Promotions, Follow‑ups, Reports, Retention) also be fully pluggable, or remain always on? Your note says “all the modules”, so I will include them as capabilities and block them entirely when disabled.
- Confirm policy that even read access is blocked when a module is disabled (the plan assumes full block).
- Current JWT roles: do we already issue `role: 'super_admin'` for your account? If not, I can add a temporary env‑based override for dev.

If this plan matches your expectations, I’ll start with Phase A (backend registry + Super Admin enforcement + capability guards) and report back with the updated endpoints and examples.