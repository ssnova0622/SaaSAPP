### Short answer
Right now, the Admin UI does not yet expose a button to re‑activate a tenant. The backend already supports it, so you can make a tenant active again via the API:

- Endpoint: `PATCH /v1/tenants/{tenant}/status`
- Body: `{ "active": true }`

I can add the Activate/Deactivate toggle to the Tenants page next, but in the meantime you can re‑enable a tenant with one of the methods below.

### How to re‑activate a tenant now

- Using curl
```
curl -X PATCH \
  "http://127.0.0.1:8000/v1/tenants/<TENANT_ID>/status" \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"active": true}'
```

- Using the browser console (from your Admin UI tab after logging in)
```
fetch(`${import.meta.env.VITE_API_BASE || import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/v1'}/tenants/<TENANT_ID>/status`, {
  method: 'PATCH',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
  },
  body: JSON.stringify({ active: true })
}).then(r => r.json()).then(console.log)
```

- Using Postman/Insomnia
  - Method: PATCH
  - URL: `http://127.0.0.1:8000/v1/tenants/<TENANT_ID>/status`
  - Headers: `Authorization: Bearer <JWT>`, `Content-Type: application/json`
  - Body (JSON): `{ "active": true }`

You can verify with:
```
curl -H "Authorization: Bearer <JWT>" http://127.0.0.1:8000/v1/tenants/<TENANT_ID>
```
Look for `"active": true` in the response.

### Why you don’t see it in the UI yet
- The backend already enforces active tenants via `ensure_tenant_active` and exposes the status toggle endpoint.
- The Tenants page (`admin_ui/src/pages/Tenants/Index.tsx`) still shows a Delete button and no Status column yet.
- The API client already has `setTenantActive(tenant, active)` defined in `admin_ui/src/api/tenants.tsx`, so wiring the toggle in the UI is straightforward.

### Proposed UI update (what I can implement next)
- Tenants page:
  - Add a Status column (Active/Inactive chip).
  - Replace the Delete button with an `Activate` or `Deactivate` button that calls `setTenantActive()`.
  - After deactivation: if the deactivated tenant is currently selected, automatically switch selection to another active tenant and notify the user.
- Tenant picker (sidebar and Settings):
  - Show only active tenants in the drop‑down.
  - If the current selection becomes inactive, auto‑switch to the first active tenant or prompt the user.

If you’d like, I can make these UI changes now so you’ll see an “Activate” button directly in the Tenants page. Would you prefer inactive tenants to be visible in the list (with an Activate action), or hidden by default with a “Show inactive” filter?