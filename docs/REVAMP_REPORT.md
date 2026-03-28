# Revamp Report: old_app & admin_ui

This document describes the revamp applied to the **old_app** (Python backend) and **admin_ui** (React admin frontend) folders to align with the new application theme and improve structure while **keeping all existing logic and use cases**.

---

## 1. Summary

| Area | Changes | Logic preserved |
|------|---------|-----------------|
| **admin_ui** | New theme (Tailwind), Layout + Sidebar matching new admin-ui, several pages migrated to Tailwind | Yes – all API calls, state, handlers unchanged |
| **old_app** | Documented structure; no behavioral changes | Yes – all behavior preserved |

---

## 2. admin_ui Revamp

### 2.1 Theme and layout (aligned with new admin-ui)

- **Tailwind CSS v4** added alongside existing stack:
  - `tailwindcss`, `@tailwindcss/vite` in `package.json`
  - `vite.config.ts`: `tailwindcss()` plugin
  - `src/index.css`: `@import "tailwindcss"` and `@theme` (slate surface, borders, primary, etc.)

- **New shell (replaces MUI AppShell):**
  - **`src/components/Layout.tsx`**  
    - Full-height layout: sidebar + main content.  
    - `bg-slate-900` for main, `p-6` for content, offline banner, super-admin tenant selection warning.  
    - Renders `<Outlet />` for child routes.

  - **`src/components/Sidebar.tsx`**  
    - Fixed sidebar: `w-64`, `bg-slate-800`, `border-slate-700`.  
    - Nav built from `src/config/nav.ts` (CORE_NAV, SALON_NAV, STORE_NAV, AI_NAV, WHATSAPP_BOT_NAV).  
    - Visibility still driven by **capabilities and modules** (same logic as previous AppShell):  
      - JWT role (super_admin / tenant_admin / staff), tenant settings (modules, capabilities), user caps.  
    - Tenant selector (super admin) / tenant badge (non–super admin).  
    - Sign out clears token and tenant cache, redirects to `/login`.

  - **`src/config/nav.ts`**  
    - Central nav config: labels, routes, capability keys for filtering in Sidebar.

- **App entry and routing:**
  - **`src/main.tsx`**  
    - Removed MUI `ThemeProvider` and `CssBaseline`.  
    - Added `import './index.css'`.  
    - Kept `QueryClientProvider` and `BrowserRouter`.

  - **`src/App.tsx`**  
    - Replaced `<AppShell />` with `<Layout />`.  
    - All routes unchanged (same paths and components).  
    - Still uses `RequireAuth` (token check) and `RequireCapability` where applicable.

### 2.2 Components migrated to Tailwind (logic unchanged)

- **`src/components/TenantContext.tsx`**  
  - **TenantBadge:** MUI `Alert` → Tailwind: `rounded-lg border border-slate-600 bg-slate-700/50` + text.  
  - **TenantSelector:** MUI `TextField` + `MenuItem` → native `<select>` with same options and `onChange` (still calls `setEffectiveTenant` and `window.location.reload()` when tenant changes).

- **`src/components/RequireCapability.tsx`**  
  - MUI `Box` + `Alert` → Tailwind: `rounded-lg border border-amber-500/50 bg-amber-500/10` + message text.  
  - Capability and role checks unchanged.

- **`src/components/TimezoneSelect.tsx`**  
  - MUI `Autocomplete` + `TextField` → native `<select>` with same options and `onChange`.  
  - `getTimeZones()` and fallback list unchanged.

- **`src/pages/Login.tsx`**  
  - MUI `Box`, `Card`, `CardContent`, `TextField`, `Button`, `Typography` → Tailwind: centered container, card-style div, inputs and button with slate/blue classes.  
  - Form state, `login()`, redirect from `location.state?.from`, and error handling unchanged.

### 2.3 Pages migrated to Tailwind (logic unchanged)

- **`src/pages/Dashboard.tsx`**  
  - MUI (Box, Card, Grid, Typography, Stack, Skeleton, Alert, Chip) → Tailwind (grid, rounded cards, text utilities).  
  - `getDashboardSummary(tenant)`, loading/error state, and all derived data (modules, revenue, appointments, store orders, professional performance, top sellers, low stock) unchanged.

- **`src/pages/Promotions/Index.tsx`**  
  - MUI Table/Card/Button → Tailwind table and buttons.  
  - `listPromotions(tenant)`, links to Simulator/New/Detail unchanged.

- **`src/pages/Customers/Index.tsx`**  
  - MUI Table, Dialog, TextField, Select, Chip, Buttons → Tailwind table, modal (fixed overlay + div), inputs, select, status badge, buttons.  
  - `listCustomers`, `upsertCustomer`, `importCustomersCsv`, `setCustomerActive`, `isValidE164`, pagination, filters, and edit modal logic unchanged.

- **`src/pages/WhatsApp/MenusIndex.tsx`**  
  - MUI Table, Card, Dialog, Button, Chip → Tailwind table, cards, modal, buttons, status badge.  
  - `listMenus`, `publishMenu`, `getMenu`, `upsertMenu`, `deleteMenu`, `getWhatsAppConfig`, navigation to triggers/config/wizard/editor unchanged.

### 2.4 Pages still using MUI (same logic; can be migrated with same pattern)

These pages were **not** converted to Tailwind in this pass. Their **behavior and API usage are unchanged**; only the shell (Layout/Sidebar) and the migrated pages use the new theme. To align them with the new theme:

- Replace MUI layout components with Tailwind:  
  `Box` → `div` with appropriate classes (`flex`, `grid`, `space-y-*`, `p-4`, etc.).  
- Replace `Card`/`CardContent` → `div` with `rounded-xl border border-slate-700 bg-slate-800 p-4`.  
- Replace `Table`/`TableHead`/`TableBody`/`TableRow`/`TableCell` → `<table>` with Tailwind table classes (as in Customers/Index or MenusIndex).  
- Replace `Button` → `<button>` with `rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-500` (or outline variant).  
- Replace `TextField` → `<input>` / `<textarea>` with `rounded-lg border border-slate-600 bg-slate-700 px-3 py-2 text-white`.  
- Replace `Dialog` → fixed overlay + centered div (pattern used in Customers/Index and MenusIndex).  
- Replace `Alert` → `div` with `rounded-lg border border-*-500/50 bg-*-500/10 text-*-200`.  
- Replace `Chip` → `span` with `rounded px-2 py-0.5 text-xs bg-*-500/20 text-*-300`.  
- Keep all `useState`, `useEffect`, API calls, and event handlers as-is.

List of pages still on MUI:

- Settings.tsx  
- Professionals/Index.tsx, Services/Index.tsx  
- Users/Index.tsx  
- Staff/Index.tsx, Staff/New.tsx, Staff/Edit.tsx  
- Appointments/Index.tsx  
- Followups/Index.tsx  
- Reports/Index.tsx  
- Retention/Index.tsx  
- Store/Carts.tsx, Store/Orders.tsx, Store/Products.tsx, Store/Categories.tsx  
- Promotions/Detail.tsx, Promotions/New.tsx, Promotions/Simulator.tsx  
- WhatsApp/MenuEditor.tsx, WhatsApp/MenuWizard.tsx, WhatsApp/Config.tsx  
- WhatsApp/TriggersIndex.tsx, WhatsApp/TriggerEdit.tsx  
- WhatsApp/WorkflowManager.tsx, WhatsApp/BotModule.tsx  
- AI/Index.tsx, AI/AppointmentsAssist.tsx, AI/Predictions.tsx  
- Tenants/Index.tsx, Tenants/New.tsx  
- Admin/CronJobs.tsx  
- components/charts/LineChart.tsx, components/charts/ChartToolbar.tsx  
- components/WhatsAppPreview.tsx  

**AppShell.tsx** is no longer used (replaced by Layout + Sidebar); it can be removed once all pages are migrated if desired.

### 2.5 Dependencies

- **Tailwind:** Added `tailwindcss`, `@tailwindcss/vite` (dev).  
- **MUI:** Kept `@mui/material`, `@emotion/react`, `@emotion/styled`, `@mui/icons-material` so that pages still using MUI continue to work.  
- No other dependency or API contract changes.

---

## 3. old_app (Python backend)

- **Scope:** All changes are **inside the old_app folder** (and docs).  
- **Logic:** No business logic, API contracts, or database behavior were changed.  
- **Structure:**  
  - **Services:** `old_app/services/` – core, store, whatsapp, workflow, ai, salon, promotions, etc.  
  - **Repositories:** `old_app/repositories/` – tenant, customer, appointment, order, product, etc.  
  - **Models:** `old_app/models/` – customers, professionals, workflows, users, etc.  
  - **Helpers / utils:** `old_app/helpers/`, `old_app/utils/` (e.g. constants).  

- **Optimization notes (for future refactors):**  
  - Prefer importing from `app.utils.constants` (e.g. appointment/slot statuses) instead of repeating string literals.  
  - Repositories already abstract DB access; services can depend on repositories instead of direct DB calls where it simplifies testing.  
  - Type hints and small helpers can be added incrementally without changing behavior.  

No code changes were applied inside **old_app** in this revamp; only this documentation. All logic and use cases remain as before.

---

## 4. File-level change summary

### admin_ui – new or heavily updated

| File | Change |
|------|--------|
| `package.json` | Tailwind + Vite plugin added; MUI kept. |
| `vite.config.ts` | `tailwindcss()` plugin added. |
| `src/index.css` | New file: Tailwind import + theme variables. |
| `src/main.tsx` | MUI theme removed; `index.css` imported. |
| `src/App.tsx` | AppShell → Layout; routes unchanged. |
| `src/config/nav.ts` | New: central nav config for Sidebar. |
| `src/components/Layout.tsx` | New: main layout (sidebar + outlet, banners). |
| `src/components/Sidebar.tsx` | New: capability/module-based nav, tenant UI, logout. |
| `src/components/TenantContext.tsx` | MUI → Tailwind (badge + select). |
| `src/components/RequireCapability.tsx` | MUI Alert → Tailwind alert box. |
| `src/components/TimezoneSelect.tsx` | MUI Autocomplete → native select. |
| `src/pages/Login.tsx` | MUI → Tailwind form and layout. |
| `src/pages/Dashboard.tsx` | MUI → Tailwind; same data and logic. |
| `src/pages/Promotions/Index.tsx` | MUI → Tailwind; same API and links. |
| `src/pages/Customers/Index.tsx` | MUI → Tailwind; same CRUD and CSV import. |
| `src/pages/WhatsApp/MenusIndex.tsx` | MUI → Tailwind; same menus API and actions. |

### admin_ui – unchanged (logic)

- All API modules under `src/api/`.  
- All hooks under `src/hooks/`.  
- All other pages and components (only their layout/styling would change when migrated with the pattern above).

### old_app

- No file content changes.  
- Logic and use cases preserved; structure documented in this report.

---

## 5. How to run and verify

- **admin_ui:**  
  - `cd admin_ui && npm install && npm run dev`  
  - Log in; you should see the new sidebar and layout.  
  - Migrated pages (Dashboard, Promotions list, Customers, WhatsApp Menus) use the new theme; others still use MUI until migrated with the same pattern.

- **old_app:**  
  - Run as before (e.g. existing backend entrypoint).  
  - No intentional change in endpoints or behavior.

---

## 6. Conclusion

- **admin_ui:** New theme and layout match the new app (Tailwind, slate palette, sidebar + main). All logic is preserved; several key pages and shared components were fully migrated; the rest can be migrated using the same Tailwind substitution pattern.  
- **old_app:** No code changes; all logic and use cases kept; structure and optional optimizations documented for future work.

End of revamp report.
