### Overview
We’ll move from “any valid JWT = admin” to a proper, configurable authentication and authorization system backed by a single `users` collection. It will support three account types out of the box: `super_admin` (global), `tenant_admin` (scoped to one tenant), and `staff` (scoped to one tenant with allowed capabilities restricted by the tenant admin). All logins (including super admin) will live in Mongo, and JWTs will be issued by our API after password authentication.

### Target outcomes
- One Mongo collection for all accounts: `users`.
- Login via `email + password` → JWT with claims: `sub` (user id), `role`, `tenant?`, `caps?`.
- Super Admin can manage all tenants, modules/capabilities, and users for any tenant.
- Tenant Admin can manage only their tenant’s settings, modules/capabilities for their tenant, and their tenant’s users (staff).
- Staff can sign in, but can only see pages/features that match the capabilities assigned by the tenant admin.
- All API endpoints enforce role/capability/tenant scope; Admin UI hides/guards pages accordingly.

---

### Data model (Mongo)
Collection: `users`
- `_id`: ObjectId (string in API)
- `email`: string (unique, lowercased)
- `password_hash`: string (bcrypt)
- `role`: enum: `super_admin` | `tenant_admin` | `staff`
- `tenant`: string | null (required for `tenant_admin` and `staff`; null for `super_admin`)
- `display_name`: string
- `status`: enum: `active` | `disabled` (default `active`)
- `caps`: string[] (capability ids allowed for this user; optional for `tenant_admin`, required for `staff`)
- `created_at`, `updated_at`: datetime

Indexes:
- `users(email)` unique
- `users(tenant, role)`

Optional collection: `user_sessions` (if you want refresh tokens later)

Seeding on startup:
- If no `super_admin` exists and env `BOOT_SUPER_ADMIN_EMAIL` + `BOOT_SUPER_ADMIN_PASSWORD` are present, create one.

---

### Auth flows and endpoints (FastAPI)
- POST `/v1/auth/login` (public)
  - Body: `{ email, password }`
  - Validate user, check `status == active`, verify password via bcrypt.
  - Returns: `{ access_token, token_type: 'bearer', user: { id, email, role, tenant?, caps? } }`
  - JWT claims:
    - `sub`: user_id
    - `role`: `super_admin|tenant_admin|staff`
    - `tenant`: tenant id or null
    - `caps`: string[] subset allowed for this user (especially for staff)
    - `exp`: short (e.g., 2h), `iat`

- POST `/v1/auth/refresh` (optional for later)
  - With refresh token; returns new access token.

- POST `/v1/auth/logout` (optional; if storing refresh tokens server-side)

- GET `/v1/auth/me` (returns user profile from token)

Password management:
- POST `/v1/users` (create user)
  - `super_admin` can create any user; `tenant_admin` can only create `staff` in their tenant.
- PATCH `/v1/users/{id}` (update)
  - `super_admin` can update any; `tenant_admin` can update users in their tenant; self can update `password` and `display_name`.
- PATCH `/v1/users/{id}/password`
- GET `/v1/users` (list/search)
  - `super_admin`: all tenants; `tenant_admin`: only their tenant users.

Validation/guards:
- New dependency: `require_role(*roles)`
- Existing `get_current_user()` will decode JWT, then hydrate a minimal user context:
  - `{ id, email, role, tenant, caps }`
- Extend `ensure_capability_enabled()` to check both tenant capabilities and user capabilities (intersection):
  - A request is allowed only if capability is enabled for tenant AND present in user’s `caps` (or user is `super_admin` or `tenant_admin` with override rules; see below RBAC).

---

### RBAC matrix (server)
- super_admin:
  - Access all tenants, all endpoints, bypass tenant/cap restrictions (still keep soft checks/hints).
- tenant_admin (with tenant T):
  - Access only endpoints with `tenant == T`.
  - Can manage tenant settings, modules, capabilities for T.
  - Can manage `users` with `tenant == T` (create staff, reset password, disable accounts).
  - Capabilities in token may be omitted (treat as full access within tenant’s enabled capabilities for admin UI), but server enforcement for sensitive actions is role-based.
- staff (with tenant T):
  - Access only endpoints with `tenant == T`.
  - Must have required capability in `caps` AND tenant must have capability enabled. Example:
    - Access `/store/orders` only if `store.orders` in user.caps and in `tenant.capabilities`.

Implementation detail:
- For staff requests, change `ensure_capability_enabled(capId)` to:
  - Check tenant has cap → then if role == staff, confirm `capId ∈ user.caps`; if role == tenant_admin or super_admin, allow.

---

### Backend changes (FastAPI)
1) New `users` storage in `app/services/storage_mongo.py`:
   - `create_user(email, password, role, tenant?, caps?)`
   - `get_user_by_email(email)`
   - `get_user_by_id(id)`
   - `list_users(tenant?, role?, search?)`
   - `update_user(id, patch)` (role/caps/status/password_hash)
   - Use `bcrypt` for hashing (add `bcrypt` to requirements if not present).

2) Auth router changes (`app/routers/auth.py`):
   - Add `/login`, `/me` endpoints.
   - Issue JWT using `JWT_SECRET`. Configure `JWT_EXPIRES_IN`.

3) Deps and guards (`app/routers/deps.py`):
   - `get_current_user()` should only trust token and not DB-hit on each request (optional), but may verify `status` on critical ops.
   - Add `require_role(*roles)` dependency.
   - Update `ensure_capability_enabled()` to also check user-level caps for staff.

4) Gate existing routers:
   - Already using `get_current_user` and tenant active/module/cap checks.
   - Add `require_role('super_admin')` for `/v1/modules` and tenant modules/capabilities updates (already enforced by role check in handler; convert to a dedicated dependency for consistency).
   - For Store/Salon data actions, keep current tenant and capability checks; new user-level caps will automatically restrict staff.

5) Startup seeding:
   - In `app/main.py` startup, if no `super_admin` exists and env `BOOT_SUPER_ADMIN_EMAIL` & `BOOT_SUPER_ADMIN_PASSWORD` defined, create the account.

---

### Admin UI changes (Vite + React)
1) Login page
   - Current UI stores token in `localStorage('auth_token')`. Replace the ad-hoc approach with a proper login form.
   - Add `src/api/auth.ts`:
     - `login(email, password) => { access_token, user }`
     - `me()` to fetch user profile.
   - Page updates:
     - `Login.tsx`: email + password; on success, save token, save user profile in a `userStore`.

2) Role awareness
   - Update `tokenStore` or add `userStore` to keep `{ role, tenant?, caps? }` alongside the token.
   - AppShell/nav visibility rules:
     - super_admin: see Tenants, Modules for any tenant (as now), and a new Users/Admins page at global or per-tenant scope.
     - tenant_admin: see their tenant’s Settings + Modules + Users; no cross-tenant.
     - staff: see only items where `requiredCapability ∈ user.caps` AND tenant has that capability.
   - Route guard `<RequireRole roles={...}/>` and refine `<RequireCapability id="..."/>` to also consult `user.caps`.

3) Users management UI
   - For super_admin (global): page to list/create users for any tenant; mark tenant required for tenant_admin/staff; set caps for staff.
   - For tenant_admin: page to list/create staff for their tenant; set caps (checkboxes) constrained to tenant’s enabled capabilities.
   - Simple forms: email, display name, role, tenant (dropdown), caps (checkboxes fed from `/v1/modules` registry; filtered by tenant’s enabled module/caps).

4) Staff experience
   - On login, staff sees only allowed pages. For store staff with only `store.orders`, they’ll see Store → Orders but not Carts, etc., depending on how granular we define.

---

### Capability mapping (UI and API)
- Maintain the existing `registry` (`app/modules/registry.py`); Admin UI already reads `/v1/modules`.
- For staff cap assignment, present all capabilities from the registry; disable those whose parent module isn’t enabled for the tenant.
- On every page/route, continue to declare a `requiredCapability` so the guard logic can enforce both tenant and user caps.

---

### Migration and compatibility
- Keep existing JWT-only dev flow operational temporarily (feature flag: `AUTH_MODE=legacy|db`):
  - `legacy`: accept any signed token; existing behavior.
  - `db`: require login via `/auth/login` and enforce roles/caps from `users`.
- Provide a CLI or script to create the initial super_admin if envs aren’t set.

---

### Security details
- Password hashing: `bcrypt` with a strong work factor (e.g., 12).
- JWT: HS256 with `JWT_SECRET`; consider RS256 later.
- Token expiration: 2 hours; refresh tokens can be added later if needed.
- Account status: If `status == disabled`, login denied.
- Brute-force protection: (later) rate-limit by IP/email.

---

### Step-by-step implementation plan
1) Backend groundwork
   - Add `users` model/storage with bcrypt and indexing.
   - Implement `/v1/auth/login` and `/v1/auth/me`.
   - Seed super_admin on startup if missing (env-driven).

2) Roles/guards
   - Add `require_role()` and update modules endpoints to use it explicitly.
   - Enhance `ensure_capability_enabled()` to enforce user-level caps for staff.

3) Wire endpoints to RBAC
   - Keep current tenant/module checks; add the user-cap check automatically for staff.
   - Verify Store/Salon/Reports continue to function; add missing guards if needed.

4) Admin UI login
   - Build login form; integrate `/auth/login`.
   - Store `{ token, role, tenant?, caps? }` in memory/localStorage.

5) Admin UI visibility/guards
   - Centralize route requirements (capability or role) and read from `userStore` + tenant settings.
   - Update nav rendering accordingly.

6) Users management pages
   - Super Admin: cross-tenant users admin.
   - Tenant Admin: users admin scoped to their tenant.

7) QA
   - Matrix tests for each role across tenants/modules/caps; verify 403s on server when access is blocked.

---

### Acceptance criteria
- All logins stored in `users` collection; super_admin seeded in DB.
- Login via email/password returns JWT; UI uses it for session.
- Super Admin can assign modules/capabilities per tenant, and manage users for any tenant.
- Tenant Admin can manage only their tenant and its users.
- Staff can log in and only see/use features within their assigned capabilities and tenant’s enabled capabilities.
- API enforces role/capability and tenant scope; UI reflects it and hides disallowed routes.

---

### Env/config to set
- `JWT_SECRET` (required)
- `JWT_EXPIRES_IN` (e.g., `7200` seconds)
- `BOOT_SUPER_ADMIN_EMAIL`, `BOOT_SUPER_ADMIN_PASSWORD` (optional bootstrap)
- (Optional) `AUTH_MODE=db` to switch on DB-backed auth once ready.

If you confirm this plan, I can implement it in small milestones: backend users+login, guards, then Admin UI login and users management, followed by staff capability enforcement and QA.