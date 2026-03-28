### What I changed to make auth “session‑wise” and fix Swagger
You were passing the token correctly, but to make it simpler (and to avoid header issues inside Swagger/UI), I added cookie‑based session support on the backend:

- `POST /v1/auth/login` now sets an HttpOnly cookie `access_token` with your JWT (lifetime = `JWT_EXP_MINUTES`).
- The auth dependency now accepts either:
  - `Authorization: Bearer <token>` header, OR
  - `access_token` HttpOnly cookie (sent automatically by the browser/Swagger after you login).

Files changed (already applied):
- `ai_scheduler/routers/auth.py` — login now sets `Set-Cookie: access_token=<JWT>; HttpOnly`.
- `ai_scheduler/routers/deps.py` — `get_current_user()` reads from Authorization header first, then falls back to the `access_token` cookie.

This means you can log in once, and all subsequent requests in the same browser/Swagger session are authenticated automatically (no need to paste the header repeatedly). Tokens are still per user/session; another machine must log in separately.

---

### How to use it in Swagger (recommended)
1) In Swagger UI (http://127.0.0.1:8100/docs), open `POST /v1/auth/login`.
2) Execute with body:
   ```json
   {"username":"admin","password":"admin123"}
   ```
3) You’ll get a JSON with `access_token` and the browser will receive an HttpOnly `access_token` cookie.
4) Now call any protected endpoint (e.g., `GET /v1/tenants`). The cookie is sent automatically and you should no longer see “Missing bearer token”.

You can still use the Authorize button with `Bearer <token>`, but with the cookie in place it’s not required for Swagger.

---

### How to call with curl (header way)
```bash
# 1) Obtain a token
TOKEN=$(curl -s -X POST http://127.0.0.1:8100/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | jq -r .access_token)

# 2) Call protected endpoints using Authorization header
curl -s http://127.0.0.1:8100/v1/tenants \
  -H "Authorization: Bearer $TOKEN"
```

### How to call with curl (cookie way)
```bash
# Save the Set-Cookie header then pass the cookie back
curl -i -s -X POST http://127.0.0.1:8100/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' \
  -c cookies.txt  # store cookies

# Now call protected endpoint with the cookie
curl -s http://127.0.0.1:8100/v1/tenants -b cookies.txt
```

---

### Why you saw “Missing bearer token”
That message is raised only if the server doesn’t see either:
- An `Authorization` header starting with `Bearer `, or
- The `access_token` cookie.

If you paste `Bearer <token>` only inside a random text box, it won’t help unless it becomes an actual HTTP header on the request. With the change above, Swagger will rely on the cookie after a successful login.

---

### Admin UI (React)
- The React app already sends `Authorization: Bearer <token>` via Axios interceptor after you log in on the UI.
- The backend now accepts both header and cookie; the header path continues to work unchanged.

---

### Token lifetime and cookie settings
- `JWT_EXP_MINUTES` — token validity (default 120 minutes).
- `COOKIE_SECURE` (default false) — set `true` in HTTPS environments so cookies are marked Secure.
- `COOKIE_SAMESITE` (default `lax`) — adjust to `strict` or `none` as needed (`none` requires `COOKIE_SECURE=true`).

---

### Optional: logout endpoint
If you want, I can add `POST /v1/auth/logout` that clears the `access_token` cookie (sets it with Max‑Age=0). For now, you can clear site cookies in your browser to end the session.

---

### Quick checklist if it still fails
- Make sure you actually executed `POST /v1/auth/login` in Swagger (not just Authorize). You should see a `Set-Cookie: access_token=...` in the response headers (check Network tab).
- Confirm subsequent calls are from the same browser tab (cookies are per browser session).
- If you prefer header‑only, ensure you set `Authorization` exactly as `Authorization: Bearer <token>` (space required).

If you paste a failing request screenshot (headers + response) I’ll pinpoint the exact issue. 