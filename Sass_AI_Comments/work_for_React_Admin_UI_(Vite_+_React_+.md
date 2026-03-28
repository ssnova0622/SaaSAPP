### React Admin UI plan (Vite + React + TypeScript + MUI)

#### Goals
- Deliver a production‑ready Admin SPA for the AI Scheduler backend you already have.
- Authenticate with JWT (`POST /v1/auth/login`).
- Manage tenants, customers, promotions (send via both channels), appointments, reports (PDF via S3/local), and retention, with realtime WebSocket progress for promotions.

---

### 1) Tech stack and project bootstrap
- Tooling: Vite, React 18, TypeScript, React Router v6, React Query, Axios, MUI v6, notistack (toasts), dayjs (TZ/date), papaparse (CSV preview), zod (optional schema validation).
- Directory: create `admin_ui/` at repo root.
- Scripts:
  - `dev`: Vite dev server on `http://localhost:5173`.
  - `build`: production build.
  - `preview`: serve dist locally for smoke tests.
- Env config:
  - `.env.development`: `VITE_API_BASE=http://127.0.0.1:8100/v1`.
  - Backend CORS already allows `http://localhost:5173` per `settings.env`.

---

### 2) App architecture
- Top‑level layout: `AppShell` with left nav (MUI Drawer), header (tenant picker, user menu), content outlet.
- Routing (React Router):
  - `/login`
  - `/` → Dashboard (requires auth)
  - `/settings`
  - `/customers`
  - `/promotions`
  - `/promotions/:id`
  - `/appointments`
  - `/followups`
  - `/reports`
  - `/retention`
- Auth flow:
  - Login page posts to `POST /auth/login`.
  - Store `access_token` (JWT) in memory + `localStorage` fallback; attach `Authorization: Bearer <token>` via Axios interceptor.
  - 401 handler → signout and redirect to `/login`.
- Data fetching:
  - React Query client with sensible `staleTime`/`cacheTime` per resource.
  - Query keys: `['tenants']`, `['tenant', id]`, `['customers', tenant, params]`, `['promotions', tenant]`, `['promotionLogs', id, params]`, `['analytics', tenant]`, `['appointments', tenant]`, `['followups', tenant]`, `['reports', tenant]`, `['retentionSummary', tenant]`.
- Realtime:
  - WS client to `ws://127.0.0.1:8100/ws/{tenant}` with auto‑reconnect; listen for `promotion.started|progress|completed` and surface in Promotions UI.

---

### 3) API integration map (existing backend)
- Auth: `POST /v1/auth/login` → token.
- Tenants: `GET /v1/tenants`, `GET /v1/tenants/{tenant}`, `PUT /v1/tenants/{tenant}`.
- Customers: `GET /v1/tenants/{tenant}/customers`, `POST /v1/tenants/{tenant}/customers`, `POST /v1/tenants/{tenant}/customers/import` (multipart CSV).
- Promotions: `POST /v1/tenants/{tenant}/promotions`, `GET /v1/tenants/{tenant}/promotions`, `GET /v1/tenants/{tenant}/promotions/{id}`, `PUT /v1/tenants/{tenant}/promotions/{id}`, `POST /v1/tenants/{tenant}/promotions/{id}/send`, `GET /v1/tenants/{tenant}/promotions/{id}/logs` (filters supported: `status`, `channel`, `from_ts`, `to_ts`).
- Appointments: `GET /v1/tenants/{tenant}/appointments`, `POST /v1/tenants/{tenant}/appointments`, `DELETE /v1/tenants/{tenant}/appointments/{appointment_id}`.
- Analytics: `GET /v1/tenants/{tenant}/analytics`.
- WS: `/ws/{tenant}`.
- Reports/Follow‑ups/Retention: Frontend will scaffold pages and API hooks; if endpoints are not yet live, pages will display placeholders and progressively enable as backend ships.

---

### 4) UI pages and features

#### 4.1 Login
- Simple MUI form (username/password) → `POST /auth/login`.
- Store token; redirect to dashboard.

#### 4.2 Dashboard
- Tenant selector (persist selection in `localStorage`).
- KPIs from `GET /tenants/{tenant}/analytics`: total appointments, cancellations, revenue.
- Promotions section: current/last 5 campaigns, realtime progress if any running.

#### 4.3 Settings
- Form bound to `GET/PUT /tenants/{tenant}` for: `owner_email`, `owner_phone`, `tz` (default `Asia/Kolkata`), `invoice_delivery` (fixed to `both`), follow‑up timings/templates (textareas).
- Validate TZ against IANA list (use `@vvo/tzdb` or a small whitelist including `Asia/Kolkata`).

#### 4.4 Customers
- Table with server pagination and search (name/phone/email) using `GET /customers`.
- Create/Update drawer: `POST /customers` upsert.
- Tags chips, filter by tag.
- Import CSV wizard:
  - Client preview with papaparse; map columns; POST file to `/customers/import`.
  - Show server result `{inserted, updated, failed, errors}`.

#### 4.5 Promotions
- List: cards/table with name, status, created/scheduled times; actions (Edit, Send Now, View Logs).
- Create/Edit wizard:
  - Step 1: Content (name, message, optional HTML preview), channel = `both` by default.
  - Step 2: Audience (all | tags | custom phones/emails).
  - Step 3: Schedule now or time (UTC ISO); call `POST` then optional `send`.
- Detail page:
  - Summary + live progress bar from WS.
  - Logs tab using `GET /promotions/{id}/logs` with filters (`status=sent|failed`, `channel=whatsapp|email`, date range).
  - Action buttons: Send Now (POST `/send`), Cancel (future), Duplicate (create from existing data, UI only for now).

#### 4.6 Appointments
- Table of recent appointments via `GET /appointments`; cancel action via `DELETE`.
- Quick create modal using existing `POST /appointments` (handy for phone‑in bookings).

#### 4.7 Follow‑ups
- If backend endpoints exist: list scheduled follow‑ups; cancel action.
- If not yet available: show placeholder message “Coming soon; backend en route”.

#### 4.8 Reports
- List recent reports (when endpoints are live): date, status, channel(s), “Open PDF” (presigned URL) and “Generate now”.
- In dev (`S3_ENABLED=false`), display `file://` link to local path returned.

#### 4.9 Retention
- Summary tiles (active, at_risk, churned). List by segment and button to “Create promotion for this segment” pre‑filling the audience.

---

### 5) Components and utilities
- `ApiProvider` with Axios instance:
  - Base URL from `VITE_API_BASE`.
  - Request interceptor to attach `Authorization` header.
  - Response interceptor for 401 → signout.
- `WsProvider` with reconnecting WS and React context per tenant.
- Reusable components: `DataTable`, `ConfirmDialog`, `FormTextField`, `FormSelect`, `TagChips`, `CsvDropzone`, `ProgressWithStats`.
- Notifications: notistack; global error boundary and centralized error handler.

---

### 6) State, caching, and performance
- React Query for all server data, with query invalidation patterns:
  - After `PUT /tenants/{tenant}` → invalidate `['tenant', tenant]`.
  - After customer upsert/import → invalidate `['customers', tenant]`.
  - After promotion create/update/send → invalidate `['promotions', tenant]` and `['promotionLogs', id]`.
- Optimistic UI for quick upserts; rollback on error.

---

### 7) Security considerations
- JWT stored in memory with `localStorage` fallback; consider HTTP‑only cookie in future.
- Sanitize audience free‑text fields and HTML preview (use `dompurify`) — promotion HTML is optional.
- Validate CSV size and columns client‑side before upload.

---

### 8) Developer experience
- ESLint + Prettier + TypeScript strict mode.
- Absolute imports via tsconfig `paths`.
- MUI theme file with brand colors; dark mode toggle (optional).

---

### 9) Testing
- Unit tests with Vitest + React Testing Library for components (forms, tables, CSV import flow).
- Integration tests (optional now) with Playwright: login, customers import, create/send promotion (no‑op), see WS progress.

---

### 10) Folder structure (proposed)
```
admin_ui/
  src/
    api/
      axios.ts
      auth.ts
      tenants.tsx
      customers.ts
      promotions.ts
      appointments.tsx
      reports.tsx
      followups.ts
      retention.ts
    components/
      AppShell/
      DataTable/
      ConfirmDialog/
      CsvDropzone/
      Promotion/
    hooks/
      useAuth.ts
      useTenant.ts
      useWebSocket.ts
    pages/
      Login.tsx
      Dashboard.tsx
      Settings.tsx
      Customers/
        Index.tsx
        Import.tsx
        EditDialog.tsx
      Promotions/
        Index.tsx
        New.tsx
        Detail.tsx
      Appointments/Index.tsx
      Followups/Index.tsx
      Reports/Index.tsx
      Retention/Index.tsx
    routes.tsx
    App.tsx
    main.tsx
  index.html
  tsconfig.json
  vite.config.ts
  package.json
  .env.development
```

---

### 11) Milestones, timelines, and acceptance criteria

Milestone A — Bootstrap + Auth + Shell (0.5–1 day)
- Create `admin_ui` with Vite, TS, MUI, React Router, React Query.
- Implement login and token storage; Axios interceptors.
- AppShell with tenant picker wired to `GET /v1/tenants`.
- Acceptance: can login and see dashboard shell with selected tenant persisted.

Milestone B — Settings + Customers (1–2 days)
- Settings page bound to `GET/PUT /tenants/{tenant}`.
- Customers list with pagination/search; create/upsert dialog; CSV import flow with preview and server result.
- Acceptance: can import CSV and see counts; list/search works; settings saved and validated (TZ).

Milestone C — Promotions end‑to‑end (2 days)
- List/Create/Edit/Detail pages; audience wizard; Send Now; Logs with filters; WS progress bar.
- Acceptance: create campaign, send in no‑op mode, see realtime progress events and logs.

Milestone D — Appointments (0.5 day)
- List/cancel; quick create modal.
- Acceptance: can create and cancel via UI (affects backend state and WS events appear).

Milestone E — Follow‑ups (0.5–1 day once backend endpoints are ready)
- List scheduled; cancel action; status chips.
- Acceptance: items display and can be canceled; reflects dispatcher actions (no‑op is fine).

Milestone F — Reports (1 day)
- List reports; manual “Generate Now”; open link.
- Acceptance: manual run returns a valid link (file:// in dev or S3 presigned in prod) and list shows entries.

Milestone G — Retention (1 day)
- Summary tiles and lists by segment; “Create promotion from segment”.
- Acceptance: segment lists render; action pre‑fills Promotions audience.

Milestone H — Polish, tests, docs (1–2 days)
- Add toasts, loading/error states, table empty placeholders, responsive tweaks.
- Vitest unit tests for key flows; README for frontend run.

---

### 12) Run instructions (frontend)
- In repo root:
```
cd admin_ui
npm create vite@latest . -- --template react-ts   # initial scaffold (done once)
npm install @mui/material @emotion/react @emotion/styled @mui/icons-material @tanstack/react-query axios notistack react-router-dom dayjs papaparse dompurify
npm install -D eslint prettier @types/node @types/react @types/react-dom vite-tsconfig-paths
```
- Create `.env.development`:
```
VITE_API_BASE=http://127.0.0.1:8100/v1
```
- Start backend (`uvicorn ...`) and frontend:
```
npm run dev
```

---

### 13) Risks & mitigations
- Backend endpoints for follow‑ups/reports/retention may arrive later → show placeholders and progressively enable.
- WS connectivity drops → auto‑reconnect; keep last known progress via React Query cache.
- Timezone handling → keep UI display with dayjs; store server TZ (IANA) fetched from tenant settings.

---

### 14) Deliverables
- `admin_ui/` project with documented scripts and env.
- Fully wired pages: Login, Dashboard, Settings, Customers, Promotions, Appointments (Follow‑ups/Reports/Retention as backend matures).
- README updates and a short Loom/GIF walkthrough (optional).

If you approve this plan, I’ll scaffold `admin_ui/` and deliver Milestone A → C first so you can start using Promotions end‑to‑end in the UI quickly.