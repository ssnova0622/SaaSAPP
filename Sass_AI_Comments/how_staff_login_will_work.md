### How staff login works in this app

Here’s the end‑to‑end behavior for Staff users (role `staff`) based on the current codebase and tenant model:

#### 1) Authentication and token
- Staff users authenticate via the same login flow as other roles and receive a JWT from the backend.
- The JWT payload includes at least `role`, `tenant`, and `caps` (capability ids):
  - `role`: should be `staff` for staff members.
  - `tenant`: the single tenant they are scoped to. Staff cannot switch tenants.
  - `caps`: per‑user capabilities (e.g., `store.catalog`, `store.orders`, etc.). These are enforced together with tenant capabilities from settings.

#### 2) Effective tenant is locked to JWT
- On the client, `useEffectiveTenant` parses the token:
  - For non‑super roles (`tenant_admin` and `staff`), it sets `effectiveTenant` to `jwt.tenant` and marks `isSuper = false`.
  - It does not allow changing the tenant; the global selector is hidden for these roles. Instead, a read‑only badge is shown in the AppBar indicating the current tenant.

#### 3) Navigation and permissions
- The left navigation (Drawer) is built in `AppShell` using:
  - The active tenant’s capability list from `getTenantSettings(effectiveTenant)` (tenant‑enabled capabilities).
  - The user’s own `caps` from the JWT.
- For non‑super users, a menu item is visible only if BOTH are true:
  - The tenant has that capability enabled (from tenant settings).
  - The user’s JWT `caps` includes that capability.
- Special case: AI Predictions requires the tenant’s AI flag in addition to caps (and is always visible for Super Admin).

#### 4) Data scoping and refresh
- All tenant‑aware pages query APIs with `effectiveTenant`.
- As Staff cannot change tenant, their pages naturally load only their JWT tenant’s data and ignore any tenant switch UI.

#### 5) Resulting UX for Staff
- On login, Staff land in the Admin UI scoped to their tenant.
- They see a read‑only banner in the header indicating the tenant and their role (“Staff”).
- They only see navigation items for which both tenant and user caps permit access.
- All operations (lists, CRUD, actions) are restricted to their tenant.

#### 6) Where this is implemented in code
- Token parsing and effective tenant selection: `admin_ui/src/hooks/useEffectiveTenant.ts` and also in `AppShell` for role/caps.
- Header UI and nav gating: `admin_ui/src/components/AppShell/AppShell.tsx`.
- Read‑only badge: `admin_ui/src/components/TenantContext.tsx` (`TenantBadge`).
- Pages use `useEffectiveTenant` to pass the tenant to API calls (examples: Users, Customers, Promotions, Professionals, Appointments, Store pages, etc.).

#### 7) Creating a staff user
- A Super Admin or Tenant Admin can create a Staff user in Users → New User.
- For Staff:
  - Set role = `staff`.
  - Ensure `tenant` is set (Super Admin can pick; Tenant Admin is locked to their own tenant).
  - Assign `caps` within what the tenant has enabled (UI already filters to allowed set).
- The new Staff user can then log in and will be scoped accordingly.

If you want, I can also outline the backend requirements (endpoints and token fields) to ensure the login issue is fully covered end‑to‑end.