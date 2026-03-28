### We’ll fix your CORS for port 8100 step by step
Your browser shows CORS “Missing Allow Origin” on POST to `http://127.0.0.1:8100/v1/tenants/ss-salon/appointments`. This means the backend isn’t returning `Access-Control-Allow-Origin` for your Vite origin. Let’s align both sides precisely and verify.

#### 1) Set the Admin UI base URL to 8100 and restart Vite
In `admin_ui/.env`:
```bash
VITE_API_BASE=http://127.0.0.1:8100/v1
```
Restart dev server (env changes require restart):
```bash
cd /Users/rahmath.shihabudeen/PycharmProjects/SaasProject/admin_ui
npm run dev
```
Tip: If you visit Vite via `http://localhost:5173`, you can instead set `VITE_API_BASE=http://localhost:8100/v1` so hostnames match. Consistency helps.

Quick sanity check in browser console:
```js
import('/src/api/axios').then(m => console.log('axios baseURL =', m.api.defaults.baseURL))
// Should print http://127.0.0.1:8100/v1 (or http://localhost:8100/v1 if you chose localhost)
```

#### 2) Start FastAPI on 8100 with explicit CORS origins
Your `app/main.py` reads `CORS_ORIGINS` from env. Start the API and include ALL dev origins you might use:

macOS/Linux:
```bash
export CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8100 --reload
```
Windows PowerShell:
```powershell
$env:CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8100 --reload
```
Notes:
- Our CORS middleware is configured with `allow_credentials=True`, so use explicit origins (not a wildcard `*`).
- Keep `--host 127.0.0.1` to match the base URL you set in the UI.

#### 3) Verify CORS preflight from your terminal
Replace Origin if you use 127.0.0.1 in the browser:
```bash
curl -i -X OPTIONS "http://127.0.0.1:8100/v1/tenants/ss-salon/appointments" \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST"
```
Expected headers in the response:
- `Access-Control-Allow-Origin: http://localhost:5173` (or `http://127.0.0.1:5173`)
- `Access-Control-Allow-Headers: authorization,content-type,...`
If you don’t see `Access-Control-Allow-Origin`, the backend env variable didn’t take effect or the origin string doesn’t match exactly what your browser uses.

#### 4) Confirm the browser is truly calling 8100 and which Origin it sends
In DevTools → Network, click the failing POST and share these (or check yourself):
- Request URL (should be `http://127.0.0.1:8100/...` or `http://localhost:8100/...`)
- Request Headers → `Origin: ...`
- Response Headers → do you see any `Access-Control-*`?
- Status and body (if any)
This pinpoints any host mismatch — e.g., UI on `localhost` while CORS is only allowing `127.0.0.1`.

#### 5) If you prefer to avoid CORS in dev entirely (optional)
Use a Vite dev proxy so requests are same-origin:
- In `admin_ui/.env`: `VITE_API_BASE=/v1`
- In `admin_ui/vite.config.ts` add a proxy:
  ```ts
  export default defineConfig({
    plugins: [react(), tsconfigPaths()],
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/v1': { target: 'http://127.0.0.1:8100', changeOrigin: true }
      }
    },
    preview: { port: 5174, strictPort: true },
  })
  ```
This removes CORS from the equation during local development.

#### 6) After CORS passes, retry booking
- If you then get a business error, it will be a proper JSON response (not a network error):
  - 403 `Professional is inactive` → toggle Active in Professionals list.
  - 400 `Slot not available` → pick another time (stale slot).
  - 404 `Professional not found` → verify the name.

---

If it’s still failing, please paste:
- Output of the curl in step 3.
- The Network tab details (Request URL, Origin header, Response headers) for the POST.
- The console result of `m.api.defaults.baseURL` from step 1.
With those, I’ll give you the exact one-line `CORS_ORIGINS` and the precise `VITE_API_BASE` setting to make it work immediately.