### Why you see “Missing bearer token” and how to fix it
That exact error is raised in `ai_scheduler/routers/deps.py` only when the `Authorization` header is either absent or doesn’t start with `Bearer ` (note the space). Common pitfalls:

- Wrong header name (e.g., `Authentication` or `authorizationToken` instead of `Authorization`)
- Missing the `Bearer ` prefix (or missing the space): `Bearer<token>` → WRONG
- Putting the token in the body or query instead of the header
- An intermediary (proxy/extension) stripping the `Authorization` header

Your sample shows:
```
bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9....
```
This is just the value. You must send it as an HTTP header with the correct key:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9....
```
Case of the word “Bearer” is not important in our code (we lowercase internally), but the header key must be exactly `Authorization`, and there must be a space after `Bearer`.

---

### Working examples
- Curl (tenants list):
```bash
# 1) get a fresh token
TOKEN=$(curl -s -X POST http://127.0.0.1:8100/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | jq -r .access_token)

# 2) call the protected endpoint with the header
curl -s http://127.0.0.1:8100/v1/tenants \
  -H "Authorization: Bearer $TOKEN"
```

- Postman
  - Choose the Authorization tab → Type = “Bearer Token” → paste the token only (Postman will send `Authorization: Bearer <token>` automatically).
  - Alternatively, in Headers add: `Authorization` as the key and `Bearer <token>` as the value.

- Swagger UI (http://127.0.0.1:8100/docs)
  - Click the green “Authorize” button (top right).
  - Paste `Bearer <token>` (including the word `Bearer` and a space).
  - Execute the request.

- JavaScript fetch
```js
const token = '...';
const res = await fetch('http://127.0.0.1:8100/v1/tenants', {
  headers: { Authorization: `Bearer ${token}` }
});
const data = await res.json();
console.log(data);
```

---

### Double-check your token & environment
- Expired token → you get `Token expired`, not “Missing bearer token”. If you see “Missing bearer token”, the header isn’t arriving correctly.
- Ensure you’re hitting the right host/port (`http://127.0.0.1:8100`) and not a different service stripping headers.
- If calling from the React Admin UI, login once in the UI; it saves the token and the Axios interceptor adds the header automatically.

---

### Quick diagnostic
If it still fails, please share:
- The exact command (curl) or a screenshot of your Postman headers
- The first lines of the error response
- The URL you’re calling (to verify host/port)

With that, I’ll pinpoint the cause immediately (header name/value formatting, missing space, proxy interference, etc.).