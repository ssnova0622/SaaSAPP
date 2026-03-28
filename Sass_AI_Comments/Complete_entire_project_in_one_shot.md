### Project Completion Plan — “Complete entire project in one shot”

Below is a single, end‑to‑end execution plan to take the AI‑Powered Appointment & Scheduling System to a complete, demo‑ready, and deployable state. It covers the FastAPI backend (Mongo), the React Admin UI (Vite + TS + MUI), messaging (Twilio/SMTP), daily PDF reports (ReportLab → S3 with presigned URLs), follow‑ups, retention analytics, testing, packaging, and deployment.

---

### 1) Ground truth and readiness

- Code branches and envs
  - Main branch: stabilize the current backend and `admin_ui/` scaffolding.
  - `.env` template with dummy creds (Twilio/SMTP/S3 disabled by flags) for local dev.
- Data dependencies
  - MongoDB running locally via Docker or service.
  - Seed tenants: `demo-salon`, `demo-clinic` (optional re‑enable seeding or provide POST tenant flow).
- Confirm feature flags
  - `TWILIO_ENABLED=false`, `SMTP_ENABLED=false`, `S3_ENABLED=false` for local.
  - `SCHEDULER_ENABLED=true`.
  - `DEFAULT_TZ=Asia/Kolkata`.

Acceptance criteria:
- `uvicorn ai_scheduler.main:create_app --factory` boots, `/health` returns `{status:"ok"}`.
- `admin_ui` runs on `http://localhost:5173` (CORS permitted) after login token flow added.

---

### 2) Backend feature completion

#### 2.1 Follow‑ups (scheduling + dispatch)
- Storage
  - Create `followups` collection with indexes: `(tenant, run_at, status)`, `(tenant, appointment_id)`.
- Triggers
  - On `POST /v1/tenants/{tenant}/appointments`: enqueue `confirm(now)`, `reminder24`, `reminder2`, `post(+4h or next morning 10:00 tenant TZ)`.
  - On `DELETE /v1/tenants/{tenant}/appointments/{id}`: cancel pending; optionally enqueue `recovery`.
- Dispatcher
  - APScheduler job every 60s: pick due items, send via both channels (if available), retry transient failures (3 attempts, exp backoff), mark `sent|failed`.
- Templates
  - Extend `tenants` doc with `templates.confirm`, `templates.reminder24`, `templates.reminder2`, `templates.post`, `templates.recovery` with placeholders: `{{customer_name}}`, `{{professional}}`, `{{time}}`, `{{tenant}}`.
- API (JWT)
  - `GET /v1/tenants/{tenant}/followups?status=&from=&to=`
  - `POST /v1/tenants/{tenant}/followups/{id}/cancel`
- Realtime
  - WS events: `followup.sent`, `followup.failed`.

Acceptance criteria:
- Creating/canceling appointments changes scheduled follow‑ups appropriately; dispatcher drains due follow‑ups (no‑op in dev) and emits WS events.

#### 2.2 Daily reports (ReportLab → S3, presigned URLs)
- PDF
  - Use existing `build_daily_report(tenant, date)`; augment content later using real day’s appointments.
- Storage
  - `reports` collection: `{ tenant, date, s3_key_or_path, created_at, sent_via:['email','whatsapp'], status, error? }` with `(tenant, date)` index.
- S3 integration
  - Use `S3Reports.upload_report()` and `get_presigned_url()`; local fallback when `S3_ENABLED=false`.
- Scheduler
  - Per‑tenant cron at `19:30` in tenant TZ (default Asia/Kolkata) registered on startup.
- Delivery
  - Email attachment (if `SMTP_ENABLED=true`) and/or link; WhatsApp with presigned link.
- API (JWT)
  - `POST /v1/tenants/{tenant}/reports/daily/run?date=YYYY-MM-DD`
  - `GET /v1/tenants/{tenant}/reports/daily` → list with fresh links.

Acceptance criteria:
- Manual run returns a valid URL (file:// in dev); scheduled runs create entries at the configured local time.

#### 2.3 Retention analytics
- Aggregation job (nightly)
  - Compute segments: `active (≤30d)`, `at_risk (31–60d)`, `churned (>60d)` from appointment history.
  - Store in `retention_metrics` with `(tenant, date)` index.
- API (JWT)
  - `GET /v1/tenants/{tenant}/customers/retention/summary`
  - `GET /v1/tenants/{tenant}/customers/retention/list?segment=at_risk&days=45`
- Integrate with Promotions
  - Allow pre‑filling a promotion audience from a segment.

Acceptance criteria:
- Returns consistent counts for demo data; segment lists feed promotions.

---

### 3) Promotions hardening (already implemented first drop)

- Throttling via env: `PROMO_BATCH_SIZE` (default 50), `PROMO_RPS` (default 20).
- Realtime WS: `promotion.started`, `promotion.progress`, `promotion.completed`.
- Idempotency guard: unique index on `(promotion_id, channel, to)` and runtime checks.
- Logs filter API: `status`, `channel`, `from_ts`, `to_ts`.

Acceptance criteria:
- With dev flags off (no‑op), creating and sending a promotion shows realtime progress and logs match counts; re‑send is safe.

---

### 4) React Admin UI completion (Vite + TS + MUI)

Milestone B — Settings + Customers
- Login page calling `/v1/auth/login`, store JWT; route guards.
- AppShell with MUI AppBar/Drawer and Tenant picker bound to `GET /v1/tenants`.
- Settings page bound to `GET/PUT /v1/tenants/{tenant}` (email/phone/TZ/delivery/templates).
- Customers page:
  - Data table with server pagination/search; create/upsert drawer.
  - CSV import wizard (papaparse preview) → `POST /customers/import` and show result stats.

Milestone C — Promotions
- List/Create/Edit/Detail pages.
- Audience wizard: all | tags | custom.
- Send Now and scheduled sends; Logs tab with filters and WS progress bar.

Milestone D — Appointments
- List/book/cancel binding to existing endpoints, with inline feedback.

Milestone E — Follow‑ups
- List scheduled follow‑ups, status chips, cancel action; reflect dispatcher actions in near real time.

Milestone F — Reports
- List recent reports, manual generate, open link (file:// or presigned URL).

Milestone G — Retention
- Summary tiles and lists by segment; quick action to “Create promotion from segment”.

Acceptance criteria (UI):
- Full admin flows are possible from React (login → choose tenant → manage customers → create/send promotions with progress → view appointments → see follow‑ups → run/open reports → retention views).

---

### 5) Security and configuration

- JWT roles & claims
  - For now, `role=admin`; later add `ops` and `viewer` and gate routes.
- Input validation and limits
  - CSV import: size cap; column checks.
  - Promotions content: sanitize HTML (`dompurify` on client side).
- Rate limiting and backoff
  - Promotions dispatcher and follow‑ups dispatcher use env‑driven throttle; retries with exponential backoff.
- Secrets hygiene
  - `.env.example` with dummy values; document flags to prevent accidental sends.

Acceptance criteria:
- Unauthorized requests rejected; 4xx errors are informative; no secrets in logs.

---

### 6) Testing strategy

- Unit tests (Python)
  - Audience resolver; phone normalization; follow‑up scheduling math; PDF generator (metadata only); S3 presign helper (mocked).
- Integration tests (Python + FastAPI TestClient + Mongo test DB)
  - JWT login; tenants/customers; promotions send (no‑op); appointment → follow‑up hooks; manual reports run/list; WS progress observed (can be smoke‑tested manually).
- Frontend tests (Vitest + React Testing Library)
  - Auth flow; Settings save; Customers import flow; Promotions wizard and progress UI.

Acceptance criteria:
- Core unit tests pass locally; minimal integration coverage proves main flows.

---

### 7) Packaging & deployment

- Docker
  - Backend Dockerfile (uvicorn, prod settings, healthcheck); `.dockerignore`.
  - Frontend Dockerfile (build → static assets served by Nginx or Vite preview for demo).
- docker‑compose (dev/demo)
  - Services: mongo, backend, admin_ui, (optional) nginx; networks; env files; volumes.
- CI (GitHub Actions or similar)
  - Lint + type check + unit tests on PR.
  - Build Docker images on main; optional push to registry.
- Config for staging/production
  - Flip flags to enable Twilio/SMTP/S3; set real credentials via secrets manager.

Acceptance criteria:
- `docker compose up` brings up Mongo + backend + admin_ui; healthchecks pass; Admin UI works end‑to‑end in no‑op mode.

---

### 8) Operational runbook

- Feature flags
  - Start in no‑op: `TWILIO_ENABLED=false`, `SMTP_ENABLED=false`, `S3_ENABLED=false`.
  - Enable one by one in staging with real credentials; monitor logs.
- Scheduler
  - Ensure `SCHEDULER_ENABLED=true`; check log lines: `dispatch_promotions`, `dispatch_followups`, `daily_reports_tick`.
- Backups
  - Mongo dump instructions; S3 reports retained per bucket lifecycle policy.
- Observability (basic)
  - Structured logs for dispatchers; counts for sent/failed; report generation outcomes.

---

### 9) Timeline (aggressive, sequential but parallelizable)

- Week 1
  - Finish Follow‑ups backend (2–3 days) and wire Reports to S3 + manual run endpoint (2 days).
  - Promotions hardening (done) + polish (0.5 day).
- Week 2
  - Retention backend (1.5–2 days).
  - React Admin Milestones B–C (Settings/Customers/Promotions) (3–4 days).
- Week 3
  - React Admin Milestones D–G (Appointments/Follow‑ups/Reports/Retention) (3–4 days).
  - Security hardening + tests + docs + dockerization (2–3 days).

You can compress by parallelizing UI and backend work.

---

### 10) Deliverables checklist

- Backend
  - Follow‑ups: collection, hooks, dispatcher, JWT endpoints, WS events.
  - Reports: S3 integration, cron scheduling per tenant TZ, manual run/list endpoints, delivery via both channels.
  - Retention: nightly aggregation, summary/list endpoints.
  - Promotions: realtime progress, throttles, idempotency, logs filters.
- Frontend (admin_ui)
  - Auth + AppShell + Tenant picker.
  - Settings, Customers (incl. CSV), Promotions (with WS), Appointments, Follow‑ups, Reports, Retention.
- Ops
  - `.env.example` and README run instructions for backend and frontend.
  - Dockerfiles + docker‑compose.
  - Minimal CI (lint/test/build) and Postman collection.

---

### 11) How you can proceed today

- Backend
  - Keep feature flags off; run Mongo + API; verify promotions flow end‑to‑end (no‑op send) and scheduler ticks.
- Frontend
  - Implement Login → AppShell → Settings → Customers (using existing APIs).
  - Then build Promotions pages and connect WebSocket progress to `/ws/{tenant}`.
- Credentials (stage/prod later)
  - Prepare Twilio WhatsApp sender, SMTP creds, AWS S3 bucket/region; flip flags one by one in staging.

If you want, I can now start implementing the remaining backend pieces (Follow‑ups, Reports integration, Retention) and continue building out the React Admin pages according to this plan. Reply “go” and specify if you want any milestone reordered or deprioritized.