### Completed both points
- Added a tenant-awareness banner in the Admin UI for non‑Super Admin users, displayed at the top of all pages inside the shell.
- The banner includes a role chip (Tenant Admin or Staff) to make the scope explicit.
- UI is locked to the user’s tenant; Tenants nav is hidden for non‑Super Admin; tenant picker is restricted to the JWT tenant.
- Backend already enforces tenant scope on `/v1/tenants` and tenant settings endpoints.

Files updated:
- `admin_ui/src/components/AppShell/AppShell.tsx` — banner + role chip; lock logic retained.
- `app/routers/tenants.py` — list/filter tenants by role; scope checks on GET/PUT settings.

### How to verify
1) Log in as a tenant_admin or staff.
2) Confirm:
   - Info banner: “You are managing tenant <tenant>. Access is limited to this tenant.”
   - Role chip shows Tenant Admin or Staff.
   - Tenants menu is hidden; picker only shows the JWT tenant.
3) API checks:
   - `GET /v1/tenants` returns only your tenant.
   - `GET /v1/tenants/<other>` returns 403.

### Next steps (ready to proceed)
- If you want further UX polish, I can add a quick “switch tenant” overlay for Super Admins only.
- Otherwise, tell me the next priority (e.g., Store catalog/inventory, Reports enhancements, or Users management UI), and I’ll proceed immediately.