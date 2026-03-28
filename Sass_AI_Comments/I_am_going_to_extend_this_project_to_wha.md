### Objective
Design and implement a clean, modular architecture so each business domain (Salon, Clinic, Store, Car Showroom, etc.) ships as a separate module. A Super Admin can assign modules to each tenant. Backend endpoints, background jobs, and Admin UI menus are dynamically enabled per-tenant. Example: Salon tenants don’t see Orders/Store, while Store tenants do.

---

### High‑level approach
- Introduce a first‑class `Module` concept with a central registry (e.g., `modules.registry`), and move domain features into self‑contained modules (routes, services, menus, permissions, schedulers).
- Add `tenant.modules: string[]` to tenant settings. Super Admin assigns modules per tenant.
- Enforce module access at the API layer via a `ensure_module_enabled(tenant, module_id)` dependency around module routes/services.
- Render Admin UI navigation and pages based on the assigned modules; modules contribute their own menu entries.
- Keep cross‑cutting concerns (Auth, Staff, Customers, Reports, Retention, Integrations) as shared core, but allow modules to extend them (e.g., Store adds Orders reports).

---

### Modules we’ll start with (extensible)
- core (always on): Auth, Tenants, Users/Staff, Customers, Promotions, Followups, Reports, Retention, Integrations, Realtime
- salon: Professionals, Slots, Appointments
- clinic: (alias of salon with medical labels; can split later if needed)
- store: Carts, Orders, Payments, Catalog (future), Inventory (future), Offers/Coupons (future)
- showroom (future): Leads, Test drives, Bookings, Quotes, Orders

Each module has:
- id: `"salon" | "clinic" | "store" | ...`
- label: human‑readable name
- backend: FastAPI routers, Pydantic schemas, services, optional schedulers
- ui: routes and menu entries for Admin UI
- capabilities: feature flags for granular enabling (e.g., `store.payments`, `store.catalog`)

---

### Data model updates
- Tenants document (Mongo):
  - `modules: string[]` — module ids assigned to tenant (e.g., `["salon"]` or `["store"]`).
  - Optional granular flags per module remain inside module configs (already have `payment_config`, `delivery_config` in store).
- Migration: backfill existing tenants with default modules derived from `category`:
  - `category in {"salon","clinic"}` → `modules=["salon"]`
  - `category in {"store"}` → `modules=["store"]`
  - Allow Super Admin to override later.

---

### Backend plan (FastAPI)
1) Module registry
- New `app/modules/__init__.py` with `Module` dataclass and a `registry: Dict[str, Module]`.
- Register built‑in modules: `salon`, `store`. `core` is implicit.
- Each module exports:
  - `routers: list[(router, prefix, tags)]`
  - `capabilities: list[str]` (optional)
  - `schedules: list[callable]` (optional)

2) Tenant settings
- Add `modules` to `Storage.get_tenant_settings` normalization with a safe default according to `category`.
- Extend `Storage.update_tenant_settings` to accept `modules` (Super Admin only; see RBAC below).

3) Access guard
- New dependency `ensure_module_enabled(module_id)`:
  - Resolves tenant (from path), loads tenant settings, checks module id in `tenant.modules`, else `HTTP 403`.
- Apply to all module routers:
  - Salon (slots, appointments): `ensure_module_enabled("salon")`.
  - Store (carts, orders, payments): `ensure_module_enabled("store")`.
- Keep `ensure_tenant_active` in place (compose both dependencies).

4) Router wiring
- In `create_app()`, include module routers via the registry rather than hardcoding per project growth. For now, we keep existing includes but add the guard on endpoints.

5) RBAC for Super Admin
- Extend `get_current_user()` or roles to include `role: super_admin`.
- New Admin endpoint to update tenant modules: `PUT /v1/tenants/{tenant}/modules` available only to super_admin.
- Alternatively, add `modules` to existing `PUT /tenants/{tenant}` but check role in the handler.

6) Scheduler separation per module
- Scheduler startup iterates tenants and registers per‑tenant jobs only for modules enabled:
  - e.g., daily reports job remains core.
  - store: abandoned cart reminders (future) only if `"store"` in modules.
  - salon: slot cleanup jobs only if `"salon"` in modules.

7) Backwards compatibility & deprecation
- Leave current endpoints in place but guarded by the new module dependency to avoid breaking URLs.
- Map `clinic` → `salon` module until clinic differentiates.

---

### Admin UI plan (Vite + React)
1) Module awareness
- Fetch `tenant.settings.modules` at login and whenever tenant changes. Store in a global store (e.g., context/hook).
- Build NAV dynamically from a `uiModulesRegistry` mirroring backend modules.
  - Salon menu items: Professionals, Appointments
  - Store menu items: Store — Carts, Store — Orders, (future: Products, Inventory, Offers)
  - Core menu remains always present: Settings, Tenants, Customers, Staff, Promotions, Followups, Reports, Retention
- Hide or disable routes not in assigned modules. Add a route guard `RequireModule({ moduleId })` that redirects to `/` if missing.

2) Super Admin UI for module assignment
- In Settings (or a Super Admin panel), add a `Modules` section with checkboxes for available modules per tenant.
- Only visible to `super_admin` users. If you don’t have role in JWT yet, we can hide client‑side and rely on server enforcement.

3) Progressive loading
- Keep code splitting by page. Dynamic nav will only link to module pages if enabled. This reduces accidental navigation.

4) Empty state and banners
- If a user opens a deep link to a module not enabled, show a friendly message: “This feature isn’t enabled for your tenant. Contact support.”

---

### Enforcement summary (end‑to‑end)
- Data: `tenant.modules` is the single source of truth.
- API: `ensure_module_enabled("salon"|"store"|...)` dependency on every module route.
- UI: Dynamic menu + route guards per module.
- Jobs: Scheduler registers per‑tenant jobs for enabled modules only.

---

### Step‑by‑step implementation plan
1) Backend — foundations
- Add `modules: string[]` normalization + update in `Storage`.
- Add `ensure_module_enabled(module_id)` dependency in `app/routers/deps.py`.
- Apply the dependency to:
  - Salon module: `/appointments`, `/slots` routers.
  - Store module: `/store` router (carts, orders, payments webhook guarded where applicable; webhook can be public but cross‑checks order/tenant).
- Add Super Admin capability: extend `get_current_user` to include `role` and add checks in `PUT /tenants/{tenant}` for `modules` field.
- Migration script: for existing tenants, set default modules based on `category`.

2) Backend — scheduler
- In `main.py` startup `_register_daily_report_jobs`, continue as is (core).
- Add stubs for module jobs registered only if module present (to be filled when features arrive, e.g., abandoned cart reminders for `store`).

3) Admin UI — dynamic nav & route guards
- Create `uiModulesRegistry` mapping module ids → menu entries and route guards.
- Read `tenant.settings.modules` and store in context/hook.
- Update `AppShell` to render menu entries conditionally.
- Add `RequireModule` wrapper to module routes; protect Store and Salon pages accordingly.

4) Admin UI — Super Admin assignment UI
- Add a `Modules` card to `Settings` or a dedicated “Tenant Modules” page (under Tenants for Super Admin only): checkboxes for `salon`, `store`, `clinic` (alias of `salon`), `showroom` (disabled placeholder). Save via `PUT /tenants/{tenant}`.
- If you don’t yet have JWT roles, temporarily show to all users but rely on server enforcement; add a visual “Super Admin only” note.

5) Tests & verification
- Unit/integration API:
  - A tenant with `modules=["salon"]` can call appointments/slots; calling store orders returns 403 (module disabled).
  - A tenant with `modules=["store"]` sees store endpoints; appointments/slots return 403.
- Admin UI:
  - With salon tenant selected, menus for Store are hidden and route guard blocks deep links.
  - With store tenant selected, Store menus appear; salon menus hidden/blocked.
  - Toggling modules in Super Admin UI updates visibility after refresh.

6) Rollout
- Ship backend first (non‑breaking: defaults preserve current behavior).
- Then ship Admin UI dynamic menus and guards.
- Add Super Admin UI when JWT role is ready; until then, you can update `modules` directly in DB or via a temporary protected endpoint.

---

### Data contracts and examples
- Tenant JSON now includes modules:
```json
{
  "tenant": "ss-salon",
  "category": "salon",
  "modules": ["salon"],
  "store_enabled": true,
  "payment_config": { "provider": "dummy", "methods": ["ONLINE","COD"], "currency": "INR" },
  "delivery_config": { "delivery_enabled": true, "pickup_enabled": true }
}
```
- Super Admin updates modules:
```http
PUT /v1/tenants/ss-store
Authorization: Bearer <super_admin_token>
Content-Type: application/json

{
  "modules": ["store"]
}
```
- Calling a disabled module endpoint returns 403:
```json
{ "detail": "Module 'store' is not enabled for this tenant" }
```

---

### Future extensions (kept simple by the module architecture)
- Add `catalog` and `inventory` submodules under `store` with their own routers and UI pages; Super Admin can toggle sub‑capabilities if needed.
- Introduce `showroom` with its own routers (leads, test drives, quotes) without touching salon/store code.
- Module‑specific reports (e.g., Sales for store; Utilization for salon) are registered by the module and shown only if enabled.

---

### Risks and mitigations
- Drift between UI and API checks: mitigate by strict API enforcement and UI guards as convenience only.
- Role handling not yet present: initially protect via server (required); UI hides but isn’t a security boundary.
- Migration mistakes: provide a one‑time script and log counts of tenants updated.

---

### Deliverables checklist
- [ ] Backend: `modules` field support in tenants (get/update), migration/backfill defaults.
- [ ] Backend: `ensure_module_enabled()` dependency + applied to salon/store routes.
- [ ] Backend: Super Admin role check to update `modules`.
- [ ] UI: Dynamic nav + route guard by module.
- [ ] UI: Super Admin module assignment UI.
- [ ] Tests: API 403 for disabled modules, UI visibility/guards verified.

If you want, I can proceed to implement this plan in small PRs: backend guards and tenant `modules` first, then UI dynamic nav, and finally the Super Admin assignment UI.