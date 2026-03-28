### Let’s pinpoint the remaining CORS issue on port 8001
It’s almost certainly still a config mismatch between the Admin UI base URL and the backend CORS allow-list. We’ll verify both sides quickly and fix precisely.

#### 1) Confirm the Admin UI is actually pointing to 8001
In your browser DevTools Console, run these and paste back the outputs:
```js
// What base URL is axios using right now?
import('/src/api/axios').then(m => console.log('axios baseURL =', m.api.defaults.baseURL))

// What env did Vite pick up? (should be 8001)
console.log('VITE_API_BASE =', (import.meta as any).env?.VITE_API_BASE)
console.log('VITE_API_BASE_URL =', (import.meta as any).env?.VITE_API_BASE_URL)
```
If these aren’t `http://127.0.0.1:8001/v1`, then the UI still points to the wrong place. Fix by setting `admin_ui/.env` and restart Vite:
```bash
VITE_API_BASE=http://127.0.0.1:8001/v1
# restart dev server
npm run dev
```

Tip: If you use `http://localhost:5173` in your browser, you can also set `VITE_API_BASE=http://localhost:8001/v1` so the host matches. Consistency helps avoid CORS surprises.

#### 2) Verify backend CORS with a preflight curl
From a terminal, run (replace origin if you use 127.0.0.1 or localhost):
```bash
curl -i -X OPTIONS "http://127.0.0.1:8001/v1/tenants/ss-salon/appointments" \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST"
```
Expected headers include:
- `Access-Control-Allow-Origin: http://localhost:5173` (or `http://127.0.0.1:5173`)
- `Access-Control-Allow-Headers: ...` (should include `content-type`, `authorization`)

If you don’t see `Access-Control-Allow-Origin`, the backend CORS list isn’t including your exact origin. Start API like this (macOS/Linux):
```bash
export CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8001 --reload
```
Windows PowerShell:
```powershell
$env:CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8001 --reload
```
Note: Since the backend enables `allow_credentials=True`, you should list explicit origins (not just `*`).

#### 3) Inspect the failed request in Network tab
Please click the failed POST in the Network tab and paste:
- Request URL
- Request Headers (especially `Origin`, and if `Authorization` is present)
- Response Headers (do you see any `Access-Control-*`?)
- Status code and JSON body (if any)

This will tell us exactly which origin the browser is sending and confirm the API response.

#### 4) Quick alternative to bypass CORS in dev (optional)
If you prefer, we can use a Vite dev proxy so API calls are same-origin:
- Set `VITE_API_BASE=/v1` in `admin_ui/.env`.
- In `admin_ui/vite.config.ts`, add:
  ```ts
  export default defineConfig({
    plugins: [react(), tsconfigPaths()],
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/v1': {
          target: 'http://127.0.0.1:8001',
          changeOrigin: true,
        }
      }
    },
    preview: { port: 5174, strictPort: true },
  })
  ```
This avoids CORS entirely during local dev. Let me know if you want me to wire this in.

#### 5) After CORS passes
Retry the booking. If you then get a backend error, it will be meaningful JSON:
- 403 `Professional is inactive` → activate the pro.
- 400 `Slot not available` → refresh/pick another time.
- 404 `Professional not found` → name mismatch.

---

Please share the outputs from steps (1), (2), and the Network details from (3). With that, I’ll pinpoint the misconfiguration and provide the exact final commands/config so it works immediately.