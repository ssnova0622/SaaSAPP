### Summary of the approach you want
You want a strict multi‑tenant RBAC model with three levels:
- Super Admin: full system control, can see all tenants, and is the only role that can assign modules/capabilities to tenants.
- Tenant Admin: scoped to one tenant, cannot see other tenants, can create staff for their tenant, and can assign capabilities to their staff but only from what Super Admin enabled for that tenant.
- Staff: scoped to one tenant, can access only the capabilities granted to them by the Tenant Admin.

Additionally, new tenants should be created with a bootstrap Tenant Admin account but with no modules/capabilities enabled, so the tenant can’t use any modules until Super Admin assigns them.

Below I map this onto your current codebase and point out the exact places to use or tweak.

---

### What already exists in your codebase
- Role and tenant scoping (good):
  - `app/routers/deps.py` has `get_current_user`, `ensure_super_admin`, `ensure_tenant_scope`.
  - `ensure_tenant_scope()` blocks tenant_admin/staff from crossing tenant boundaries.
- Module/capability guards (good):
  - `ensure_module_enabled("<module>")` and `ensure_capability_enabled("<capability>")` are already applied in routers such as `catalog.py`, `appointments.py`, `slots.py`, `store.py`.
  - `ensure_capability_enabled` also enforces that non‑Super users must have the capability in their own `caps` claim.
- Registry of modules/capabilities (good):
  - `app/modules/registry.py` lists modules and capabilities, and the helper `normalize_selection(modules, capabilities)` validates & resolves dependency defaults.
- Tenant settings endpoints (good):
  - `PUT /tenants/{tenant}` in `app/routers/tenants.py` allows updating a tenant’s `modules` and `capabilities` and already restricts this to `super_admin`.
- User management (good):
  - `app/routers/users.py` allows Super Admin to create `tenant_admin`/`staff` and Tenant Admin to create `staff` for their own tenant.
  - Capabilities for a staff user are sanitized against tenant‑enabled capabilities via `_sanitize_caps_for_tenant`.

These pieces are almost exactly what you need.

---

### The one behavior that conflicts with your requirement
- In `ensure_module_enabled` there is a backward‑compat fallback:
  - If a tenant has no `modules` configured (empty), it infers a module from tenant `category` (e.g., salon → enables `salon`).
  - For your requirement (“new tenants start with no modules”), this fallback will silently grant modules. You’ll want to turn it off once you adopt the strict model.

Minimal change recommendation:
- Keep the `category` field for context, but stop auto‑enabling modules by category if the `modules` key exists (even if empty).
- Practically, set `modules: []` and `capabilities: []` when you create a tenant, and update `ensure_module_enabled` to skip the category fallback if the `modules` key is present.

Suggested rule for `ensure_module_enabled`:
- If `modules` is present in tenant settings: trust it as source of truth (even if it’s empty) → no fallback.
- If `modules` is missing entirely (old data): optionally keep the old category‑based fallback for legacy tenants.

That exactly matches your desired “new tenants start with nothing” behavior while not breaking older data.

---

### End‑to‑end flow to achieve your desired model
1) Super Admin creates a tenant (bootstrap only)
- Endpoint: `POST /tenants`
- Payload model: `TenantCreate` in `app/models/schemas.py` (it already includes `admin_email`, `admin_password`, optional `tz`, etc.)
- Current behavior: creates tenant, seeds domain data, and creates a `tenant_admin` user; does not assign any modules/capabilities.
- What to ensure: after creation, the tenant’s settings should include `modules: []` and `capabilities: []`. If your storage layer doesn’t set these by default, set them to empty arrays at seed time.

2) Super Admin assigns tenant modules and capabilities
- Endpoint: `PUT /tenants/{tenant}` (already guarded to Super Admin when changing `modules`/`capabilities`).
- Typical payload (use the registry ids from `app/modules/registry.py`):
  ```json
  {
    "modules": ["store"],
    "capabilities": [
      "store.orders",
      "store.payments",
      "store.catalog"
    ]
  }
  ```
- Server-side validation: run `registry.normalize_selection(modules, capabilities)` to get a clean set respecting dependencies. Store the normalized arrays.
- From now on, all routes protected with `ensure_module_enabled`/`ensure_capability_enabled` will open for this tenant.

3) Tenant Admin creates staff and assigns per‑user capabilities
- Endpoint for list/create/update users: `app/routers/users.py` (`/users` endpoints)
- Tenant Admin can:
  - `POST /users` with body:
    ```json
    {
      "email": "staff@demo.test",
      "password": "secret123",
      "role": "staff", 
      "tenant": "<tenant-id>",
      "caps": ["store.catalog", "store.orders"]
    }
    ```
  - The code automatically sanitizes caps to be a subset of the tenant’s enabled capabilities.
  - `PATCH /users/{id}` can adjust caps later; sanitization still applies.

4) Access enforcement at runtime (already implemented)
- For tenant data APIs (e.g., catalog/products):
  - Dependencies include `ensure_tenant_scope()` → Tenant Admin/Staff cannot access other tenants.
  - `ensure_module_enabled("store")` blocks everything if module not enabled.
  - `ensure_capability_enabled("store.catalog")` requires both:
    - Capability enabled for the tenant
    - And, for non‑Super Admin users, the user must have it in their token/user caps
- Super Admin bypass:
  - Super Admin does not need per‑user caps and is not tenant‑scoped; they can call any tenant’s endpoints for administration.

---

### Concrete changes to align strictly with your requirement
You can likely achieve your goal with very small tweaks:

- Tenant creation defaults (in `app/routers/tenants.py#create_tenant`):
  - When calling `Storage.seed_if_absent`, also set:
    - `modules: []`
    - `capabilities: []`
  - This makes the tenant “dark” until Super Admin assigns modules explicitly.

- Module fallback (in `app/routers/deps.py#ensure_module_enabled`):
  - Current code falls back to `category` whenever `mods` is empty. Change the condition to only fallback when the `modules` key is missing in the tenant settings document. If `modules` exists (even `[]`), don’t fallback.
  - Pseudocode logic:
    ```python
    t = Storage.get_tenant_settings(tenant)
    if "modules" in t:  # explicit, even if empty
        mods = t.get("modules") or []
    else:
        # legacy fallback by category
        mods = derive_from_category(t.get("category"))
    ```
  - This preserves backward compatibility and achieves “no modules by default” for new tenants.

- Capability enforcement (already correct):
  - `ensure_capability_enabled` checks tenant caps first, then user caps for tenant_admin/staff. Keep as is.

- Token contents
  - Ensure your login process includes `role`, `tenant` (for tenant_admin/staff), and `caps` for staff in the JWT claims so the middleware has what it needs.

---

### Admin UI and API usage checklist
- Super Admin UI:
  - Use `GET /modules` to fetch the registry for building the “Assign Modules & Capabilities” UI.
  - After creating a tenant, call `PUT /tenants/{tenant}` with the selected `modules` and `capabilities`.
- Tenant Admin UI:
  - User management screen uses `/users` endpoints to create/update staff.
  - When editing a staff user, only show capabilities that are enabled for the tenant (read from `GET /tenants/{tenant}`’s `capabilities`).
- Feature gating in UI:
  - Hide or disable module UIs (e.g., Catalog) unless both the module and the specific capability are enabled for the tenant, and the logged‑in user has that capability (unless they’re Super Admin).

---

### Example: minimal payloads/flows
- Create tenant (Super Admin):
  ```http
  POST /tenants
  {
    "tenant": "demo1",
    "category": "store",
    "admin_email": "owner@demo1.test",
    "admin_password": "secret12345"
  }
  ```
  Storage should persist at least:
  ```json
  {
    "tenant": "demo1",
    "active": true,
    "category": "store",
    "modules": [],
    "capabilities": []
  }
  ```

- Assign modules/caps (Super Admin):
  ```http
  PUT /tenants/demo1
  {
    "modules": ["store"],
    "capabilities": ["store.orders", "store.payments", "store.catalog"]
  }
  ```

- Tenant Admin creates staff:
  ```http
  POST /users
  {
    "email": "cashier@demo1.test",
    "password": "secret123",
    "role": "staff",
    "tenant": "demo1",
    "caps": ["store.orders", "store.catalog"]
  }
  ```

Now that staff user can use Orders and Catalog routes for `demo1`.

---

### Recap of the only code change likely needed
- Disable the category→module fallback for tenants that explicitly have a `modules` key (even if empty). This makes new tenants start with truly zero modules until Super Admin assigns them.

If you want, I can provide the exact patch for `ensure_module_enabled` and the small addition to the tenant seeding so `modules` and `capabilities` are set to empty arrays for new tenants. Let me know if you’d prefer me to generate those changes now.