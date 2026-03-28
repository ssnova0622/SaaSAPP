### Root cause
Your React app uses TypeScript path aliases like `@pages/*`, `@api/*`, etc. (configured in `admin_ui/tsconfig.json`), but Vite isn’t resolving them because the `vite-tsconfig-paths` plugin isn’t enabled. That’s why imports such as `@pages/Login` and `@api/axios` fail.

### Fix (2 steps)
1) Install the Vite TS paths plugin
```bash
cd admin_ui
npm i -D vite-tsconfig-paths
```

2) Update `admin_ui/vite.config.ts` to use the plugin
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  server: {
    port: 5173,
    strictPort: true,
  },
  preview: {
    port: 5174,
    strictPort: true,
  }
})
```

Then restart the dev server:
```bash
npm run dev
```

### Verify
- The error about failing to resolve `@pages/...` and `@api/...` should disappear.
- If you now get a different error about a specific file not found, double‑check that the file exists at the path referenced by the alias. Examples based on your imports in `src/App.tsx`:
  - `@pages/Login` → `admin_ui/src/pages/Login.tsx`
  - `@pages/Dashboard` → `admin_ui/src/pages/Dashboard.tsx`
  - `@pages/Settings` → `admin_ui/src/pages/Settings.tsx`
  - `@pages/Customers/Index` → `admin_ui/src/pages/Customers/Index.tsx`
  - `@components/AppShell/AppShell` → `admin_ui/src/components/AppShell/AppShell.tsx`
  - `@api/axios` → `admin_ui/src/api/axios.ts`

If any of those files are missing, either create them or adjust the import to the correct existing path.

### Alternative (if you don’t want the plugin)
Replace alias imports with relative paths. For example:
```ts
// from
import Login from '@pages/Login'
// to
import Login from './pages/Login'
```
Do this for all `@pages/*`, `@api/*`, `@components/*`, etc. The plugin approach is cleaner and keeps imports readable.

### Quick checklist
- Node 18+ (or 20+): `node -v`
- Correct API base in `admin_ui/.env.development`:
  ```
  VITE_API_BASE=http://127.0.0.1:8100/v1
  ```
- Backend running with CORS allowing the dev origin:
  ```bash
  export CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
  uvicorn ai_scheduler.main:create_app --factory --reload --port 8100
  ```

If you still hit an error after applying the plugin and restarting, paste the new error message (terminal and/or browser console), and I’ll pinpoint the next fix.