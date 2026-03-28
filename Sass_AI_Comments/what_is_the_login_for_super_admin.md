### Short answer
There isn’t a built‑in username/password “super admin” account in this project. Super admin is determined purely by the JWT token’s `role` claim. If the token has `role: "super_admin"`, you’re a super admin. Otherwise you’re a regular admin.

### How super admin is recognized in code
- Backend: `get_current_user()` decodes your JWT and reads `role` (defaults to `admin` if missing).
  - File: `app/routers/deps.py`
  - Secret: `JWT_SECRET` (defaults to `dev-secret-change-me` if not set in env)
- Super‑admin‑only checks use `ensure_super_admin()` and routes like `GET /v1/modules` or updating tenant `modules`/`capabilities` verify `role === 'super_admin'` in your token.

### How to get a Super Admin token (dev)
You can mint a JWT yourself using the server secret. The payload just needs a `sub` and `role: "super_admin"` (optionally `exp`).

Option A — Python one‑liner (run in a shell where `JWT_SECRET` matches the API):
```bash
python - <<'PY'
import jwt, time, os
secret = os.environ.get('JWT_SECRET','dev-secret-change-me')
payload = {
  'sub': 'you@example.com',
  'role': 'super_admin',
  'iat': int(time.time()),
  'exp': int(time.time()) + 3600*24*7  # 7 days
}
print(jwt.encode(payload, secret, algorithm='HS256'))
PY
```

Option B — Node.js snippet:
```bash
node -e "const jwt=require('jsonwebtoken'); const sec=process.env.JWT_SECRET||'dev-secret-change-me'; const tok=jwt.sign({sub:'you@example.com',role:'super_admin'}, sec, {expiresIn:'7d'}); console.log(tok)"
```

Option C — jwt.io
- Go to https://jwt.io
- Right panel “VERIFY SIGNATURE”: HS256 and secret `dev-secret-change-me` (or your `JWT_SECRET`).
- Payload (example):
```json
{
  "sub": "you@example.com",
  "role": "super_admin",
  "exp": 1893456000
}
```
- Copy the resulting token.

### Use the token
- API (curl example):
```bash
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8100/v1/modules
```
- Admin UI (Vite app):
  - If there’s a login screen that accepts a token, use it; otherwise you can set it directly:
  - In the browser console (on your admin UI tab):
    ```js
    localStorage.setItem('auth_token', '<PASTE_YOUR_JWT>');
    location.reload();
    ```
  - The UI reads the token from `localStorage` (via `tokenStore`) and will show super‑admin only sections (e.g., Settings → Modules) when `role` is `super_admin`.

### Production note
For production, you’ll likely want a real auth flow that issues tokens with roles from a users table/IdP. Until then, for dev/testing, generating a JWT with `role: "super_admin"` and your `JWT_SECRET` is sufficient.

### Troubleshooting
- 401 Invalid token: ensure the token was signed with the same `JWT_SECRET` the API is running with.
- 403 Super Admin required: your token’s payload probably lacks `role: "super_admin"` or you’re calling a super‑admin endpoint with a regular admin token.
- Token not picked up by UI: make sure it’s stored under `localStorage` key `auth_token`, then hard‑refresh the page.