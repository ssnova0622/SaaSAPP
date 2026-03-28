### Plan: Apply consistent tenant context across all pages (resolve tenant conflicts everywhere)

#### Objectives
- Make tenant context deterministic and automatic on every page.
- Eliminate conflicts from mixed sources (JWT, localStorage, URL) by defining one rule of truth per role.
- Ensure navigation always carries the correct tenant context, avoiding cross‑tenant API calls and 403s.

#### Core rules (single source of truth)
- Non‑Super users (tenant_admin, staff):
  - Effective tenant = tenant claim in JWT (always). Never ask to choose.
  - UI shows a read‑only badge for the tenant; all links/requests must use that tenant.
- Super Admin:
  - Effective tenant = last selected tenant stored in `localStorage.selected_tenant`. If none, auto‑select the first tenant returned by `/tenants`.
  - Show a tenant selector in page headers where the page is tenant‑scoped.
  - Always propagate `?tenant=<id>` in route URLs.

#### Shared utilities (standardize everywhere)
- Hook: `useEffectiveTenant()` (already created for WhatsApp pages)
  - Returns `{ effectiveTenant, ready, role }`.
  - Non‑super → JWT tenant; Super → last/first tenant (persist changes to localStorage).
- Helper: `withTenantParam(url, tenant)`
  - Appends or updates `?tenant=` on a URL string.
- Guard: `RequireCapability`
  - Uses JWT tenant for non‑super users, ignores stale `selected_tenant`.
  - Option B policy enforced: Tenant Admin auto‑access when tenant capability is enabled; Staff require per‑user caps.

#### Pages to audit and refactor (batch plan)
1) Settings module
- General Settings page
- Modules & Capabilities section
- Action: Replace ad‑hoc tenant reads with `useEffectiveTenant`. Show selector for Super Admin; badge for Tenant Admin. Ensure Save calls use the effective tenant.

2) Tenants module
- Tenants list and details are typically Super‑only; still ensure internal links to tenant‑scoped pages add `?tenant=`.

3) Users module
- Users list, Create/Edit
- Make caps dropdown source the tenant’s enabled capabilities via `GET /tenants/{tenant}` for Tenant Admin.
- Ensure create/update calls include the effective tenant in payload and the list is filtered by it.

4) Store module
- Orders, Payments
- Ensure routes and API calls include tenant path/param; gate UI with `ensure_module_enabled('store')` and capabilities. Keep Option B for Tenant Admin.

5) Catalog module
- Products, Categories
- Verify tenant path and capability gating. Use `useEffectiveTenant` in page header.

6) Appointments/Slots module (Salon/Clinic)
- Appointments list, Slots management
- Ensure tenant scoping across routes and API calls; header selector/badge consistent.

7) Promotions, Followups, Reports, Retention, Staff
- Each page: replace tenant sourcing with `useEffectiveTenant`; add selector (Super) or badge (Tenant Admin); gate visibility via capabilities; pass `?tenant=` in navigation links.

8) WhatsApp module (already mostly updated)
- Menus: carry `?tenant=` in all navigations (New/Edit/View/Fork). ✓
- Menu Editor: read `?tenant=`, persist for Super; badge for Tenant Admin. ✓
- Triggers: auto‑tenant via `useEffectiveTenant` (no selector). ✓
- Config: selector (Super) or badge (Tenant Admin); accept prefixed or unprefixed numbers. ✓

#### Navigation & routing rules
- When a page links to another tenant‑scoped route, always call `withTenantParam(targetUrl, effectiveTenant)`.
- For Super Admin, changing the top‑bar tenant immediately updates localStorage and triggers data reload.
- For non‑super roles, ignore `?tenant=` if it differs from JWT tenant (auto‑correct silently).

#### API client consistency checklist
- Ensure all client calls that require tenant either:
  - Use path style: `/v1/tenants/${tenant}/...`, or
  - Include `?tenant=${tenant}` where the API supports it (e.g., registry filters/WhatsApp actions list).
- Normalize all callers to use `effectiveTenant` from the hook.

#### UX safeguards
- No tenants available (fresh system): for Super Admin, show inline notice and disable actions; for others, show an error and sign out or request admin assistance.
- Tenant mismatch detected on page load (URL vs JWT): auto‑switch to effective tenant and raise a short toast: “Switched to your tenant context.”

#### Testing plan
- Unit: `useEffectiveTenant` behavior (roles, localStorage, fallback to first tenant) and `RequireCapability` Option‑B logic.
- Manual QA matrix:
  - Roles: Super Admin, Tenant Admin, Staff
  - Pages: Settings, Users, Catalog, Store, Appointments/Slots, Promotions, Followups, Reports, Retention, Staff, WhatsApp
  - Actions: Navigate between pages; create/edit entities; verify `?tenant=` persists and APIs use the correct tenant.
- Optional E2E: Cypress/Playwright smoke tests for tenant switching and critical flows.

#### Rollout strategy
- Phase 1 (done): WhatsApp module — Menus, Editor, Triggers, Config.
- Phase 2: Settings + Users (highest impact on day‑to‑day ops).
- Phase 3: Catalog + Store.
- Phase 4: Appointments/Slots.
- Phase 5: Promotions, Followups, Reports, Retention, Staff.
- After each phase:
  - Verify no regressions; check that navigation carries `?tenant=` and that pages render with the correct tenant context.
  - Remove any legacy tenant selection code in the refactored pages.

#### Acceptance criteria
- On every tenant‑scoped page:
  - Non‑Super users never see a tenant selector; a read‑only tenant badge is displayed.
  - Super Admins always see a tenant selector, and selections persist across pages.
  - Navigation links carry `?tenant=` and target pages load immediately in the same tenant context.
- All tenant‑scoped API calls use the effective tenant; cross‑tenant 403s disappear in normal use.
- `RequireCapability` allows Tenant Admin as soon as tenant capability is enabled, and Staff only when their per‑user caps include it.

#### Optional improvements
- Global tenant selector in the app shell for Super Admin (applies across all modules at once).
- Centralize route builders in a utility that auto‑applies `?tenant=`.
- Add a “Switch Tenant” quick‑action palette for Super Admin.

If you want, I can start with Phase 2 (Settings + Users) immediately and push the changes in a small batch so you can test within your current environment.