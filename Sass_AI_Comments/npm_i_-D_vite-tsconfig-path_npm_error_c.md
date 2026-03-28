### The error is from a typo in the package name
You installed `vite-tsconfig-path` (singular) which doesn’t exist. The correct package is `vite-tsconfig-paths` (plural).

#### Fix it
1) Install the correct plugin:
```bash
cd admin_ui
npm i -D vite-tsconfig-paths
```
If you still get a 404, you might be behind a proxy or have a custom registry. Try:
```bash
# reset to the public npm registry
npm config set registry https://registry.npmjs.org/
# then
npm i -D vite-tsconfig-paths
```
Or with yarn/pnpm:
```bash
yarn add -D vite-tsconfig-paths
# or
pnpm add -D vite-tsconfig-paths
```

2) Update `admin_ui/vite.config.ts` to enable the plugin:
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

3) Restart the dev server:
```bash
npm run dev
```

That will make Vite resolve the TS path aliases defined in `tsconfig.json` (e.g., `@pages/*`, `@api/*`).

---

### If you prefer not to add the plugin
You can still make aliases work by configuring Vite’s `resolve.alias` manually (no extra package):
```ts
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@api': path.resolve(__dirname, 'src/api'),
      '@components': path.resolve(__dirname, 'src/components'),
      '@hooks': path.resolve(__dirname, 'src/hooks'),
      '@pages': path.resolve(__dirname, 'src/pages'),
      '@utils': path.resolve(__dirname, 'src/utils'),
    },
  },
  server: { port: 5173, strictPort: true },
  preview: { port: 5174, strictPort: true },
})
```
Then restart `npm run dev`.

Or, as a last resort, replace alias imports with relative paths, e.g.:
```ts
// from
import Login from '@pages/Login'
// to
import Login from './pages/Login'
```

---

### Double‑check files actually exist
After fixing aliases, if you see a different error like “Does the file exist?”, make sure these paths exist relative to `admin_ui/src/`:
- `src/pages/Login.tsx`
- `src/pages/Dashboard.tsx`
- `src/pages/Settings.tsx`
- `src/pages/Customers/Index.tsx`
- `src/components/AppShell/AppShell.tsx`
- `src/api/axios.ts` (this one exists from your repo dump)

If any are missing, either create them or adjust the imports. Here are minimal placeholders you can drop in if needed:
```tsx
// src/pages/Login.tsx
export default function Login() { return <div style={{padding:16}}>Login page</div> }

// src/pages/Dashboard.tsx
export default function Dashboard() { return <div style={{padding:16}}>Dashboard</div> }

// src/pages/Settings.tsx
export default function Settings() { return <div style={{padding:16}}>Settings</div> }

// src/pages/Customers/Index.tsx
export default function Customers() { return <div style={{padding:16}}>Customers</div> }

// src/components/AppShell/AppShell.tsx
import { Outlet, Link } from 'react-router-dom'
export default function AppShell(){
  return (
    <div>
      <nav style={{padding:8, borderBottom:'1px solid #ddd'}}>
        <Link to="/">Dashboard</Link> | <Link to="/settings">Settings</Link> | <Link to="/customers">Customers</Link>
      </nav>
      <Outlet />
    </div>
  )
}
```

---

### Quick sanity checklist
- Backend running on 8100 and CORS allows the UI:
  ```bash
  export CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
  uvicorn ai_scheduler.main:create_app --factory --reload --port 8100
  ```
- Frontend env: `admin_ui/.env.development` contains
  ```
  VITE_API_BASE=http://127.0.0.1:8100/v1
  ```
- Node 18+ / npm up‑to‑date.

If the install still 404s after switching registry and using the correct name (`vite-tsconfig-paths`), paste the exact `npm` output and I’ll advise next steps (e.g., proxy config or using Vite’s `resolve.alias` approach).