### Goal
Display all available modules in Admin UI Settings so a Super Admin can enable/disable them per tenant. Changes must enforce visibility and access for both UI and API. Example: a Salon tenant may have only “Salon” module on, another Salon may additionally enable “Payments”; a Store tenant may enable Orders but keep Catalog off.

---

### High-level outcome
- A central registry of modules/capabilities (backend) with ids, labels, and descriptions.
- Tenant settings contain which modules/capabilities are enabled.
- Secure endpoints to read and update a tenant’s modules (Super Admin only for updates).
- UI Settings → Modules section lists all modules with descriptions; Super Admin can toggle per tenant.
- UI navigation and pages are shown/hidden based on enabled modules; API also enforces via dependencies.

---

### Proposed module model
- Module: a domain feature group, e.g., `salon`, `store`.
- Capability: a finer toggle inside a module, e.g., `store.orders`, `store.payments`, `store.catalog`, `salon.appointments`, `salon.professionals`.
- Examples to start with:
  - salon: `salon`, capabilities: `salon.professionals`, `salon.appointments`
  - store: `store`, capabilities: `store.orders`, `store.carts`, `store.payments`, `store.catalog` (future), `store.inventory` (future), `store.offers` (future)
  - core (always on, but optionally list for visibility): `customers`, `staff`, `promotions`, `followups`, `reports`, `retention`

---

### Detailed plan
1. Backend: registry and validation
- Create `app/modules/registry.py` with a static registry:
  - Each record: `{ id: 'store.orders', group: 'Store', label: 'Orders', description: 'Create and manage orders', default: true, dependsOn: ['store'] }`.
  - Include top-level modules (`salon`, `store`) and capabilities.
- Utility functions:
  - `all_modules()` and `all_capabilities()` flatten lists.
  - `normalize_enabled(set: list[str]) -> tuple[modules, capabilities]` ensures ids exist and removes duplicates.

2. Backend: tenant settings persistence
- Extend `Storage.get_tenant_settings()` to always return:
  - `modules: string[]` (domain modules)
  - `capabilities: string[]` (fine-grained toggles; default computed from enabled modules + registry defaults)
- Extend `Storage.update_tenant_settings()` to accept and validate `modules` and `capabilities` against the registry.
  - If `capabilities` omitted, compute defaults based on `modules`.
- Migration/backfill:
  - For existing tenants without `modules`, keep current default derivation from `category` (salon→`['salon']`, store→`['store']`).
  - Compute `capabilities` as registry defaults for the enabled modules.

3. Backend: enforcement
- Keep `ensure_module_enabled(module_id)` for coarse gating (`salon`, `store`).
- Add `ensure_capability_enabled(cap_id)` dependency for finer gating.
  - Apply to endpoints:
    - Store: `/carts`, `/orders` → `ensure_capability_enabled('store.orders')`
    - Payments (webhook, checkout ONLINE) → `ensure_capability_enabled('store.payments')`
    - Future Catalog/Inventory → guard with their capability.
  - Salon: keep module guard for now; split into capabilities later if needed.

4. Backend: management APIs
- New `GET /v1/modules` (Super Admin): returns the registry list (modules + capabilities) with metadata.
- Expose tenant’s enabled config:
  - Continue `GET /v1/tenants/{tenant}` including `modules` and `capabilities`.
  - Updates via existing `PUT /v1/tenants/{tenant}` accepting `{ modules?: string[], capabilities?: string[] }`.
- Authorization (Super Admin only for updates):
  - Extend JWT role in `get_current_user` to read `role` claim; enforce role check when `modules` or `capabilities` are in the update payload.

5. Admin UI: Modules section
- Data fetching:
  - `GET /v1/modules` to list everything with labels/descriptions and grouping.
  - `GET /v1/tenants/{tenant}` to read current `modules` and `capabilities`.
- UI:
  - Settings → Modules card shows grouped checkboxes:
    - Group Salon: `salon` (module), sub-items: professionals/appointments (capabilities if you choose to expose them now).
    - Group Store: `store` (module), sub-items: Orders, Carts, Payments, (Catalog, Inventory, Offers when ready).
    - Group Core (read-only by default): Customers, Staff, Promotions, Follow-ups, Reports, Retention.
  - Super Admin can toggle any checkbox; non-super_admin sees read-only chips.
  - Save button persists via `PUT /v1/tenants/{tenant}`.
  - “Restore defaults” button (optional) computes defaults from registry for current modules.

6. Admin UI: dynamic navigation and guards
- Maintain a UI registry mapping nav routes to required module/capability ids.
  - Example: `/store/orders` → requires `store.orders` capability.
- Use the tenant’s enabled list to filter menu items.
- Add a `<RequireCapability id="store.orders">` wrapper for routes; display a friendly “Feature not enabled for this tenant” page when blocked.
- Subtle UI behavior:
  - Checkout: If `store.payments` is disabled, hide/disable ONLINE payment method in the checkout form.

7. Data safety and UX edge cases
- Disabling a capability should:
  - Hide related UI immediately.
  - Keep existing data readable unless you decide otherwise (e.g., viewing past orders even if orders are disabled).
  - Enforce server-side guards to return 403 for protected actions.
- Validation on save: prevent enabling a capability if its parent module is off (UI + server).

8. Testing and verification
- Backend unit/integration:
  - Validation of registry normalization; invalid ids rejected.
  - Tenants with/without capabilities receive 200/403 per endpoint as expected.
  - Payments guard blocks ONLINE checkout when `store.payments` disabled.
- Frontend manual tests:
  - Toggle modules/capabilities and verify dynamic menus and guarded routes.
  - Checkout UI respects payment toggles.
  - Non-super_admin users can’t modify settings.

9. Rollout plan
- Step 1: Backend registry + storage changes + auth check → deploy.
- Step 2: UI Modules section hooked to `GET /v1/modules` and save via `PUT /tenants/{tenant}`.
- Step 3: Route guards based on capabilities + subtle UI tweaks (payments option).
- Step 4 (optional): Split salon features into explicit capabilities if needed.

10. Timeline estimate
- Backend registry + storage + guards: 0.5–1 day
- Auth role check and modules API: 0.5 day
- UI Modules page: 0.5–1 day
- Dynamic nav & guards + payment option toggle: 0.5 day
- QA and docs: 0.5 day

11. Acceptance criteria
- Settings → Modules displays all modules/capabilities from backend with labels and descriptions.
- Super Admin can enable/disable per tenant; non-super_admin cannot update.
- Menu/route visibility reflects selections without reload; backend enforces permissions.
- ONLINE checkout hidden/blocked when `store.payments` is disabled.

---

### Options to confirm
- Do you want core features (Customers/Staff/Promotions/Follow-ups/Reports/Retention) to be toggleable too, or always-on?
- Should tenants be allowed to read existing Orders when Orders capability is disabled, or fully blocked?
- Any default bundles per category beyond current ones (e.g., Store with Payments OFF by default)?

Once you confirm these choices, I can implement Step 1 (backend registry + guard and storage) immediately.