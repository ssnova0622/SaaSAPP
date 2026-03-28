### Root cause
Your UI shows multiple tenants in the picker because it always lists all tenants (`GET /v1/tenants`) and doesn’t lock the selection to the user’s tenant. For a user whose record in `users` has `tenant: 'ss-salon'`, two things must be enforced:
- Backend scope: tenant_admin/staff can only see and operate on their own tenant.
- Frontend UX: hide the Tenants page and force the tenant picker to the user’s tenant.

You’re seeing `ss-clinic` because one or both of these guards are missing in your running build.

---

### Backend — enforce tenant scope (authoritative)
Ensure tenant_admin/staff can only see their own tenant and cannot switch via API.

1) Restrict `/v1/tenants` to the caller’s scope
Update the route to return all tenants only for super_admin; for other roles return only their tenant (or 403 if none).
```python
# app/routers/tenants.py
from .deps import get_current_user

@router.get("/tenants", dependencies=[Depends(get_current_user)])
def list_tenants(user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict]:
    role = str(user.get("role") or "admin").lower()
    if role == "super_admin":
        return Storage.list_tenants_basic()
    my_tenant = (user.get("tenant") or "").strip()
    if not my_tenant:
        raise HTTPException(status_code=403, detail="Tenant scope violation")
    # Filter to just your tenant; if it doesn’t exist, return empty list
    items = [t for t in Storage.list_tenants_basic() if t.get("tenant") == my_tenant]
    return items
```

2) Add tenant scope guard to tenant settings endpoints
```python
# app/routers/tenants.py
from .deps import ensure_tenant_scope

@router.get("/tenants/{tenant}", dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope())])
# ...
@router.put("/tenants/{tenant}", dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope())])
# ... and keep the Super Admin check for modules/capabilities inside the PUT.
```

3) Apply `ensure_tenant_scope()` everywhere it’s tenant-scoped
- Customers (already added in your repo)
- Professionals/Slots, Appointments, Promotions, Followups, Reports, Retention, Store (carts/orders)
This guarantees a staff/tenant_admin with `tenant = 'ss-salon'` can’t call APIs for `ss-clinic`.

---

### Frontend — lock the picker and menu for scoped users
The UI should reflect the server truth to avoid confusion.

1) Limit tenant picker to the user’s tenant for tenant_admin/staff
- Decode the JWT in `AppShell` (you already do this in Settings to detect super_admin). If role is not `super_admin`, set the tenant list to `[token.tenant]` and hide the Tenants page from `CORE_NAV`.
- If the current `selected_tenant` in `localStorage` differs from `token.tenant`, immediately switch it to `token.tenant`.

Example patch idea:
```ts
// admin_ui/src/components/AppShell/AppShell.tsx
import { tokenStore } from '@api/axios'

function getTokenPayload(){
  try{ const t = tokenStore.get(); if(!t) return null; const p = JSON.parse(atob(t.split('.')[1])); return p }catch{return null}
}

const payload = getTokenPayload()
const role = String(payload?.role || 'admin').toLowerCase()
const myTenant = (payload?.tenant || '') as string

useEffect(()=>{
  if(role !== 'super_admin'){
    if(myTenant){ setTenants([myTenant]); if(tenant !== myTenant) setTenant(myTenant) }
  }
}, [role, myTenant])

// When rendering nav: hide Tenants for non super_admin
const CORE_NAV = [
  { label: 'Dashboard', to: '/' },
  { label: 'Settings', to: '/settings' },
  ...(role === 'super_admin' ? [{ label: 'Tenants', to: '/tenants' }] : []),
  { label: 'Customers', to: '/customers' },
  // ...
]
```

2) Guard deep links
- If a user tries to navigate to a different tenant (e.g., by URL), the picker should immediately snap back to `token.tenant`. You can enforce this in the same `useEffect` as above.

---

### Quick verification checklist
- Log in as a tenant_admin for `ss-salon`.
- Open Admin UI — Tenants menu is hidden; tenant picker shows only `ss-salon` and cannot switch.
- All pages load and operate for `ss-salon` only.
- Calling `/v1/tenants` returns only `[{ tenant: 'ss-salon', ... }]`.
- Attempting any `/v1/tenants/ss-clinic/...` API returns 403 (tenant scope violation).

---

### Optional hardening (recommended)
- On login, if the token has no `tenant` for tenant_admin/staff, block the session (server logic already enforces but UI can show a friendly message).
- For staff users, you’ve already added capability checks; keep using `ensure_capability_enabled` on server and capability-aware nav on UI.

---

### Summary
- Backend: filter `/v1/tenants` for non-super_admins; add `ensure_tenant_scope()` to tenant endpoints and other tenant-scoped routers.
- Frontend: restrict tenant picker to the user’s tenant and hide the Tenants page unless the user is super_admin.

If you want, I can push the exact patches for `list_tenants` filtering and add `ensure_tenant_scope()` to the remaining routers, plus adjust `AppShell` to hide Tenants and lock the picker. Let me know and I’ll apply them right away.