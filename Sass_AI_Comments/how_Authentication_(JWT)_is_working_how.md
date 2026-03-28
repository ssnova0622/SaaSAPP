### How JWT auth works in this project

Backend (FastAPI):
- Login endpoint: `POST /v1/auth/login`
  - File: `ai_scheduler/routers/auth.py`
  - Accepts `{username, password}` (defaults in env: `ADMIN_DEFAULT_USER=admin`, `ADMIN_DEFAULT_PASS=admin123`).
  - Issues a JWT signed with HS256 using `JWT_SECRET` (env) and `exp` from `JWT_EXP_MINUTES`.
  - Claims include:
    - `sub`: username
    - `role`: "admin" (MVP)
    - `exp`: expiration timestamp
    - `iat`: issued-at timestamp
- Protected endpoints use the dependency in `ai_scheduler/routers/deps.py`:
  - `get_current_user(authorization: str)` reads the `Authorization: Bearer <token>` header, decodes the JWT with the same `JWT_SECRET`, and rejects if missing/invalid/expired.
  - Many Admin endpoints (e.g., Customers/Promotions/Reports/Retention) include `dependencies=[Depends(get_current_user)]`.

Frontend (React Admin UI):
- `src/api/auth.ts` calls `/v1/auth/login` and stores the token in `localStorage` via `tokenStore.set()`.
- `src/api/axios.ts` installs a request interceptor that automatically adds `Authorization: Bearer <token>` to every API request once you’re logged in.

Key files to glance at:
- `ai_scheduler/routers/auth.py` — token issuance
- `ai_scheduler/routers/deps.py` — token verification on each request
- `admin_ui/src/api/axios.ts` — token storage and request header injection

---

### How to obtain a token
- Curl:
```bash
curl -s -X POST http://127.0.0.1:8100/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
# → {"access_token":"<JWT>","token_type":"bearer","expires_in":7200}
```
- React Admin UI:
  - Open http://localhost:5173
  - Login with the same credentials; the UI stores the token and attaches it automatically.

---

### How to pass the token when calling the Reports API
The Reports endpoints are JWT-protected (`Depends(get_current_user)`):
- `POST /v1/tenants/{tenant}/reports/daily/run?date=YYYY-MM-DD` — generate & (best-effort) deliver
- `GET /v1/tenants/{tenant}/reports/daily?page=&size=` — list recent reports

Include the JWT in the `Authorization` header as `Bearer <token>`.

- Curl examples:
```bash
# 1) Get token
TOKEN=$(curl -s -X POST http://127.0.0.1:8100/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | jq -r .access_token)

# 2) Run a daily report (today if date omitted)
curl -s -X POST \
  'http://127.0.0.1:8100/v1/tenants/demo-salon/reports/daily/run?date=2025-11-29' \
  -H "Authorization: Bearer $TOKEN"

# 3) List reports
curl -s 'http://127.0.0.1:8100/v1/tenants/demo-salon/reports/daily?page=1&size=25' \
  -H "Authorization: Bearer $TOKEN"
```

- JavaScript (fetch):
```js
const base = 'http://127.0.0.1:8100/v1'
const token = '<paste JWT here>'

// Run report
await fetch(`${base}/tenants/demo-salon/reports/daily/run?date=2025-11-29`, {
  method: 'POST',
  headers: { Authorization: `Bearer ${token}` }
})

// List reports
const res = await fetch(`${base}/tenants/demo-salon/reports/daily?page=1&size=25`, {
  headers: { Authorization: `Bearer ${token}` }
})
const data = await res.json()
console.log(data)
```

- Postman
  - First, `POST /v1/auth/login` and copy `access_token`.
  - For your Reports requests, set `Authorization` = `Bearer Token` and paste the token, or go to Headers and add `Authorization: Bearer <token>`.

- Swagger UI (http://127.0.0.1:8100/docs)
  - Click Authorize (top right), paste `Bearer <token>` (including the word `Bearer` + space), then call the Reports endpoints.

---

### Frontend: calling Reports API from the Admin UI
- The React Admin UI uses Axios with an interceptor:
  - When you’re logged in, it automatically sends `Authorization: Bearer <token>` on every request, including `GET /reports/daily` and `POST /reports/daily/run`.
- Relevant frontend code:
  - `src/api/axios.ts` — attaches bearer token
  - `src/api/reports.tsx` — small wrappers for list & run endpoints
  - `src/pages/Reports/Index.tsx` — the page that lists & triggers reports

You do not need to manually add headers in the UI; logging in once is sufficient.

---

### Token lifetime and env
- `JWT_EXP_MINUTES` (default 120) controls how long tokens remain valid.
- `JWT_SECRET` must be the same for issuing and verifying.
- If a token expires, the backend returns 401 and the frontend interceptor clears it, redirecting you back to `/login` on the next guarded navigation.

---

### Quick troubleshooting
- 401 Unauthorized: Ensure you sent `Authorization: Bearer <token>`, token hasn’t expired, and your backend used the same `JWT_SECRET` to issue it.
- CORS errors from browser: Make sure `CORS_ORIGINS` includes your UI origin `http://localhost:5173`.
- Swagger “Authorize” fails: Be sure you paste `Bearer <token>` (with the word `Bearer` and a space).

If you share any failing curl or console output (with endpoint and status), I’ll pinpoint the exact fix. 