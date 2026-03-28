### Objective
Implement multi-user, tenant-based RBAC with activity auditing and role-driven navigation:
- Super Admin (cross-tenant) can see/manage all tenants and all pages.
- Tenant Admin can see/manage their own tenant, all staff and activities for that tenant, and most admin pages.
- Staff/Operators can log in under a tenant and have restricted navigation and permissions.
- All mutating actions are “stamped” with the acting user (who did what, when, in which tenant) and visible to Tenant Admin/Super Admin in an Activity Log.

Below is a concrete plan with the exact backend and frontend changes.

---

### Backend (FastAPI + Mongo) — RBAC and Auditing

#### 1) Users collection and login
Add a dedicated users collection (tenant-scoped users + a super admin):
- Collection: `users`
  - Super admin: `{ _id, username, password_hash, role: 'super_admin', tenant: null, active: true }`
  - Tenant admins/staff: `{ _id, username, password_hash, role: 'tenant_admin'|'staff'|'viewer', tenant: '<tenant-id>', active: true }`

Endpoints (JWT):
- `POST /v1/auth/login` (extend current):
  - Accept `{ username, password }` (and optional `tenant` for convenience); validate against `users` (or keep admin defaults for now, and add real users shortly).
  - JWT claims: `{ sub: user_id|username, role, tenant }`.
  - Return `{ access_token, role, tenant }` and set HttpOnly cookie `access_token` (already implemented) for Swagger/browser.
- `GET /v1/auth/me` (new, returns decoded claims for the UI): `{ sub, role, tenant }`.
- Optional: `POST /v1/auth/logout` (clear cookie).

User management (tenant admin or super admin):
- `GET /v1/tenants/{tenant}/users` (tenant-admin or super-admin)
- `POST /v1/tenants/{tenant}/users` (create staff)
- `PUT /v1/tenants/{tenant}/users/{user_id}` (update role/active)
- `DELETE /v1/tenants/{tenant}/users/{user_id}` (soft-delete/disable)
- Super admin only: `GET /v1/users` and cross-tenant operations

Password hashing: `bcrypt` or `passlib` — store only hashed passwords.

#### 2) RBAC dependencies
Add two dependencies in `routers/deps.py`:
- `ensure_tenant_access(tenant)` — already outlined (allow super_admin/admin, or tenant match for tenant roles).
- `ensure_role(*roles)` — verify user role ∈ allowed roles.

Usage examples:
```py
@router.post("/tenants/{tenant}/promotions", dependencies=[Depends(ensure_tenant_access), Depends(ensure_role('tenant_admin','super_admin'))])
```

Roles (suggested):
- `super_admin` — full cross-tenant access
- `tenant_admin` — full access inside their tenant (users, staff, activity log, promotions, etc.)
- `staff` — operational access (appointments, customers, follow-ups), but limited admin actions
- `viewer` — read-only (analytics, lists)

#### 3) Activity Log (auditing)
Add an `activities` collection:
- Document shape: `{ _id, tenant, user, role, action, resource_type, resource_id?, payload?, performed_at }`
- Index: `(tenant, performed_at)`

Utility to log activity (wraps writes):
- `log_activity(tenant, user, role, action, resource_type, resource_id=None, payload=None)` — called after successful mutations.

Integrate into write endpoints (examples):
- Appointments
  - Create: log `action: 'appointment.create'`, `resource_id: appointment.id`, `payload: { time, professional, customer }`
  - Cancel: `action: 'appointment.cancel'`
- Customers: `customer.upsert`, `customer.import`
- Promotions: `promotion.create`, `promotion.send`
- Follow-ups: `followup.schedule`, `followup.cancel`
- Professionals/Slots: `professional.create`, `slots.update`
- Reports: `report.generate`

New endpoints for viewing logs:
- Tenant Activity: `GET /v1/tenants/{tenant}/activities?user=&action=&from=&to=&page=&size=` — visible to `tenant_admin` and `super_admin`.
- Super Admin Activity: `GET /v1/activities?tenant=&user=&action=&from=&to=&page=&size=` — `super_admin` only.

#### 4) Stamp acting user on resources (optional)
Add optional metadata to the resource persistence:
- For appointments, promotions, reports, etc., add `created_by`/`updated_by` fields with `{user, role}` for quick provenance (in addition to the activity log).

---

### Frontend (React + Vite + MUI) — Role-aware UI

#### 1) Login flow
- `Login.tsx` — add optional Tenant field
  - Admin user: leave blank; role returned as `super_admin` or `tenant_admin`.
  - Tenant user: enter tenant id.
- Store `{token, role, tenant}` in localStorage and rely on Axios interceptor.

#### 2) Tenant picker behavior in AppShell
- Super Admin: can switch tenants (show all via `GET /v1/tenants`).
- Tenant Admin: locked to their tenant (picker shows one; read-only).
- Staff/Viewer: locked to their tenant; read-only picker.

#### 3) Role-driven navigation
- Build the nav from allowed routes per role:
  - `super_admin`: all pages + a Super Admin dashboard (optional) + cross-tenant Activity Log + Users management.
  - `tenant_admin`: all tenant pages including Users and Activity Log for the tenant.
  - `staff`: operational pages (Customers, Appointments, Follow-ups, Promotions send if allowed), but no Users or critical Settings.
  - `viewer`: read-only pages (Analytics, lists).

UI checks:
- Hide/disable nav items based on role.
- Handle 403 gracefully (show toast/message if a user lands on forbidden route via URL).

#### 4) Users management (tenant admin)
- New Admin UI page: `/users` (for tenant admin) — list, invite/create, set role, disable.
- API binds to `GET/POST/PUT/DELETE /v1/tenants/{tenant}/users`.

#### 5) Activity Log views
- New Admin UI page: `/activities` (tenant-scoped) — filters by user, action, date range.
- Super Admin page: `/super/activities` — cross-tenant view.

#### 6) Stamped actions
- In the UI, show who performed the last action where applicable (e.g., in Promotions Detail show last “sent by … at …”).

---

### Data model summary (new/updated)
- `users`: `{ username, password_hash, role, tenant, active, created_at }`
- `activities`: `{ tenant, user, role, action, resource_type, resource_id?, payload?, performed_at }`
- Existing domain collections (appointments, promotions, etc.) — optional `created_by`/`updated_by`.

---

### Security notes
- Keep issuing HttpOnly cookie for Swagger/browser. Frontend uses Bearer header; both are accepted.
- Enforce role/tenant auth in the backend (source of truth). UI is convenience only.
- Use bcrypt/passlib for passwords; add basic password policy.

---

### Rollout plan
1) Backend
   - Add `users` + seed one super admin and one tenant admin per demo tenant.
   - Extend `/auth/login` to read users; set role/tenant claims; keep admin fallback only during migration.
   - Add `ensure_tenant_access` + `ensure_role` and wire to routers.
   - Add `activities` collection and `log_activity()`; integrate into write endpoints.
   - Expose `GET /auth/me`, user CRUD endpoints, and activities endpoints.
2) Frontend
   - Update Login form to include Tenant (optional), persist `{role, tenant}`.
   - Lock tenant picker for non-admin roles; build navigation by role.
   - Add Users page and Activity Log pages.
3) Verify & harden
   - 403 behavior, error toasts, restricted nav tweaks.
   - Tests: unit tests for `ensure_tenant_access` and `ensure_role`, activity log capture on key actions.

---

### What I need from you
- Role matrix confirmation (default proposal):
  - super_admin: all routes, cross-tenant activities, all tenants in picker.
  - tenant_admin: full within tenant, including Users and Activity Log; no cross-tenant.
  - staff: customers, appointments, follow-ups, promotions (create/send?) — confirm if promotions allowed; no Users or critical settings.
  - viewer: read-only lists/analytics.
- Confirm whether promotions send is allowed for staff or only tenant_admin.
- Approve that delete/rename of professionals is tenant_admin only.

Say “confirm matrix” if the above defaults are fine, and I’ll implement the users collection, role guards, activities logging, UI role-based nav, and the Users/Activity pages next. If you want custom roles or page-level exceptions, list them and I’ll tailor the guards and nav accordingly.