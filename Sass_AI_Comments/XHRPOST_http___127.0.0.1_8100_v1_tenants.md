### Root cause
The Admin UI is calling the API at `http://127.0.0.1:8100/v1/...` from your Vite dev server (likely `http://localhost:5173`). The backend response has no `Access-Control-Allow-Origin` header, so the browser blocks it with CORS. This happens when either:
- The backend isn’t listening on 8100 (port mismatch), or
- The backend CORS config doesn’t include your Vite origin (`http://localhost:5173` / `http://127.0.0.1:5173`).

Given the 500 status, the request hit the backend but CORS didn’t allow your origin, so the header wasn’t added.

### Quick fix checklist
1) Decide the API port you’re using
- If your FastAPI is on 8000 (default): point the UI to 8000.
- If you really want 8100: run the API on 8100 or update the UI to 8100 consistently.

2) Set the Admin UI API base URL (Vite env)
- In `admin_ui/.env` add one of:
  - `VITE_API_BASE=http://127.0.0.1:8000/v1` (if API runs on 8000)
  - or `VITE_API_BASE=http://127.0.0.1:8100/v1` (if API runs on 8100)
- Restart Vite: `npm run dev` (env changes require restart)

3) Allow your Vite origin(s) in the backend CORS
- The app reads `CORS_ORIGINS` from env in `app/main.py`:
  - `origins = [o.strip() for o in env.str("CORS_ORIGINS", "*").split(",") if o.strip()]`
- Start the API with:
  - macOS/Linux (bash/zsh):
    ```bash
    export CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
    # choose your API port and run it, examples:
    uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --reload
    # or
    uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8100 --reload
    ```
  - Windows (PowerShell):
    ```powershell
    $env:CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
    uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --reload
    ```

4) Verify CORS quickly
- Preflight check (replace port with your API port):
  ```bash
  curl -i -X OPTIONS "http://127.0.0.1:8000/v1/tenants/ss-salon/appointments" \
    -H "Origin: http://localhost:5173" \
    -H "Access-Control-Request-Method: POST"
  ```
  You should see `Access-Control-Allow-Origin: http://localhost:5173` in the response.

5) Retry booking from Professionals page
- After fixing the base URL and CORS, try Book again. If there’s an API-side business rule issue, you’ll now see a proper JSON error instead of a network error.

### Common variants and how to resolve
- UI points to 8100 but API runs on 8000:
  - Update `admin_ui/.env` to 8000 or run backend on 8100. Restart both.
- Using `localhost` vs `127.0.0.1`:
  - Include both in `CORS_ORIGINS` to be safe, and make sure the UI base URL matches the actual API host/port exactly.
- Still receiving 401 after CORS fix:
  - Log in again so `auth_token` is present in localStorage; our axios interceptor adds the Authorization header.

### If booking still doesn’t work after CORS is fixed
Once the browser is allowed to call the API, typical backend responses are:
- 403 `Professional is inactive` → Toggle to Active in the Professionals list; UI disables booking when inactive.
- 400 `Slot not available` → Refresh slots; someone else booked it or it’s already occupied.
- 404 `Professional not found` → Ensure the selected name matches exactly (the UI uses exact values).

### Summary of what to change
- Backend: set `CORS_ORIGINS` to include your Vite origins and restart the API.
- Frontend: set `VITE_API_BASE` in `admin_ui/.env` to the correct API base and restart `npm run dev`.
- Then retry slot booking; if a business rule error appears, share the status code and `detail` so I can fine-tune the UI feedback.

If you tell me which port your API is actually running on, I’ll give you the exact two commands to run (one for the API with CORS, one to start Vite) so booking works immediately.