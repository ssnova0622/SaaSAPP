### Let’s get the Professionals navigation working
I’ve already added the Professionals page, API client, route, and the left‑nav link. If the nav item isn’t opening the page (or you see a blank/console error), do these checks in order.

#### 1) Confirm the files and routes exist
- Page file: `admin_ui/src/pages/Professionals/Index.tsx`
- API client: `admin_ui/src/api/professionals.ts`
- Route added in `admin_ui/src/App.tsx`:
  ```tsx
  import Professionals from '@pages/Professionals/Index'
  ...
  <Route path="professionals" element={<Professionals />} />
  ```
- Left nav link added in `admin_ui/src/components/AppShell/AppShell.tsx`:
  ```ts
  const NAV_ITEMS = [
    { label: 'Dashboard', to: '/' },
    { label: 'Settings', to: '/settings' },
    { label: 'Customers', to: '/customers' },
    { label: 'Professionals', to: '/professionals' },
    ...
  ]
  ```

If any of those are missing or differ, the route won’t resolve.

#### 2) Make sure Vite resolves aliases (very common)
The UI imports use `@pages/*` and `@api/*` aliases. You must have one of these in place:
- Plugin approach (recommended) — in `admin_ui`:
  ```bash
  npm i -D vite-tsconfig-paths
  ```
  `vite.config.ts` should include:
  ```ts
  import tsconfigPaths from 'vite-tsconfig-paths'
  export default defineConfig({ plugins: [react(), tsconfigPaths()] })
  ```
- OR add manual aliases (no plugin):
  ```ts
  resolve: { alias: { '@pages': path.resolve(__dirname,'src/pages'), '@api': path.resolve(__dirname,'src/api'), ... } }
  ```
After changing, restart the dev server: `npm run dev`.

Symptoms if this part is broken:
- Console: “Failed to resolve import '@pages/Professionals/Index' ...”
- 404 under `/professionals` because the component import failed.

#### 3) Hard refresh the browser and restart Vite
Sometimes Vite’s module graph needs a restart after adding new files/routes.
- Stop the dev server
- `npm run dev`
- Hard refresh the page (Ctrl/Cmd+Shift+R)

#### 4) Check the browser console for errors
Open the console (F12 → Console) on `http://localhost:5173/professionals`.
- If you see a runtime error, paste it here and I’ll pinpoint the fix.
- If you see a 401 for `GET /v1/tenants/{tenant}/professionals`, log in on the Admin UI login page first. The Axios interceptor attaches the JWT automatically.

#### 5) Quick sanity: tenant selected
The page loads the list of professionals for the selected tenant (stored in `localStorage` as `selected_tenant`). Make sure a tenant is selected in the left drawer (the Tenant selector at the top of the nav). If you haven’t created one yet, use the Tenants API or Settings page.

#### 6) Verify the backend endpoints
Backend routes used by the page (FastAPI):
- `GET /v1/tenants/{tenant}/professionals` → names list
- `GET /v1/tenants/{tenant}/professionals/{name}/slots` → slots
- `POST /v1/tenants/{tenant}/professionals` → create (JWT/cookie required)
- `PUT /v1/tenants/{tenant}/professionals/{name}/slots` → update slots (JWT/cookie required)

If the Admin UI shows 401 on create/update, authenticate first:
- Swagger: Execute `POST /v1/auth/login` — cookie session is set automatically (I added this).
- UI: Login at `/login` — the token is added to all requests.

#### 7) Case‑sensitive paths (on Linux/macOS with case‑sensitive FS)
Ensure the folder and import casing match exactly:
- File path: `src/pages/Professionals/Index.tsx`
- Import: `import Professionals from '@pages/Professionals/Index'`
A mismatch in case will cause the route to fail build/run.

---

### If it still doesn’t work
Please paste one of the following:
- The first red error line from the browser console when you click “Professionals”
- The terminal output from `npm run dev` when you click the link
- A screenshot of the Network tab for `/professionals` (status and any failing imports)

I’ll give you a precise fix (package, route, or import) within one message.

---

### What’s coming next for full CRUD
You also asked for complete CRUD for professionals and slots. I already implemented:
- Create professional
- Read professional names and slots
- Update slots (bulk)

I will add shortly:
- Update professional (rename/price)
- Delete professional
- Optional slot helpers (reset to default, append/remove)
- UI controls (Edit/Delete buttons in the Professionals table, Reset Slots button, optional per‑slot add/remove)

If you confirm delete/rename behavior (e.g., migrate appointments on rename? block delete if appointments exist?), I’ll implement those right away.