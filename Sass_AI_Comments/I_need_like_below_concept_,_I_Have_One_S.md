### Goal
Implement a strict, simple multi‑tenant RBAC model:
- Super Admin: full system access; can view all tenants and assign capabilities to each tenant.
- Tenant Admin: scoped to their tenant; starts with no capabilities until Super Admin enables tenant capabilities; can create Staff and grant them a subset of tenant capabilities.
- Staff: scoped to their tenant; can access only capabilities explicitly granted to them.

All tenants are created “dark” (no capabilities). Access to features is controlled exclusively via capabilities (modules are deprecated/no‑op).

---

### Decision gate (confirm one)
- Option A (strict): Tenant Admin must also have per‑user caps. After Super Admin enables tenant capabilities, also assign those caps to Tenant Admin (manually or via auto‑sync), then Tenant Admin can assign subsets to staff.
- Option B (admin‑friendly): Tenant Admin bypasses per‑user caps; if a capability is enabled for the tenant, Tenant Admin automatically has it. Staff still require per‑user caps.

If you don’t choose, I will implement Option B by default for better UX.

---

### Backend plan
1) Capabilities as the single source of truth
- Keep `ensure_module_enabled` as a no‑op for backward compatibility (already done).
- Continue using `ensure_capability_enabled('<cap>')` for feature gating.

2) Tenant creation defaults ("dark" tenant)
- On `POST /tenants`, ensure the stored tenant settings explicitly include:
  - `modules: []`
  - `capabilities: []`
- Result: new tenant cannot use any features until Super Admin assigns capabilities.

3) Capability enforcement policy
- Option A: keep current behavior in `ensure_capability_enabled` (non‑super users must have cap in their own `caps` claim and tenant must enable it).
- Option B: change `ensure_capability_enabled` to bypass per‑user cap checks for role `tenant_admin` (only enforce on `staff`).

4) Tenant capability assignment (Super Admin)
- Endpoint: `PUT /tenants/{tenant}` accepts `{ capabilities: string[] }` and persists normalized list via `registry.normalize_selection`.
- `GET /modules` returns capability registry for Admin UI (already in place).

5) Tenant Admin and Staff management
- `POST /users` and `PATCH /users/{id}`: keep `_sanitize_caps_for_tenant` so Staff caps must be subset of tenant capabilities.
- If Option A, expose a helper to “sync tenant caps to a given user”: `POST /tenants/{tenant}/sync_caps_to_user/{userId}` (optional convenience endpoint), or instruct Super Admin to `PATCH /users/{id}` manually.

6) JWT contents
- JWT includes `role`, optional `tenant`, and `caps` (for Tenant Admin/Staff if Option A). No change needed.

7) Backward compatibility/migration
- For old tenants that relied on `category`/modules, set `capabilities` explicitly to the desired set using the Super Admin UI; modules are already deprecated.

---

### Admin UI plan (Super Admin)
1) Capabilities management UI (already present)
- Settings page lists all capabilities from `/modules` grouped by `group` with checkboxes.
- Save persists `{ capabilities: [...] }` via `PUT /tenants/{tenant}`.

2) Optional: Auto‑grant Tenant Admin
- If Option A, add a small action: “Grant these capabilities to Tenant Admin” that finds the tenant’s admin user and does `PATCH /users/{id}` with `caps` = tenant capabilities. Prompt to re‑login.
- If Option B, no per‑user grant needed for Tenant Admin.

3) UX prompts
- After saving capabilities, show tip:
  - Option A: “Ask Tenant Admin to re‑login to refresh permissions, or click ‘Grant to Tenant Admin’ now.”
  - Option B: “Tenant Admin can use enabled features immediately; staff still need per‑user caps.”

---

### Tenant Admin UI plan
1) Staff management
- Continue using `/users` endpoints to create/update Staff with caps.
- Cap picker should show only tenant‑enabled capabilities (read from `GET /tenants/{tenant}`), which already aligns with `_sanitize_caps_for_tenant` server‑side.

2) Visibility and navigation
- Hide/disable feature pages unless the tenant has the capability enabled.
- If Option A, also check the logged‑in user’s caps for visibility.
- If Option B, Tenant Admin visibility can key off tenant capabilities alone.

---

### Testing plan
1) Unit tests (backend)
- `ensure_tenant_scope` denies cross‑tenant access for Tenant Admin/Staff.
- `ensure_capability_enabled` admits/denies correctly for:
  - Super Admin (always admits regardless of user caps, tenant caps required only if you decide to enforce – currently tenant caps are still required; we can keep or relax for Super Admin if desired).
  - Tenant Admin (Option A: needs user cap; Option B: bypass user cap).
  - Staff (must have user cap and tenant cap).

2) Integration tests (API)
- Create tenant → verify `capabilities == []`.
- Super Admin assigns capabilities → verify protected endpoints open/close accordingly per role.
- Tenant Admin creates Staff and assigns subset → verify subset access works.

3) E2E (UI)
- Super Admin toggles capabilities and saves → Tenant Admin visibility changes accordingly (immediate for Option B, after re‑login for Option A).

---

### Rollout plan
1) Choose policy (Option A or B) and implement.
2) Deploy backend changes first.
3) Deploy Admin UI with capability management (already updated) and optional “Grant to Tenant Admin” action (Option A).
4) Migrate existing tenants by setting their capability lists via Super Admin UI.
5) Communicate to Tenant Admins:
- Option A: they must re‑login after caps are granted to refresh JWT.
- Option B: they will see features immediately after Super Admin enables them.

---

### Acceptance criteria
- New tenant has `capabilities: []` and cannot access protected routes.
- Super Admin can see all tenants and assign any capabilities.
- Tenant Admin is limited to their own tenant and cannot modify tenant capabilities.
- Staff creation limited to Tenant Admin (within their tenant) and Super Admin; staff caps are validated against tenant capabilities.
- Access to each protected route requires tenant capability; for user‑level:
  - Option A: Tenant Admin and Staff must have the capability in their `caps`.
  - Option B: Tenant Admin automatically has tenant capabilities; Staff still need per‑user caps.

---

### What I need from you
Please confirm which policy to implement for Tenant Admin:
- Option A (strict) or Option B (admin‑friendly)?

Once you choose, I’ll apply the minimal code updates (a small change in `ensure_capability_enabled` for Option B, or an optional utility/endpoint/UI action to sync caps for Option A), and verify with targeted tests.