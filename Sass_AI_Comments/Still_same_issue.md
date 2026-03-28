### Updated Plan to Resolve: Tenant Admin still can’t see enabled modules/features (Option B)

#### What we know
- Backend is set to Option B: Tenant Admins automatically access capabilities that are enabled for their tenant. Staff must have per‑user caps. This is enforced by `ensure_capability_enabled` in `app/routers/deps.py`.
- Frontend `RequireCapability.tsx` now fetches tenant capabilities using the tenant from JWT for non‑super users and should allow Tenant Admin if the tenant has the capability.
- You still don’t see features after enabling them for the tenant.

Below is a focused plan to locate and eliminate remaining blockers.

---

### 1) Collect minimal evidence (so we know where it fails)
Please run these and share outputs:
- As Super Admin (or via DB), confirm tenant capabilities:
  - `GET /v1/tenants/{tenant}` → paste the `capabilities` array.
- As the Tenant Admin (login as that tenant admin and use the same browser session):
  - `GET /v1/auth/me` → paste `role`, `tenant`, and `caps`.
  - Call one protected API for a feature you expect to see (example for Catalog):
    - `GET /v1/tenants/{tenant}/catalog/products` → paste status and `detail` on error.
- In the browser console (while logged in as the Tenant Admin):
  - `localStorage.getItem('selected_tenant')`
  - Confirm it equals the `tenant` claim from `/auth/me`.

This quickly separates: tenant capability missing vs. UI gating vs. stale tenant selection vs. backend check.

---

### 2) Verify frontend gating beyond RequireCapability
- Search the Admin UI for other guards that might still be hiding features (menus/sidebars/routes) using user caps or the wrong tenant:
  - Check the main navigation/sidebar component(s). Ensure feature visibility for Tenant Admin is based on tenant capability only (not user caps) and uses the token tenant.
  - Any remaining uses of `selected_tenant` for non‑super users should be replaced with token tenant.
- Action: Update those guards to follow Option B rules:
  - Super Admin → always allowed (or by design).
  - Tenant Admin → visible if tenant has the capability (ignore user caps).
  - Staff → visible only if tenant has the capability AND user caps include it.

Notes on where to look:
- Components that render menus (e.g., `AppShell`, `Sidebar`, any feature-level route wrappers) often re-check caps.
- Wrap feature pages with `RequireCapability` consistently; remove duplicate/stricter checks that don’t align with Option B.

---

### 3) Force correct tenant context for non‑super users (UI)
- After successful login on the client, if role != `super_admin`, set `localStorage.selected_tenant = token.tenant`.
- In `AppShell` or a top-level effect, if role != `super_admin`, coerce the selected tenant to the token tenant (if they differ) to avoid stale values from previous sessions.
- This prevents fetching the wrong tenant’s settings anywhere else in the UI.

---

### 4) Reconfirm backend paths
- `ensure_module_enabled` is now a no‑op; verify no server route still relies on actual module toggles.
- `ensure_capability_enabled(<cap>)` remains the single gate:
  - Tenant must have `<cap>` in its `capabilities`.
  - If `role == 'staff'`: user token must also include `<cap>`.
  - If `role == 'tenant_admin'`: per‑user cap bypass (allowed when tenant has it).

If an endpoint still returns 403 for Tenant Admin while the tenant has the capability, capture the exact `detail` string — it will tell us which check failed.

---

### 5) Strengthen RequireCapability (optional but helpful)
- Ensure the effect depends on `cap` as well as `selectedTenant`/`tokenTenant` so it refetches when the required capability prop changes.
- Add dev-only console logs when access is denied for quick diagnostics:
  - `role`, `tokenTenant`, `targetTenant`, `hasTenantCap`, `userCaps.includes(cap)`.

---

### 6) Retest end-to-end
- Flow A (Tenant Admin):
  1) Super Admin: enable capabilities for tenant; `PUT /v1/tenants/{tenant}` with `{ capabilities: [...] }`.
  2) Tenant Admin logs in; verify menus/pages for those capabilities are visible; protected APIs return 200.
- Flow B (Staff):
  1) Tenant Admin creates staff and grants subset caps.
  2) Staff sees only their granted features; protected APIs 403 when cap missing in user token or tenant.

---

### 7) Share the three concrete items if still blocked
Please paste:
- `GET /v1/tenants/{tenant}` capabilities array
- `GET /v1/auth/me` as Tenant Admin (role, tenant, caps)
- One failing protected API call (status + exact `detail`)
With these, I can point to the exact failing layer and provide the precise 1–2 line change.

---

### Why this plan will resolve it
- It validates the tenant’s capability list, the tenant context used by the UI, and the exact backend guard result. The remaining issues at this stage are typically stale selected tenant, extra UI guards not updated to Option B, or a mismatch in capability IDs. These steps isolate and fix each of those.
