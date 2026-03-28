### Goal
Admin users can access all tenants; tenant‑scoped users can access only their own tenant. Enforce this on the backend and reflect it in the Admin UI (login + tenant picker and page access).

Below is a minimal, safe design you can apply quickly, with exact code changes and UI notes.

---

### Backend changes (FastAPI)
We’ll implement tenant scoping via JWT claims and a dependency that authorizes access to per‑tenant routes.

#### 1) Extend JWT to include `role` and `tenant` (already partially done)
- Request body: add optional `tenant` to `POST /v1/auth/login` for tenant‑scoped logins (admin can omit it).
- Token claims:
  - Admin: `{ role: 'admin', tenant: null }` — can access all tenants.
  - Tenant user: `{ role: 'tenant', tenant: '<tenant-id>' }` — can only access their own tenant.

Concretely in `ai_scheduler/routers/auth.py`:
```py
# add in imports
from ai_scheduler.services.storage_mongo import Storage

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str = "admin"          # NEW: include role for UI convenience
    tenant: Optional[str] = None  # NEW: include tenant for UI convenience

# modify issuer to accept role/tenant
def _issue_jwt(username: str, role: str = "admin", tenant: Optional[str] = None) -> LoginResponse:
    secret = env.str("JWT_SECRET", "dev-secret-change-me")
    exp_minutes = env.int("JWT_EXP_MINUTES", 120)
    exp_dt = datetime.utcnow() + timedelta(minutes=exp_minutes)
    payload = {
        "sub": username,
        "role": role,
        "tenant": tenant,
        "exp": exp_dt,
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return LoginResponse(access_token=token, expires_in=exp_minutes * 60, role=role, tenant=tenant)

@router.post("/auth/login", response_model=LoginResponse)
def login(body: LoginRequest, response: Response):
    admin_user = env.str("ADMIN_DEFAULT_USER", "admin")
    admin_pass = env.str("ADMIN_DEFAULT_PASS", "admin123")
    if body.username != admin_user or body.password != admin_pass:
        # You can add a real user store here; for MVP, keep a single admin user.
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # If 'tenant' is provided, validate it and issue tenant‑scoped token
    if body.tenant:
        if not Storage.tenant_exists(body.tenant):
            raise HTTPException(status_code=404, detail="Tenant not found")
        token_resp = _issue_jwt(body.username, role="tenant", tenant=body.tenant)
    else:
        token_resp = _issue_jwt(body.username, role="admin", tenant=None)

    # Set HttpOnly cookie (session‑wise auth)
    response.set_cookie(
        key="access_token",
        value=token_resp.access_token,
        max_age=token_resp.expires_in,
        httponly=True,
        secure=env.bool("COOKIE_SECURE", False),
        samesite=env.str("COOKIE_SAMESITE", "lax").lower(),
    )
    return token_resp
```

#### 2) Return role/tenant from `get_current_user`
- File: `ai_scheduler/routers/deps.py` (you already added cookie fallback). Make sure you propagate `tenant` from the token claims:
```py
def get_current_user(authorization: Optional[str] = Header(default=None), access_token: Optional[str] = Cookie(default=None)) -> dict:
    ...
    payload = jwt.decode(...)
    return {
        "sub": payload.get("sub"),
        "role": payload.get("role", "admin"),
        "tenant": payload.get("tenant"),
    }
```

#### 3) Add an authorization helper for per‑tenant routes
- Create an authorization dependency that enforces tenant scoping on any route that has a `{tenant}` path param.
- New function in `ai_scheduler/routers/deps.py`:
```py
from fastapi import Depends

def ensure_tenant_access(tenant: str, user: dict = Depends(get_current_user)) -> dict:
    # Admins can access everything
    if user.get("role") == "admin":
        return user
    # Tenant users must match the path tenant
    if user.get("role") == "tenant" and user.get("tenant") == tenant:
        return user
    raise HTTPException(status_code=403, detail="Forbidden for this tenant")
```

#### 4) Apply `ensure_tenant_access` to tenant‑scoped routers
For any endpoint that takes `{tenant}` and should be admin/tenant restricted, add `dependencies=[Depends(ensure_tenant_access)]`.
Examples:
- Tenants settings:
```py
@router.get("/tenants/{tenant}", dependencies=[Depends(get_current_user), Depends(ensure_tenant_access)])
```
- Customers, Promotions, Appointments, Followups, Reports, Retention, Slots updates:
```py
@router.get("/tenants/{tenant}/customers", dependencies=[Depends(ensure_tenant_access)])
@router.post("/tenants/{tenant}/customers", dependencies=[Depends(ensure_tenant_access)])
...
@router.put("/tenants/{tenant}/professionals/{professional}/slots", dependencies=[Depends(ensure_tenant_access)])
```
Tip: For read‑only lists that are safe to expose (if any), you can omit. But for admin CRUD, add the dependency.

#### 5) Limit `GET /v1/tenants` for tenant users
- Admins: return all tenants (existing behavior)
- Tenant users: return only their own tenant
```py
@router.get("/tenants", dependencies=[Depends(get_current_user)])
def list_tenants(user: dict = Depends(get_current_user)) -> List[Dict]:
    if user.get("role") == "tenant" and user.get("tenant"):
        # return only the user’s tenant basic record
        doc = Storage.get_tenant_settings(user["tenant"]) or {"tenant": user["tenant"]}
        return [{
            "tenant": doc.get("tenant", user["tenant"]),
            "category": doc.get("category", "salon"),
            "owner_email": doc.get("owner_email"),
            "owner_phone": doc.get("owner_phone"),
            "tz": doc.get("tz"),
            "invoice_delivery": doc.get("invoice_delivery", "both"),
        }]
    # admin → all tenants
    return Storage.list_tenants_basic()
```

Optional (nice to have): Add `GET /v1/auth/me` that returns the decoded user (role, tenant) so the UI doesn’t need to introspect.

---

### Frontend changes (React Admin UI)
Goal: Admin can see and switch across all tenants; tenant users are restricted to their tenant only.

#### 1) Login form: allow tenant input for tenant users
- `src/pages/Login.tsx`
  - Add an optional “Tenant” field.
  - Submit `{ username, password, tenant }` to `/v1/auth/login`.
  - Store the returned `role` and `tenant` in `localStorage` (e.g., `auth_role`, `auth_tenant`) along with the token.

Example changes:
```tsx
// state
const [tenant, setTenant] = useState('')
...
// form field
<TextField label="Tenant (optional for admin)" value={tenant} onChange={e=>setTenant(e.target.value)} />
...
// on submit
const res = await api.post<LoginResponse>('/auth/login', { username, password, tenant: tenant || undefined })
localStorage.setItem('auth_role', res.data.role)
if (res.data.tenant) localStorage.setItem('auth_tenant', res.data.tenant)
```

#### 2) Tenant picker behavior in AppShell
- If `auth_role === 'tenant'`, then lock the tenant picker to `auth_tenant` and hide other tenants.
- If admin, keep current behavior (show all tenants and allow switching).

In `src/components/AppShell/AppShell.tsx`:
```tsx
const role = localStorage.getItem('auth_role')
const forcedTenant = localStorage.getItem('auth_tenant')
...
useEffect(() => {
  (async () => {
    const list = await listTenants()
    const allowed = role === 'tenant' && forcedTenant ? list.filter(t => t.tenant === forcedTenant) : list
    setTenants(allowed.map(t => t.tenant))
    const initial = forcedTenant || (tenant || allowed[0]?.tenant || null)
    if (initial && initial !== tenant) setTenant(initial)
  })()
}, [])
```
Also render the tenant `<select>` as read‑only when `role==='tenant'`.

#### 3) Page access (client‑side)
The backend now enforces authorization. On UI:
- Keep routes the same.
- All per‑tenant API calls carry the selected tenant; if the user is tenant‑scoped and tries a different tenant, the backend returns 403 and the UI can show an error.

Optional: Hide navigation items that make no sense to tenant users (e.g., the Tenants admin screen) — but since most routes are per tenant, it’s fine to leave them visible.

---

### Testing
1) Admin flow:
- Login without tenant.
- Verify `/v1/tenants` returns all tenants; the tenant picker shows all; all per‑tenant endpoints work.

2) Tenant flow:
- Login with a valid `tenant`.
- Verify `/v1/tenants` returns only that tenant; picker locks to it; any attempt to call a different tenant returns 403.
- Pages work as usual for the locked tenant.

3) Swagger flow:
- Execute `POST /v1/auth/login` with a tenant in the body to set a tenant‑scoped cookie.
- Calls to `/v1/tenants/{other}` should 403; calls to `/v1/tenants/{that}` should succeed.

---

### Summary
- Added tenant scoping at JWT + dependency level.
- Admin sees all; tenant users are restricted by `{tenant}` in the path.
- UI logs in with optional tenant, locks tenant picker for tenant users, and relies on backend for enforcement.

If you’d like, I can also add:
- `POST /v1/auth/logout` to clear the cookie and local storage
- A simple `/v1/auth/me` endpoint so the UI can discover role/tenant without decoding JWT
- Per‑slot append/remove and reset helpers for Professionals

Tell me if you want me to push these code updates to the repo now, or if you prefer a PR diff preview first.