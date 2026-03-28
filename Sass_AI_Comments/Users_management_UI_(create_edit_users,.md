### Users management UI implemented (create/edit users, set staff capabilities)
I’ve completed the Users management UI and wired it into navigation with proper role‑based visibility. Super Admin can manage users across all tenants; Tenant Admin can manage staff in their own tenant; Staff cannot access the Users page.

### What’s included
- New API client: `admin_ui/src/api/users.tsx`
  - `listUsers(params)` — list/search users (server‑side scope enforced)
  - `createUser(payload)` — create a user (Super Admin: any; Tenant Admin: staff for own tenant)
  - `getUser(id)`, `updateUser(id, patch)`, `setPassword(id, password)`
- New page: `admin_ui/src/pages/Users/Index.tsx`
  - List: email, role, tenant, name, status, Edit action
  - Filters: by tenant (Super Admin only), search text, role
  - Create/Edit dialog:
    - Email, Role, Display name, Tenant (only for Super Admin and only for non‑super_admin users), Status
    - Password (on create) and reset password (on edit)
    - Staff capabilities picker, filtered to the tenant’s enabled capabilities
- Routing & navigation
  - Route added: `/users`
  - AppShell navigation shows “Users” for Super Admin and Tenant Admin; hidden for Staff
  - Existing tenant lock and information banner retained (with role chip)

### How to use
1) Restart Admin UI (to pick up the new pages):
```
cd admin_ui
npm run dev
```
2) Log in:
- As Super Admin → you’ll see “Users” in the sidebar and Tenant filter at the top of Users page
- As Tenant Admin → you’ll see “Users” (scoped to your tenant; no tenant dropdown)
- As Staff → no “Users” menu entry

3) Create a user
- Click “New User” → fill fields
- Super Admin:
  - Can choose role `super_admin | tenant_admin | staff`
  - For `tenant_admin` or `staff`, pick the tenant
- Tenant Admin:
  - Can create only `staff` for their own tenant
- For Staff, pick capabilities (only those enabled for the tenant are selectable)

4) Edit a user
- Click “Edit” → adjust display name, status, role/tenant (Super Admin only), capabilities (staff), and optional new password

### Server/authorization alignment (already enforced)
- Tenant scoping and capability checks are enforced on the backend; the UI reflects those rules:
  - Tenant Admin can only manage staff in their tenant
  - Staff cannot manage users
  - Super Admin can manage any user in any tenant

### Verify quickly
- Super Admin:
  - Create a `tenant_admin` and `staff` for a tenant; edit/display name; reset password
  - Switch tenants in the Users page and ensure listings update
- Tenant Admin:
  - Only tenant staff are listed; create/edit staff; staff capabilities limited to tenant‑enabled set
- Staff:
  - No access to Users page

### Notes & polish
- Basic validations are in place (e.g., password fields). If you want, I can add toasts/success banners and stronger client‑side validation (e.g., email format).
- If you’d like a dedicated “User Detail” view or bulk operations (disable multiple users, role changes), I can add those next.

### Next options
- Store Catalog/Inventory (products, categories, stock) UI + API
- Reports enhancements (sales summaries, date ranges, exports)
- Capability guard components on routes (deep link blocks) for even clearer UX

Tell me which one you want to proceed with, or if you’d like refinements on Users (toasts, validations, bulk ops).