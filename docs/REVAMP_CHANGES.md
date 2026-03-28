# SaaS Application Revamp – Change Report

This document describes the revamp of the **app** (Python backend) and **admin_ui** (React admin frontend) folders to align with the theme and structure of **app_ref** and **admin-ui-ref**, while **keeping all existing logic and use cases**.

---

## 1. Summary

| Area | Scope | Logic preserved |
|------|--------|------------------|
| **admin_ui** | Layout, auth, and shell ref-style (Tailwind); key pages converted to Tailwind | Yes – all routes, capabilities, APIs, and behavior unchanged |
| **app** | Structure reviewed; no breaking changes | Yes – all routers, services, and schedulers unchanged |

---

## 2. admin_ui Revamp (Theme & Layout)

### 2.1 Layout and shell (aligned with admin-ui-ref)

- **Before:** Main shell was **AppShell** (MUI `AppBar` + `Drawer`), with nav and tenant selector in the drawer.
- **After:** Main shell is **Layout + Sidebar** (Tailwind only):
  - `flex min-h-screen bg-slate-900`
  - Fixed **Sidebar** (`w-64 min-h-screen bg-slate-800 border-r border-slate-700`) with nav links, tenant selector, and “Sign out”.
  - Main content in `<main className="flex-1 overflow-auto p-6">` with `<Outlet />`.

**Files changed:**

- **`App.tsx`**
  - Replaced `<AppShell />` with `<Layout />` inside `<ProtectedRoute>`.
  - Wrapped app in `<AuthProvider>`.
  - All existing routes and `<RequireCapability>` wrappers kept as-is (paths unchanged).

- **`main.tsx`**
  - Removed MUI-only shell usage; added a **minimal MUI theme** (`createTheme` with `palette.mode: 'dark'`, `primary: '#3b82f6'`) and `CssBaseline` so pages that still use MUI components continue to render correctly during migration.
  - QueryClient default options: `retry: 1`, `refetchOnWindowFocus: false`.

- **`Layout.tsx`** (existing)
  - Already ref-style (Tailwind). Still used; shows offline banner and “select tenant” warning for super admin when no tenant is selected.

- **`Sidebar.tsx`**
  - Uses **AuthContext** for user display and logout (no local token + navigate).
  - Shows “Admin Panel”, user email, optional “Tenant: …”, then TenantSelector/TenantBadge and nav.
  - Nav visibility logic unchanged (CORE_NAV, SALON_NAV, STORE_NAV, AI_NAV, WHATSAPP_BOT_NAV; filtered by role, capabilities, modules).
  - “Sign out” calls `logout()` from `useAuth()` (clears token and redirects to `/login`).

- **`AppShell/AppShell.tsx`**
  - No longer used in routes; can be removed in a later cleanup. All behavior moved to Layout + Sidebar.

### 2.2 Auth (ref-style, logic preserved)

- **Before:** Route guard used `tokenStore.get()` directly (`RequireAuth`).
- **After:**
  - **`contexts/AuthContext.tsx`** (new):
    - Reads JWT from `tokenStore`, decodes payload, exposes `user` (`email`, `tenant`, `role`), `loading`, `isSuperAdmin`, `logout`.
    - `logout()` clears token, clears tenant settings cache, and redirects to `/login`.
  - **`components/ProtectedRoute.tsx`** (new):
    - Uses `useAuth()`; shows a loading state while `loading`; if `!user`, redirects to `/login` with `state={{ from: location }}`.
  - **`RequireCapability.tsx`**:
    - MUI `<Alert>` replaced with shared **`Alert`** component (`variant="warning"`). Capability and tenant-caps logic unchanged.

**Logic preserved:** Same JWT and tokenStore; same capability and tenant-based access rules; only the way “logged-in user” and “redirect when not logged in” are implemented matches the ref pattern.

### 2.3 Tenant selector and badge (Tailwind)

- **`TenantContext.tsx`**:
  - **TenantBadge:** MUI `Alert` replaced with a Tailwind box: `rounded-lg border border-slate-500/50 bg-slate-500/10 px-3 py-2 text-sm text-slate-200`.
  - **TenantSelector:** MUI `TextField` + `MenuItem` replaced with a native `<select>` with Tailwind classes (`border-slate-600 bg-slate-700`, focus ring). Same `listTenants()` and `setEffectiveTenant()` behavior.

### 2.4 Login page (Tailwind)

- **`pages/Login.tsx`**:
  - Reimplemented with Tailwind to match admin-ui-ref:
    - Centered card: `max-w-sm rounded-xl bg-slate-800 border border-slate-700 p-6`.
    - Native inputs with `rounded-lg border border-slate-600 bg-slate-700 text-white`, focus ring.
    - Same `login(email, password)` and redirect from `location.state?.from?.pathname || '/'`.
  - Error display and loading state kept; only markup and styles changed.

### 2.5 Dashboard (Tailwind)

- **`pages/Dashboard.tsx`**:
  - All MUI removed; uses shared components and Tailwind:
    - **PageHeader** for title and module chips.
    - **DataCard** for KPI cards and sections.
    - **Alert** for errors.
  - Same data flow: `useEffectiveTenant()`, `getDashboardSummary(tenant)`, loading/error/data state.
  - Same metrics: 30d revenue, 30d appointments (if salon/clinic), 30d store orders (if store), professional performance, top sellers, low-stock alerts.
  - **MiniRevenueChart** kept (SVG); styling adjusted (e.g. color `#3b82f6`).

### 2.6 Promotions list (Tailwind)

- **`pages/Promotions/Index.tsx`**:
  - MUI (`Box`, `Button`, `Card`, `Table`, `Typography`) replaced with:
    - **PageHeader** (title + “Simulator” / “New Promotion” links).
    - **DataCard** wrapping **AppTable** (AppTableHead, AppTableBody, AppTableRow, AppTh, AppTd).
  - Same behavior: `listPromotions(tenant)`, row click navigates to `/promotions/:id`, Simulator and New links.
  - **AppTableRow** extended to accept `...React.HTMLAttributes<HTMLTableRowElement>` (e.g. `onClick`) for row navigation.

### 2.7 Shared UI and config

- **`components/ui/Alert.tsx`** – already Tailwind; used by RequireCapability and Dashboard.
- **`components/ui/PageHeader.tsx`** – already ref-style; used by Dashboard and Promotions/Index.
- **`components/ui/DataCard.tsx`** – already ref-style; used by Dashboard and Promotions/Index.
- **`components/ui/AppTable.tsx`** – AppTableRow now accepts standard `<tr>` props (e.g. `onClick`).
- **`tsconfig.json`** – added path alias `"@contexts/*": ["src/contexts/*"]` for `AuthContext`.

### 2.8 Pages still using MUI (unchanged logic)

The following pages still use MUI components for tables, forms, dialogs, and chips. **Behavior and API usage are unchanged**; only the shell and the pages above use the new theme. They can be migrated later using the same pattern (PageHeader, DataCard, AppTable, Alert, native/Tailwind inputs and buttons):

- Settings, Customers, Staff (Index, New, Edit), Users, Tenants (Index, New)
- Promotions: New, Detail, Simulator
- Followups, Reports, Retention
- Appointments, Services, Professionals
- Store: Carts, Orders, Products, Categories
- WhatsApp: MenusIndex, MenuEditor, Config, TriggersIndex, TriggerEdit, MenuWizard, BotModule, WorkflowManager
- AI: Index, AppointmentsAssist, Predictions
- Admin: CronJobs
- Components: WhatsAppPreview, TimezoneSelect, charts (LineChart, ChartToolbar)

A minimal MUI theme is still provided in `main.tsx` so these pages render correctly during the transition.

---

## 3. Backend (app) – No structural or logic changes

The **app** folder (FastAPI backend) was reviewed for alignment with **app_ref** and for cleanup. Conclusion:

- **Routers:** All existing routers are still mounted under `/v1` (and WebSocket at `/`). No routes or tags were removed or renamed.
- **Services and repositories:** All business logic (appointments, promotions, followups, retention, reports, store, catalog, WhatsApp, AI, workflows, cron, etc.) is unchanged.
- **Scheduler:** Startup/shutdown and job definitions (e.g. `dispatch_promotions`, `dispatch_followups`, `retention_nightly`, `daily_reports_tenant`, `stock_alerts`) are unchanged.
- **CORS, health, bootstrap:** Unchanged.

No code changes were made in **app**; all logic and use cases are preserved. Any future alignment with app_ref (e.g. router grouping or naming) can be done in a separate task without affecting the revamp described here.

---

## 4. File-level change list

### admin_ui – New files

- `src/contexts/AuthContext.tsx` – Auth state from JWT, logout.
- `src/components/ProtectedRoute.tsx` – Auth guard with loading and redirect.

### admin_ui – Modified files

- `src/App.tsx` – Layout, ProtectedRoute, AuthProvider; routes unchanged.
- `src/main.tsx` – Minimal MUI theme + CssBaseline; QueryClient options.
- `src/components/Sidebar.tsx` – useAuth for user/logout; user email and tenant in header.
- `src/components/RequireCapability.tsx` – MUI Alert replaced with shared Alert.
- `src/components/TenantContext.tsx` – TenantBadge and TenantSelector converted to Tailwind.
- `src/components/ui/AppTable.tsx` – AppTableRow accepts HTML table row attributes.
- `src/pages/Login.tsx` – Tailwind layout and inputs; same login/redirect logic.
- `src/pages/Dashboard.tsx` – Tailwind + PageHeader/DataCard/Alert; same data and metrics.
- `src/pages/Promotions/Index.tsx` – Tailwind + PageHeader/DataCard/AppTable; same list and navigation.
- `tsconfig.json` – Added `@contexts/*` path.

### app – Modified files

- None.

---

## 5. How to run and verify

- **Backend:** Unchanged; run as before (e.g. `uvicorn` or your usual command).
- **admin_ui:**  
  - `npm install` (if needed) then `npm run dev`.  
  - Login still uses same API (`/v1/auth/login`); JWT and capabilities unchanged.  
  - You should see the new Layout + Sidebar (ref-style), Tailwind Login/Dashboard/Promotions list, and all other pages working as before (with MUI where not yet migrated).

---

## 6. Optional next steps

1. **Remove AppShell:** Delete `src/components/AppShell/AppShell.tsx` (and its directory) once you are satisfied with Layout + Sidebar.
2. **Migrate remaining pages:** Replace MUI in the pages listed in §2.8 with Tailwind + PageHeader/DataCard/AppTable/Alert and native or Tailwind form controls, reusing the same API and state logic.
3. **Drop MUI:** After all pages are migrated, remove `@mui/material` and `@mui/icons-material` and the MUI theme/CssBaseline from `main.tsx`.

This completes the revamp report: theme and layout aligned with admin-ui-ref, all logic preserved in **app** and **admin_ui**, with a clear path for full Tailwind migration.
