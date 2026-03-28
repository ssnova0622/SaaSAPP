### Why you only see the Dashboard text on “Professionals”
That specific text is your Dashboard page. Seeing it when you click “Professionals” means the route `/professionals` did not match, so React Router hit your catch‑all (`*`) and redirected back to `/` (Dashboard). In other words: the “Professionals” route is not being registered (or the import failed), so React Router falls back to the index.

Below are quick checks and fixes to make the Professionals page appear.

---

### 1) Verify the route exists in `src/App.tsx`
You should have the explicit route (already added in the repo):
```tsx
import Professionals from '@pages/Professionals/Index'
...
<Route path="professionals" element={<Professionals />} />
```
Make sure it’s inside the same nested block as your other pages (under the `<Route path="/" element={<AppShell/>}>` group), like this:
```tsx
<Route
  path="/"
  element={
    <RequireAuth>
      <AppShell />
    </RequireAuth>
  }
>
  <Route index element={<Dashboard />} />
  <Route path="settings" element={<Settings />} />
  <Route path="customers" element={<Customers />} />
  <Route path="professionals" element={<Professionals />} />
  ...
</Route>
```
If the route isn’t there, add it and save.

---

### 2) Ensure the left‑nav link points to the same path
In `src/components/AppShell/AppShell.tsx`, the nav items should include:
```ts
const NAV_ITEMS = [
  { label: 'Professionals', to: '/professionals' },
]
```
This is already in the repo. If it were missing or had a typo (e.g., `/professional`), the link would navigate to a path that doesn’t match a route, triggering the redirect to Dashboard.

---

### 3) Confirm the page file exists with correct casing
On macOS/Linux (case‑sensitive), a casing mismatch prevents the module loading and the route doesn’t register.
- File must be at: `admin_ui/src/pages/Professionals/Index.tsx`
- Import must be: `import Professionals from '@pages/Professionals/Index'`

This file was created in the repo. Double‑check the capitalization of `Professionals` in both folder and import.

---

### 4) Make sure Vite resolves `@pages` alias
If Vite can’t resolve `@pages/Professionals/Index`, the component import fails and the route never registers.

Use one of these (recommended is plugin):
- Plugin approach (already added in the repo, you just need to install):
  ```bash
  cd admin_ui
  npm i -D vite-tsconfig-paths
  ```
  And `admin_ui/vite.config.ts` must include:
  ```ts
  import tsconfigPaths from 'vite-tsconfig-paths'
  export default defineConfig({
    plugins: [react(), tsconfigPaths()],
    server: { port: 5173, strictPort: true },
    preview: { port: 5174, strictPort: true },
  })
  ```
- OR manual aliases (no plugin):
  ```ts
  // vite.config.ts
  import path from 'node:path'
  export default defineConfig({
    plugins: [react()],
    resolve: {
      alias: {
        '@pages': path.resolve(__dirname, 'src/pages'),
        '@api': path.resolve(__dirname, 'src/api'),
        '@components': path.resolve(__dirname, 'src/components'),
        '@hooks': path.resolve(__dirname, 'src/hooks'),
        '@utils': path.resolve(__dirname, 'src/utils'),
      },
    },
  })
  ```
After changing config, restart the dev server.

Symptoms of alias failure:
- Dev console shows import/resolve error for `@pages/Professionals/Index`.
- Clicking “Professionals” keeps redirecting you to Dashboard because the route component didn’t load.

---

### 5) Restart Vite and hard refresh
After adding new pages/routes, Vite sometimes needs a fresh start:
- Stop the dev server
- `npm run dev`
- Hard refresh the browser (Ctrl/Cmd+Shift+R)

---

### 6) Make sure you’re logged in and a tenant is selected
The page fetches professionals for the selected tenant (`localStorage.selected_tenant`). If you aren’t logged in, some calls (create/update) will 401. But even if a fetch fails, you should still see the Professionals UI shell (not the Dashboard). Still, it’s good to log in:
- Visit http://localhost:5173/login → `admin / admin123`
- In the left drawer, pick an existing tenant (e.g., `demo-salon`) from the top dropdown
- Click “Professionals” again

---

### 7) Quick diagnostic
- Open http://localhost:5173/professionals directly.
- Open dev console (F12 → Console) and check for red errors.
- Open Network tab; reload; check if the JS module for `Professionals/Index.tsx` loaded or there’s a 404/resolve error.

Paste the first red error line and I’ll give you the exact one‑line fix.

---

### What’s already implemented on that page
- List professional names (left)
- Add new professional (dialog)
- Load slots of the selected professional
- Edit slots by entering comma‑separated `HH:MM` values and Save (bulk replace)

If you also want rename/delete professional and a “Reset slots to default” button on the page, confirm and I’ll add the extra endpoints + UI controls next (rename, delete, reset, and optional per‑slot add/remove).