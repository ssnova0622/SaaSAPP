### Updated plan with React Admin UI (and send via both channels)

You’ve chosen a React JS Admin UI (instead of server‑rendered) and to send messages via both WhatsApp and Email. Below is the refined plan covering the React app, the API surface we’ll expose from FastAPI, messaging, scheduler jobs, S3 storage for reports, and how everything ties together.

---

### Tech stack
- Frontend (new):
  - React + Vite (fast dev), TypeScript, React Router, React Query (data fetching), Material UI (MUI) for components.
  - WebSocket client for realtime updates (`/ws/{tenant}` already exists).
  - CSV parsing on client with `papaparse` (preview) + server validation.
- Backend (existing FastAPI + Mongo):
  - Add new REST endpoints to support Admin features.
  - APScheduler for scheduled jobs (promotions, follow‑ups, daily reports) — per‑tenant TZ.
  - Messaging abstraction for Twilio (WhatsApp) + SMTP (Email).
  - ReportLab for PDF generation; upload to S3 with presigned URLs.
  - CORS: allow the React dev server origin.

---

### Frontend app structure
- Directory (proposed): `admin_ui/`
  - `src/`
    - `main.tsx`, `App.tsx`, `routes.tsx`
    - `pages/`
      - `Login.tsx`
      - `Dashboard.tsx`
      - `Settings.tsx`
      - `Customers/Index.tsx`, `Customers/Import.tsx`, `Customers/Edit.tsx`
      - `Promotions/Index.tsx`, `Promotions/New.tsx`, `Promotions/Detail.tsx`
      - `Appointments/Index.tsx`
      - `Reports/Index.tsx`
    - `components/` (Table, Form, Upload, Chart, TenantPicker, WS indicator)
    - `api/` (React Query hooks: tenants, customers, promotions, appointments, reports)
    - `utils/` (auth, date/tz helpers, csv parser wrapper)
  - `vite.config.ts`
  - `.env.development` with `VITE_API_BASE=http://127.0.0.1:8100/v1`

Auth flow:
- Minimal login with API key or username/password stored server‑side. React keeps a session token (HTTP‑only cookie preferred). For MVP, an `X-API-Key` header from a login response stored in memory/localStorage, then include in all API requests.

---

### Backend API extensions (to support React Admin)
We will add the following routers/endpoints under `/v1`:

1) Settings/Tenants
- `GET /v1/tenants` → list tenant ids and basic settings.
- `GET /v1/tenants/{tenant}` → details (owner_email, owner_phone, tz, invoice_delivery, followup templates/prefs).
- `PUT /v1/tenants/{tenant}` → update settings (email, phone, tz=Asia/Kolkata, delivery='both', templates).

2) Customers
- `GET /v1/tenants/{tenant}/customers?search=&tag=&page=&size=` → paginated list.
- `POST /v1/tenants/{tenant}/customers` → create/update single.
- `POST /v1/tenants/{tenant}/customers/import` → CSV import (server validates, upserts by phone); returns stats and error rows.
- `GET /v1/tenants/{tenant}/customers/retention/summary` → {active, at_risk, churned}.
- `GET /v1/tenants/{tenant}/customers/retention/list?segment=at_risk&days=45` → list phones for segment.

3) Promotions (send via both)
- `POST /v1/tenants/{tenant}/promotions` → create promotion: `{ name, channel: 'both', message, html_message?, media_url?, audience:{ type:'all'|'tags'|'custom', tags?, phones? }, schedule_at? }`.
- `GET /v1/tenants/{tenant}/promotions` → list.
- `GET /v1/tenants/{tenant}/promotions/{id}` → detail + aggregate stats.
- `PUT /v1/tenants/{tenant}/promotions/{id}` → update if not started.
- `POST /v1/tenants/{tenant}/promotions/{id}/send` → trigger send now / confirm schedule.
- `GET /v1/tenants/{tenant}/promotions/{id}/logs?page=&size=` → delivery logs.

4) Follow‑ups
- Hooked to existing appointment create/cancel; add endpoints for visibility:
  - `GET /v1/tenants/{tenant}/followups?status=scheduled` → list upcoming.
  - `POST /v1/tenants/{tenant}/followups/{id}/cancel` → cancel a follow‑up.

5) Reports (S3 + ReportLab)
- `POST /v1/tenants/{tenant}/reports/daily/run?date=YYYY-MM-DD` → generate now, upload to S3, return metadata + presigned URL.
- `GET /v1/tenants/{tenant}/reports/daily` → list recent reports with dates and URLs (presigned on demand).

Realtime events (WebSocket `/ws/{tenant}`):
- Extend with: `promotion.started`, `promotion.progress` (sent/failed counts), `promotion.completed`, `followup.sent`, `report.generated`.

Security:
- Admin endpoints guarded by an API key / bearer token.
- CORS updated to allow React dev origin.

---

### Messaging & scheduling (send via both channels)
- `services/messaging.py`:
  - `send_whatsapp_text(to, text)` and `send_whatsapp_media(to, url, caption)` via Twilio WhatsApp sender.
  - `send_email(to, subject, text, html?, attachments?)` via SMTP.
  - Both used by Promotions and Follow‑ups. Promotions with `channel='both'` will execute WhatsApp + Email for every recipient that has both contacts (if only phone, WhatsApp only; only email, email only).
- APScheduler jobs:
  - Promotions dispatcher: picks queued/scheduled promotions, batches deliveries (e.g., 50/s) with retries/backoff; logs to `promotion_logs`.
  - Follow‑ups dispatcher: every minute, sends due tasks; cancels future items on appointment cancellation.
  - Daily reports: per‑tenant TZ (Asia/Kolkata by default), generate PDF → upload S3 → send presigned URL via both channels to owner.

---

### S3 for PDFs (presigned URLs)
- `services/storage_s3.py`:
  - `upload_report(tenant, date, bytes)` returns `s3_key`.
  - `get_presigned_url(s3_key, expiry_seconds=86400)` returns a 24h link used in email/WhatsApp.
- Mongo `reports` collection stores metadata: `{ tenant, date, s3_key, sent_via:['email','whatsapp'], status, created_at }`.

---

### React UI flows
- Login → store token → set `Authorization: Bearer <token>` for API calls.
- Tenant picker → loads KPIs from analytics + retention summary.
- Customers → table with search, tags, CSV import (client preview → POST to server).
- Promotions → Wizard: define content (text + optional HTML), choose audience (all/tags/custom), schedule or send now; live progress feed via WebSocket.
- Appointments → list with cancel action.
- Reports → table with date, status, and “Open PDF” (presigned URL) and “Send again”.
- Settings → edit email/phone, TZ (default Asia/Kolkata), invoice delivery (fixed to both per your choice), follow‑up timings and templates.

---

### Milestones & delivery order
1) Backend foundations: messaging, S3, scheduler, settings endpoints, CORS update.
2) React Admin skeleton: login, layout, tenant picker, Settings page.
3) Customers list + CSV import + server validation.
4) Promotions API + React pages; WebSocket progress; send via both.
5) Follow‑ups: enqueue on appointment create/cancel; dispatcher; visibility page.
6) Reports: ReportLab PDF → S3 → presigned links; daily job; React reports page.
7) Retention: daily metrics + UI views + quick “win‑back” promotions.

---

### What I need from you
- Provide your Twilio WhatsApp sender number (format `whatsapp:+xxxxxxxxxxx`).
- Provide SMTP sender credentials.
- Provide S3 bucket name and region; we’ll default to presigned URLs.
- Confirm if token‑based auth (JWT with a simple in‑app user store) is OK, or you prefer API key only for now.

With this, I’ll start implementing the foundations and the initial React Admin shell. I’ll share startup instructions for the React app (Vite) and the new `.env` entries for both frontend and backend in the first drop.