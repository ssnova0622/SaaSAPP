### Let’s fix your Admin UI run error
I can help fastest if you paste the exact error text from your terminal and/or browser console. Meanwhile, here are the most common causes and quick fixes for this repo.

#### 1) Very likely: path alias imports not resolved by Vite
Your React app uses TypeScript path aliases (see `admin_ui/tsconfig.json`):
```json
{
  "paths": {
    "@api/*": ["src/api/*"],
    "@components/*": ["src/components/*"],
    "@hooks/*": ["src/hooks/*"],
    "@pages/*": ["src/pages/*"],
    "@utils/*": ["src/utils/*"]
  }
}
```
But `vite.config.ts` does not install/enable `vite-tsconfig-paths`. If you see errors like:
- `Failed to resolve import "@pages/Login" from "src/App.tsx"`
- `Module not found: @pages/...`

Fix:
1) Install the plugin:
   ```bash
   cd admin_ui
   npm i -D vite-tsconfig-paths
   ```
2) Update `admin_ui/vite.config.ts` to include the plugin:
   ```ts
   import { defineConfig } from 'vite'
   import react from '@vitejs/plugin-react'
   import tsconfigPaths from 'vite-tsconfig-paths'

   export default defineConfig({
     plugins: [react(), tsconfigPaths()],
     server: { port: 5173, strictPort: true },
     preview: { port: 5174, strictPort: true }
   })
   ```
3) Restart the dev server: `npm run dev`

If you prefer not to add the plugin, replace alias imports (e.g., `@pages/Login`) with relative paths (`./pages/Login`). But the plugin is the cleanest fix.

#### 2) Make sure the backend is reachable and CORS is allowed
- Backend should run on port 8100:
  ```bash
  uvicorn ai_scheduler.main:create_app --factory --reload --port 8100
  ```
- Confirm CORS allows the Vite dev origin. In the backend we read `CORS_ORIGINS` from env. Set it before starting:
  ```bash
  export CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
  ```
- Verify health: http://127.0.0.1:8100/health → `{ "status": "ok" }`

If the UI shows 401 on login:
- Ensure you’re using the dev credentials (unless you changed them):
  - Username: `admin`
  - Password: `admin123`
- Or set env before starting backend:
  ```bash
  export ADMIN_DEFAULT_USER=admin
  export ADMIN_DEFAULT_PASS=admin123
  export JWT_SECRET=dev-secret-change-me
  ```

#### 3) Check the UI API base URL
`admin_ui/.env.development` should have:
```
VITE_API_BASE=http://127.0.0.1:8100/v1
```
If you ran the backend on a different port/host, update this and restart `npm run dev`.

#### 4) Node/npm versions and a clean install
- Use Node 18+ (20+ preferred). Check:
  ```bash
  node -v
  npm -v
  ```
- If install errors occurred, try a clean install:
  ```bash
  cd admin_ui
  rm -rf node_modules package-lock.json
  npm install
  npm run dev
  ```

#### 5) Port conflict or Vite crashed
- If port 5173 is busy, you’ll see an error. You can change the dev port in `vite.config.ts` `server.port`, or run `npm run preview` (serves the built app at 5174) after `npm run build`.

#### 6) Backend side issues that affect UI
- Mongo not running → some pages that query data may error. Start Mongo:
  ```bash
  docker run --name mongo -p 27017:27017 -d mongo:6
  ```
- Missing tenants → Settings/tenant picker might be empty. Create a tenant via API or use the existing demo.

### Quick test sequence
1) Backend terminal:
   ```bash
   export CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
   export ADMIN_DEFAULT_USER=admin
   export ADMIN_DEFAULT_PASS=admin123
   uvicorn ai_scheduler.main:create_app --factory --reload --port 8100
   ```
2) Frontend terminal:
   ```bash
   cd admin_ui
   npm i -D vite-tsconfig-paths
   # update vite.config.ts as shown above
   npm install
   npm run dev
   ```
3) Open http://localhost:5173 and login.

### If it still fails
Please paste:
- The exact error message from your terminal (where `npm run dev` runs)
- Any red errors from the browser console (F12 → Console)
- A screenshot or the text of the first error line is enough

With that, I’ll pinpoint the issue and provide the exact fix (or generate a small patch if you prefer).