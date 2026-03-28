### Diagnosis and quick fix steps
Your console shows only a 404 for `favicon.ico` and no import errors. When you click “Professionals” but still see the Dashboard text, it means the `/professionals` route is not matching (so Router falls back to the index route). The two most common causes are:
1) The `Professionals` route isn’t actually registered in `App.tsx` (or file casing mismatch), or
2) The alias import didn’t resolve, so the module didn’t load and React Router silently used the index.

Let’s fix it quickly.

---

### 1) Verify and correct the route in `admin_ui/src/App.tsx`
Ensure you have all of the following (exact casing):
```tsx
import Professionals from '@pages/Professionals/Index'

// inside the nested routes under "/" (same level as settings/customers)
<Route path="professionals" element={<Professionals />} />
```
The nested block should look like this:
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
  <Route path="promotions" element={<PromotionsIndex />} />
  <Route path="promotions/new" element={<PromotionNew />} />
  <Route path="promotions/:id" element={<PromotionDetail />} />
  <Route path="appointments" element={<Appointments />} />
  <Route path="followups" element={<Followups />} />
  <Route path="reports" element={<Reports />} />
  <Route path="retention" element={<Retention />} />
</Route>
```

And your left nav in `src/components/AppShell/AppShell.tsx` must include:
```ts
{ label: 'Professionals', to: '/professionals' }
```

Also check the file path and casing exactly match:
- File: `admin_ui/src/pages/Professionals/Index.tsx`
- Import: `import Professionals from '@pages/Professionals/Index'`

---

### 2) Confirm alias resolution is active (vite‑tsconfig‑paths or manual aliases)
If the alias isn’t actually active, the route won’t register. Run:
```bash
cd admin_ui
npm i -D vite-tsconfig-paths
```
`admin_ui/vite.config.ts` must include:
```ts
import tsconfigPaths from 'vite-tsconfig-paths'
export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  server: { port: 5173, strictPort: true },
  preview: { port: 5174, strictPort: true },
})
```
Restart dev server: `npm run dev` and hard refresh (Ctrl/Cmd+Shift+R).

If you prefer no plugin, add manual aliases instead:
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
Then restart.

---

### 3) Make sure you’re logged in and a tenant is selected
- Visit http://localhost:5173/login → login `admin / admin123`
- In the left drawer, select a tenant (e.g., `demo-salon`) from the tenant dropdown.
- Click “Professionals”. Even if the fetch fails, you should still see the Professionals UI shell; the Dashboard text would only appear if route matching failed.

---

### 4) Optional: Fix the favicon 404 (cosmetic)
Create `admin_ui/public/favicon.ico` (any small icon) so the 404 disappears.

---

### If it still shows the Dashboard
Please paste the very first red error line from the browser console and the code snippet of the top of your `src/App.tsx` (imports + the nested routes block). With that, I’ll provide the exact one‑line change needed.

I can also switch your imports temporarily to relative paths to bypass alias issues:
```tsx
// In App.tsx
import Professionals from './pages/Professionals/Index'
```
If that works, the problem is strictly alias configuration; we’ll keep the plugin/manual alias thereafter to restore `@pages/*` style imports.