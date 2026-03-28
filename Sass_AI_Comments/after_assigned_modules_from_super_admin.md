### Why this happens
Even after the Super Admin assigns modules/capabilities to a tenant, the Tenant Admin may still “not see” or access those modules if their user token doesn’t include the required capabilities. Your backend enforces two layers:
- Tenant level: module/capability must be enabled for the tenant.
- User level: for non‑Super users (`tenant_admin` and `staff`), the user must also have that capability in their own `caps` claim (checked by `ensure_capability_enabled`).

So, if the Super Admin enables e.g. `store.catalog` for the tenant, but the Tenant Admin user doesn’t have `store.catalog` added to their `caps`, the routes guarded by `ensure_capability_enabled("store.catalog")` will still return 403 and the UI will likely hide those pages.

Code reference:
- `app/routers/deps.py` `ensure_capability_enabled` lines 88–93: requires user caps for non‑super roles.

---

### Quick fixes (choose one)
1) Assign capabilities to the Tenant Admin user
- Super Admin can update the Tenant Admin user to include the newly enabled tenant capabilities.
- Steps:
  - Find Tenant Admin’s `id`: `GET /auth/me` (when logged in as that admin) or list users as Super Admin: `GET /users?tenant=<tenant-id>&role=tenant_admin`.
  - Update caps: `PATCH /users/{user_id}` with body:
    ```json
    { "caps": ["store.orders", "store.payments", "store.catalog"] }
    ```
  - Important: caps you assign must be a subset of the tenant’s enabled `capabilities` or they’ll be sanitized out.
  - Ask the Tenant Admin to sign out and sign in again (to refresh the JWT) if the UI still shows old permissions.

2) Allow Tenant Admin to bypass per‑user cap checks (policy choice)
- If you want Tenant Admin to access any capability enabled for their tenant without assigning caps individually, you can change the policy in `ensure_capability_enabled` to skip the per‑user caps requirement for `tenant_admin` role. For example, only enforce user‑caps for `staff`.
- Trade‑off: Tenant Admin will then have access to all tenant capabilities by default.

3) UI gating only on tenant settings for Tenant Admin (frontend choice)
- If your UI hides modules based on user caps AND tenant caps, Tenant Admin won’t see modules until caps are assigned. You can make the UI show modules to Tenant Admin when the tenant enables them, even if user caps are empty, while still relying on backend checks.

---

### Troubleshooting checklist
- Verify tenant settings actually updated:
  - `GET /tenants/{tenant}` should show your selected `modules` and `capabilities` arrays.
- Verify the user’s current token claims:
  - `GET /auth/me` while logged in as Tenant Admin → check `role`, `tenant`, and `caps`. If `caps` doesn’t include expected entries, update the user caps and re‑login to refresh the token.
- Confirm the endpoint’s guards:
  - Some routes are gated by both `ensure_module_enabled("store")` AND `ensure_capability_enabled("store.catalog")` (e.g., Catalog in `app/routers/catalog.py`). You need both tenant capability and user capability.
- Refresh session after changes:
  - The backend mints the JWT at login time. After changing a user’s caps, the user must log out and log back in to get a token that contains the new caps.

---

### Recommended workflow going forward
- When Super Admin enables capabilities for a tenant, also assign the same capabilities to the Tenant Admin user (at least initially). Later you can refine the Tenant Admin’s caps as needed.
- Alternatively, adjust backend policy: allow Tenant Admin to bypass per‑user caps checks and reserve per‑user caps for staff only.

---

### Example API calls
- Super Admin enables tenant capabilities:
  ```http
  PUT /tenants/demo1
  {
    "modules": ["store"],
    "capabilities": ["store.orders", "store.payments", "store.catalog"]
  }
  ```
- Super Admin grants Tenant Admin user the same caps:
  ```http
  PATCH /users/<tenant-admin-user-id>
  {
    "caps": ["store.orders", "store.payments", "store.catalog"]
  }
  ```
- Tenant Admin re‑logs in → UI should now show/allow those modules.

---

### If the problem persists
Please tell me:
- The response from `GET /tenants/{tenant}` (just the `modules` and `capabilities` fields)
- The response from `GET /auth/me` when logged in as the Tenant Admin (`role`, `tenant`, `caps`)
- An example endpoint returning 403, and the exact error message
With that I can pinpoint the exact blocker (tenant vs user caps vs scope) and suggest a precise fix.