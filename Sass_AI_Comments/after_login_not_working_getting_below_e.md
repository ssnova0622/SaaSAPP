### What’s happening and what I changed
- The 422 Unprocessable Content on `POST /v1/auth/login` means the backend didn’t get the expected shape. Your API expects `{ email, password }` (see `app/routers/auth.py`), but the UI was sending `{ username, password }`.
- The React error “Objects are not valid as a React child (found: object with keys {type, loc, msg, input})” came from trying to render FastAPI’s validation error array/object (`detail`) directly in `<Typography>`.

I’ve updated the Admin UI so that:
- The login call now sends `{ email, password }` (`admin_ui/src/api/auth.ts`).
- The Login page uses an Email field and normalizes server errors into strings (`admin_ui/src/pages/Login.tsx`).

### What you should do now
1) Restart the Admin UI dev server (so the changes take effect):
```
cd /Users/rahmath.shihabudeen/PycharmProjects/SaasProject/admin_ui
npm run dev
```

2) Ensure your backend is running and you have a Super Admin user:
- Start API (example):
```
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8100 --reload
```
- If needed, bootstrap a super admin via env (idempotent) and restart API:
```
export BOOT_SUPER_ADMIN_EMAIL="super@example.com"
export BOOT_SUPER_ADMIN_PASSWORD="Super#12345"
```
- Or insert manually as we discussed earlier.

3) Test the backend login directly (sanity check):
```
curl -s -X POST http://127.0.0.1:8100/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"super@example.com","password":"Super#12345"}'
```
Expected: `{ access_token, user: { role: "super_admin" } }`

4) In the Admin UI Login screen, use:
- Email: `super@example.com`
- Password: `Super#12345`

If credentials are wrong or the server returns a validation error, you’ll now see a clean message instead of a React runtime error.

### If it still returns 422
- Double‑check the request body in DevTools → Network → the login request. It must be:
```
{ "email": "super@example.com", "password": "Super#12345" }
```
- Confirm the base URL is correct in `admin_ui/.env` (`VITE_API_BASE=http://127.0.0.1:8100/v1`). Restart `npm run dev` after changing `.env`.
- Ensure CORS permits your Vite origin: set `CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"` before starting the API.

### Summary
- Cause: UI sent `{ username, password }` but backend expects `{ email, password }`; error rendering an object caused the React warning.
- Fix: UI now posts `{ email, password }` and stringifies errors. Restart Vite and retry.
- Next: If you still hit issues, share the exact JSON request body and the server’s `detail` JSON; I’ll pinpoint the remaining gap immediately.