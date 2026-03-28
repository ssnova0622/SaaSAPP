# Admin UI

React (Vite) admin SPA for the SaaS backend. Multi-tenant: Super Admin can switch tenants; Tenant Admin and Staff see their tenant only.

## Run

```bash
npm install
npm run dev
```

Set `VITE_API_BASE` (or `VITE_API_BASE_URL`) in `.env` or `.env.development` to your API base (e.g. `http://127.0.0.1:8000/v1`). Restart the dev server after changing env.

## Theme

- **Dark palette**: background `#0f172a`, cards/paper `#1e293b`, borders `#334155`, primary `#3b82f6`, text `#f1f5f9` / muted `#94a3b8`.
- **MUI**: Theme is in `src/theme.ts`; all MUI components use it via `ThemeProvider` in `main.tsx`.
- **Tailwind**: Layout, Login, Sidebar, and shared UI use the same hex values so Tailwind and MUI match. Font: DM Sans (see `index.html`).

## Build

```bash
npm run build
```

Output is in `dist/`. Preview with `npm run preview -- --port 5174`.
