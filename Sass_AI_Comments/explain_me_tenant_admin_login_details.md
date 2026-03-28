<UPDATE>
I will explain exactly how Tenant Admin login works in your app: how the account is created, the login API, what’s in the token, what the UI does after login, what access a Tenant Admin has by default, and common troubleshooting tips.
</UPDATE>

### Who is the Tenant Admin and how is it created
- A Tenant Admin account is automatically created when Super Admin creates a tenant via `POST /tenants`.
- The credentials come from the payload fields in `TenantCreate`:
  - `admin_email`
  - `admin_password`
- Code reference: `app/routers/tenants.py#create_tenant` creates the user with `role="tenant_admin"` and sets the `tenant` field to that new tenant.

### How the Tenant Admin logs in (API)
- Endpoint: `POST /auth/login`
- Request body:
  ```json
  { "email": "<admin_email>", "password": "<admin_password>" }
  ```
- On success you receive `LoginResponse`:
  ```json
  {
    "access_token": "<JWT>",
    "token_type": "bearer",
    "expires_in": 7200,
    "user": {
      "id": "...",
      "email": "<admin_email>",
      "role": "tenant_admin",
      "tenant": "<tenant-id>",
      "display_name": "Tenant Admin",
      "caps": []
    }
  }
  ```
- The backend also sets an `HttpOnly` cookie named `access_token` containing the JWT so subsequent requests automatically carry authentication.
- Code reference: `app/routers/auth.py#login` and `_issue_jwt` define the JWT claims: `sub`, `role`, `tenant`, and `caps`.

### How the Tenant Admin logs in (UI)
- Admin UI page: `admin_ui/src/pages/Login.tsx`.
- The UI calls `POST /auth/login` through `admin_ui/src/api/auth.ts` and, on success, navigates to the app’s home/dashboard. The HttpOnly cookie set by backend persists the session.

### What the JWT contains for Tenant Admin
- Claims:
  - `role`: `tenant_admin`
  - `tenant`: their tenant id
  - `caps`: per-user capabilities (optional; typically empty for the Tenant Admin themselves unless you assign some)
- The middleware reads these via `get_current_user` in `app/routers/deps.py` and uses them to enforce:
  - Tenant scoping (`ensure_tenant_scope()`): Tenant Admin cannot access other tenants’ routes.
  - Capability checks (`ensure_capability_enabled()`): for non‑Super users, the user must have the capability in their JWT `caps` AND the tenant must have that capability enabled.

### What a Tenant Admin can do after first login
- Immediately after tenant creation, by your intended setup, the tenant has:
  - `modules`: [] (none enabled yet)
  - `capabilities`: []
- Therefore, most feature routes guarded by `ensure_module_enabled`/`ensure_capability_enabled` will return 403 until Super Admin assigns modules/caps to the tenant.
- Tenant Admin can manage staff for their own tenant using `/users` endpoints:
  - Create staff: `POST /users` with `role: "staff"`, `tenant: "<their-tenant>"`, and a list of `caps`.
  - The system will sanitize staff `caps` to be a subset of the tenant-enabled capabilities (see `app/routers/users.py`).

### Typical login sequence for a Tenant Admin
1. Super Admin creates tenant with `admin_email` and `admin_password`.
2. Tenant Admin visits the login page (Admin UI) and enters those credentials.
3. Backend validates credentials (`Storage.verify_user_password`), issues a JWT, and sets it in an HttpOnly cookie.
4. UI redirects to the dashboard. Without modules, UI should show limited access until Super Admin enables modules/capabilities.
5. After Super Admin assigns capabilities to the tenant, Tenant Admin can create staff and grant them specific capabilities.

### Useful endpoints for the Tenant Admin
- Self info (to get own id/role/tenant):
  - `GET /auth/me` → returns `id`, `role`, `tenant`, and `caps`.
- Change password:
  - `PATCH /users/{user_id}/password` with body `{ "password": "NewSecret123" }`.
  - You can use your own `id` from `/auth/me`.
- List users in your tenant (Tenant Admin only):
  - `GET /users` → returns users scoped to your tenant.

### Troubleshooting
- Invalid credentials (401): Wrong email or password for the Tenant Admin account.
- Tenant scope violation (403): Trying to access `/tenants/{other-tenant}` as Tenant Admin.
- Module/capability not enabled (403): Super Admin hasn’t enabled the tenant’s modules or capabilities yet.
- Missing `caps` for staff (403): A staff member attempts an action requiring a capability that wasn’t assigned to them.

### Recap
- Tenant Admin credentials are defined at tenant creation (`admin_email`/`admin_password`).
- Login via `POST /auth/login` (UI uses the same).
- JWT includes `role=tenant_admin` and `tenant=<id>` to enforce scoping and permissions.
- Access is limited until Super Admin assigns modules/capabilities to the tenant.
- Tenant Admin can then create staff and assign per-user capabilities from the tenant’s enabled set.
