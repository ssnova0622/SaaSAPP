### Thanks for the Tenant Admin record
The user you shared is a Tenant Admin for tenant `ss-salon`, and their `caps` array is empty:
```
role: tenant_admin
tenant: ss-salon
caps: []
```
That is fine for Option B — Tenant Admin does not need per‑user caps. They should get access as soon as the tenant enables the corresponding capability.

The remaining question is: does tenant `ss-salon` actually have the capabilities enabled, and is the UI/requests using the correct tenant context? Let’s verify quickly.

---

### Quick 3‑step verification
1) Check the tenant’s enabled capabilities (as Super Admin)
- Call:
  ```
  GET /v1/tenants/ss-salon
  ```
- Please paste the `capabilities` array from the response. It must include (for example) `store.catalog` if you expect Catalog features.

2) Check the Tenant Admin’s claims (as the Tenant Admin)
- Log in as `ss-salon@example.com` and call:
  ```
  GET /v1/auth/me
  ```
- Please paste `role`, `tenant`, `caps`.
  - Expect: `role = tenant_admin`, `tenant = ss-salon`, `caps = []` (OK for Option B).

3) Hit one protected endpoint as the Tenant Admin (pick one feature you enabled)
- Example for Catalog list:
  ```
  GET /v1/tenants/ss-salon/catalog/products
  ```
- If it returns 403, copy the exact `detail` message. It will tell us whether the tenant capability is missing (`Capability 'store.catalog' is not enabled for this tenant`) or if there’s a scope/other issue.

With these three outputs, I can pinpoint the precise blocker immediately.

---

### Common causes and fixes (based on your symptoms)
- Cause A: Tenant capabilities not actually saved for `ss-salon`.
  - Fix: As Super Admin, go to Settings → Capabilities → enable the needed capabilities for `ss-salon` → Save. Confirm with `GET /v1/tenants/ss-salon` that `capabilities` contains them.

- Cause B: UI still using a stale selected tenant for non‑super users (from a previous Super Admin session), so it fetches the wrong tenant settings.
  - Quick test: In browser console (while logged in as `ss-salon@example.com`):
    ```
    localStorage.getItem('selected_tenant')
    ```
    - If it’s not `ss-salon`, set it and refresh:
    ```
    localStorage.setItem('selected_tenant','ss-salon'); location.reload();
    ```
  - Note: I already updated `RequireCapability.tsx` to use the JWT tenant for non‑super users; this should mitigate the issue in feature components. But if your navigation/menu/route guards elsewhere still rely on `selected_tenant` (or user caps for Tenant Admin), they could hide menus/pages even when back‑end allows them.

- Cause C: Extra UI guards not updated to Option B (still checking user caps for Tenant Admin)
  - Fix pattern for guards:
    - Super Admin → allow
    - Tenant Admin → visible if tenant has the capability (ignore user caps)
    - Staff → visible only if tenant has the capability AND user caps include it
  - Ensure menus/sidebars and route guards follow the same logic as `RequireCapability`.

- Cause D: Wrong tenant in the URL path
  - All feature API routes include the tenant in the path (e.g., `/v1/tenants/{tenant}/catalog/...`). For Tenant Admin, `ensure_tenant_scope` requires the `{tenant}` in the URL to match their JWT tenant `ss-salon`. Double‑check the UI is calling the correct tenant path.

---

### Fast debugging cues you can try now
- As Tenant Admin, open the browser dev console and try:
  ```
  // 1) Confirm token tenant
  fetch('/v1/auth/me').then(r=>r.json()).then(console.log)
  // 2) Confirm selected tenant (UI)
  localStorage.getItem('selected_tenant')
  // 3) Confirm tenant’s capabilities
  fetch('/v1/tenants/ss-salon').then(r=>r.json()).then(x=>console.log(x.capabilities))
  // 4) Try a protected API (e.g., Catalog)
  fetch('/v1/tenants/ss-salon/catalog/products').then(async r=>({status:r.status, detail: await r.json()})).then(console.log)
  ```
- Share these outputs; they will tell us exactly which layer is blocking.

---

### If you want me to proceed with code adjustments
I can:
- Force `selected_tenant` to JWT tenant on login for non‑super users (small UI change in the login success handler/AppShell).
- Audit and update any remaining menu/route guards to match Option B.

Just confirm, and I’ll apply these minimal UI adjustments so Tenant Admins immediately see enabled features without per‑user caps.
