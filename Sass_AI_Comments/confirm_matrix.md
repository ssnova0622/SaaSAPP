### RBAC matrix confirmed — implementation plan and changes
Thanks for confirming the matrix. I’ll implement tenant‑based RBAC and activity auditing with the following roles and permissions:

- super_admin
  - Scope: all tenants
  - Access: all pages (Users, Activities, Settings, Customers, Appointments, Follow‑ups, Promotions, Reports, Retention, Professionals, etc.)
- tenant_admin (within their tenant only)
  - Access: all tenant pages including Users (staff management) and Activity Log
- staff (within their tenant only)
  - Access: operational pages — Customers, Appointments, Follow‑ups, Professionals slots
  - No access: Users management, Activity Log, critical Settings, Promotions send
- viewer (within their tenant only)
  - Access: read‑only (Analytics/Reports/Lists) — no writes
- Promotions policy (per your default matrix): send allowed for tenant_admin; staff cannot send

Below is exactly what I’ll deliver.

---

### Backend (FastAPI + Mongo)

#### 1) Users model and endpoints
- Collection `users`:
  - `{ _id, username, password_hash, role: 'super_admin'|'tenant_admin'|'staff'|'viewer', tenant: null|'<tenant-id>', active: true, created_at }`
- Seed users (dev):
  - super_admin: `admin / admin123` (tenant=null)
  - tenant_admin for demo tenants (e.g., demo‑salon‑admin / pass)
- Endpoints (JWT‑protected where applicable):
  - `POST /v1/auth/login` → issues JWT with `{ role, tenant }` (and sets HttpOnly cookie)
  - `GET /v1/auth/me` → returns `{ sub, role, tenant }` (new)
  - `POST /v1/auth/logout` → clears cookie (optional, I’ll include)
  - `GET /v1/tenants/{tenant}/users` → tenant_admin, super_admin
  - `POST /v1/tenants/{tenant}/users` → create staff/viewer or tenant_admin
  - `PUT /v1/tenants/{tenant}/users/{user_id}` → update role/active
  - `DELETE /v1/tenants/{tenant}/users/{user_id}` → disable user
  - `GET /v1/users` (super_admin) → cross‑tenant view (optional)

Implementation details:
- Hash passwords with bcrypt (`passlib` convenient) — no plaintext storage
- Unique index on `(tenant, username)` or global username uniqueness depending on your preference (I’ll make it global for simplicity)

#### 2) RBAC dependencies
- `ensure_tenant_access(tenant)` — allows super_admin, or tenant‑matched user
- `ensure_role(*roles)` — ensures user role is in allowed set
- Apply guards to routers:
  - Users CRUD, Activities, Promotions send, Settings, Reports run → `tenant_admin` or `super_admin`
  - Operations (appointments/customers/followups/slots update) → `staff|tenant_admin|super_admin`
  - Read‑only (lists/analytics) → include `viewer`
- `GET /v1/tenants` behavior:
  - super_admin → all tenants
  - tenant roles → only their tenant

#### 3) Activity Log (auditing)
- Collection `activities` with indexes `(tenant, performed_at)`
- Utility `log_activity(tenant, user, role, action, resource_type, resource_id?, payload?, performed_at)`
- Stamp activities on mutations (appointments create/cancel, customer upsert/import, promotions create/send, followups schedule/cancel, professionals create/slots update, report generate)
- Endpoints:
  - `GET /v1/tenants/{tenant}/activities?user=&action=&from=&to=&page=&size=` (tenant_admin, super_admin)
  - `GET /v1/activities?tenant=&user=&action=&from=&to=&page=&size=` (super_admin)

Optional resource stamping: add `created_by/updated_by` to domain docs (appointments, promotions) for quick provenance in addition to the activity feed (I’ll add to promotions/appointments minimally).

---

### Frontend (React + Vite + MUI)

#### 1) Login page
- Add optional “Tenant” input; submit `{ username, password, tenant? }`
- Store `{ role, tenant }` from login response alongside token

#### 2) AppShell (tenant selector + nav)
- Read `auth_role` and `auth_tenant` from storage
- If `role==='super_admin'`: list all tenants and allow switching
- Else: lock picker to `auth_tenant` and only show that tenant

#### 3) Role‑driven navigation and guards
- Build navigation from role capabilities:
  - super_admin: all
  - tenant_admin: all tenant pages including Users/Activities
  - staff: operational (Customers, Appointments, Follow‑ups, Professionals); hide Users/Activities/critical Settings; Promotions listed but no “Send” action
  - viewer: read‑only nav (e.g., Dashboard/Analytics/Reports)
- Handle 403s with error notice and redirect to a safe page

#### 4) New pages
- Users: list/create/update/disable tenant users (tenant_admin)
- Activity Log: list with filters (tenant_admin); super_admin cross‑tenant view optional now/next

---

### Testing – what you’ll see
- Super Admin: login without tenant → can see all tenants; Users & Activities pages visible; all actions allowed
- Tenant Admin: login with tenant (e.g., demo‑salon) → picker locked to demo‑salon; Users & Activities visible; no cross‑tenant data
- Staff: login with tenant → only operational pages visible; trying to open Users/Activities/Settings returns 403
- Viewer: login with tenant → read‑only pages; attempts to mutate return 403

---

### Timeline (incremental, quick)
1) Backend: users collection + login from DB + RBAC deps + tenants filter (1–2 days)
2) Backend: activities logging + list endpoints + stamping (1 day)
3) Frontend: Login tenant field + role/tenant picker lock + role nav (1 day)
4) Frontend: Users + Activities pages (1–2 days)
5) Polish/QA: 403 UX, toasts, docs (0.5–1 day)

---

### Deployment and safety
- Feature is backwards compatible: until you switch to DB users fully, the existing admin defaults keep working; once users are seeded, `POST /auth/login` will authenticate against the DB users and set correct claims
- All enforcement is server‑side; UI is convenience only

---

If you want me to start with the backend users+RBAC now and then wire the UI, I’ll proceed and share quick seeds plus curl/Swagger examples as soon as they’re ready. Let me know if any page should be additionally restricted/allowed for staff/viewers beyond the defaults above.