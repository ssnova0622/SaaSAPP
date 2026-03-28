### Great — we’ll use the plugin approach
You chose to use the `vite-tsconfig-paths` plugin (recommended). Do these steps once, then restart your dev server.

#### 1) Install the correct plugin (plural)
```bash
cd admin_ui
npm config set registry https://registry.npmjs.org/
npm i -D vite-tsconfig-paths
```

Note: You previously tried `vite-tsconfig-path` (singular) which does not exist.

#### 2) Verify Vite config uses the plugin
Your `admin_ui/vite.config.ts` should look like this (the repo already has this form):
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  server: { port: 5173, strictPort: true },
  preview: { port: 5174, strictPort: true },
})
```

#### 3) Restart the dev server
```bash
npm run dev
```
Open http://localhost:5173 — the alias errors like `@pages/Login` should be gone.

---

### What’s already in place for the Admin UI
- Path alias plugin wired in `vite.config.ts`.
- App shell with navigation + tenant picker + logout: `src/components/AppShell/AppShell.tsx`.
- Login page: `src/pages/Login.tsx`.
- Dashboard placeholder: `src/pages/Dashboard.tsx`.
- Settings page (CRUD to `/v1/tenants/{tenant}`): `src/pages/Settings.tsx`.
- API modules:
  - Tenants: `src/api/tenants.tsx`
  - Customers: `src/api/customers.ts` (list/upsert/import)
  - Promotions: `src/api/promotions.ts` (CRUD/send/logs)
  - Appointments: `src/api/appointments.tsx` (list/create/cancel)
  - Follow-ups: `src/api/followups.ts` (list/cancel)

Backend run reminder (in another terminal):
```bash
export CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
export ADMIN_DEFAULT_USER=admin
export ADMIN_DEFAULT_PASS=admin123
uvicorn ai_scheduler.main:create_app --factory --reload --port 8100
```

---

### What I’ll finish next (CRUD pages for all nav items)
Now that the plugin choice is locked, I’ll complete the remaining pages and wire them to the backend you already have:
- Customers: table with search/pagination; add/update dialog; CSV import.
- Promotions: list/create/detail; Send Now; logs with filters; realtime WS progress.
- Appointments: list/create/cancel.
- Follow‑ups: list with status filter; cancel.
- Reports: list; manual generate for date; open link (file:// in dev or S3 presigned).
- Retention: summary tiles; list by segment; “Create promotion for this segment”.

If you hit any error after installing the plugin and restarting, paste the exact message (terminal + browser console), and I’ll address it immediately. Otherwise, I’ll proceed to finish the CRUD pages and update the routes so the entire navigation panel is fully functional.