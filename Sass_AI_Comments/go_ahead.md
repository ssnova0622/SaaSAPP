### Updated Implementation Plan for “go ahead”

#### Objectives
- Finish a demo‑ready system with: FastAPI backend (Mongo), React Admin UI (Vite + TS + MUI), messaging via Twilio/SMTP (feature‑flagged), daily PDFs (ReportLab → S3 presigned links), follow‑ups, promotions with realtime WS progress, retention analytics, and scheduler jobs.
- Keep external sends disabled by default; allow simple switch to enable later.

---

### Milestone 1 — React Admin UI (Core Pages)
Scope: Complete core pages and bind to existing APIs.

- Auth & Shell
  - Finalize Login form (error states, redirect). ✓ scaffolded
  - AppShell: drawer/nav + tenant picker bound to `GET /v1/tenants`. ✓ implemented

- Settings
  - Bind `GET/PUT /v1/tenants/{tenant}`; TZ selection (IANA list), invoice delivery. ✓ implemented (first cut)

- Customers
  - List/search/pagination using `GET /v1/tenants/{tenant}/customers`.
  - Upsert dialog using `POST /v1/tenants/{tenant}/customers`.
  - CSV import wizard (preview with papaparse) posting to `POST /v1/tenants/{tenant}/customers/import` and showing `{inserted, updated, failed}`.

- Promotions
  - Pages: list/create/edit/detail.
  - Audience wizard: `all|tags|custom` (phones/emails).
  - Send Now and schedule; show logs with filters (`status`, `channel`, `from_ts`, `to_ts`).
  - Realtime progress via WS events `promotion.started|progress|completed` from `/ws/{tenant}`.

- Appointments
  - List/create/cancel via existing endpoints: `GET/POST/DELETE /v1/tenants/{tenant}/appointments`.

- Follow‑ups
  - List scheduled with filters; cancel via `POST /v1/tenants/{tenant}/followups/{id}/cancel`.
  - Show live updates from WS `followup.sent|failed`.

- Reports
  - List reports via `GET /v1/tenants/{tenant}/reports/daily`.
  - Manual generate via `POST /v1/tenants/{tenant}/reports/daily/run?date=YYYY-MM-DD`.
  - Open link (file:// in dev, S3 presigned when enabled).

- Retention
  - Summary tiles from `GET /v1/tenants/{tenant}/customers/retention/summary`.
  - List segment via `GET /v1/tenants/{tenant}/customers/retention/list?segment=...`.
  - Button to “Create promotion from segment” pre‑filling the audience.

Acceptance:
- Admin can login, select tenant, manage customers (incl. CSV), create/send promotions (no‑op send), see logs/progress, manage appointments, follow‑ups, generate/open reports, and view retention.

ETA: 5–7 days (iterative: Settings/Customers/Promotions first).

---

### Milestone 2 — Backend Polish & Small Gaps
- Promotions: confirm WS events under load; document throttles `PROMO_BATCH_SIZE`, `PROMO_RPS`.
- Optional: add `POST /v1/tenants/{tenant}/promotions/{id}/cancel` (only if status `draft|scheduled`).
- Follow‑ups: allow tuning offsets via tenant `followup_prefs` (keep defaults for now).
- Reports: ensure per‑tenant TZ registration; fallback to `DEFAULT_TZ` if invalid.
- Retention: ensure indexes on `retention_metrics`, validate nightly job output.
- Error/validation: normalize messages; stricter payload validation where useful.

ETA: 1–2 days (in parallel with UI).

---

### Milestone 3 — Security & Roles
- JWT roles: `admin|ops|viewer` claims added at login.
- Backend route guards: promotions send → `admin|ops`; settings update → `admin`.
- Frontend: route guards and conditional actions by role.
- Input limits: CSV size caps; promotion message length; media URL sanitization.
- Config hygiene: startup env validation; redact sensitive logs.

ETA: 1 day.

---

### Milestone 4 — Testing
- Backend unit tests: audience resolver; phone normalization; follow‑up scheduling math; PDF metadata; S3 presign (mocked).
- Backend integration tests: JWT login; tenants/customers; promotions dispatcher (no‑op); appointment→follow‑up hooks; reports run/list.
- Frontend tests (Vitest/RTL): auth flow; settings save; customers import; promotions wizard with WS progress.

ETA: 2 days total (incremental).

---

### Milestone 5 — Packaging & Deployment
- Dockerfiles: backend (Uvicorn) and frontend (build → Nginx or Vite preview for demo); `.dockerignore`.
- docker‑compose (dev/demo): `mongo`, `backend`, `admin_ui`; shared network; env files.
- Optional CI: lint/test/build on PR; image builds on main.

Acceptance:
- `docker compose up` starts Mongo + API + Admin UI; health checks OK; no‑op external sends.

ETA: 1–2 days.

---

### Milestone 6 — Documentation & Handover
- README updates:
  - Backend run, feature flags, scheduler notes; `.env` template.
  - Admin UI run; `.env.development` with `VITE_API_BASE`.
  - Sample CSV and HTTP/Postman collection; WS testing guide.
- Ops runbook: enabling `TWILIO_ENABLED`, `SMTP_ENABLED`, `S3_ENABLED`; verifying schedulers; troubleshooting.

ETA: 0.5–1 day.

---

### Environment & Flags (dev defaults)
- Auth/JWT: `ADMIN_DEFAULT_USER`, `ADMIN_DEFAULT_PASS`, `JWT_SECRET`, `JWT_EXP_MINUTES`.
- Mongo: `MONGO_URI`.
- CORS: `CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173`.
- Scheduler: `SCHEDULER_ENABLED=true`, `DEFAULT_TZ=Asia/Kolkata`.
- Messaging: `TWILIO_ENABLED=false`, `SMTP_ENABLED=false`.
- S3: `S3_ENABLED=false`, `AWS_*`, `REPORTS_BUCKET`, `REPORTS_PREFIX`.
- Promotions throttle: `PROMO_BATCH_SIZE`, `PROMO_RPS`.

---

### Immediate Next Actions (next 24–48h)
- Frontend:
  - Implement Customers page (list/search/pagination, upsert dialog, CSV import wizard) bound to current endpoints.
  - Start Promotions pages (list/create/detail) and wire WS progress.
- Backend:
  - Add optional promotions cancel API (if requested) and small validation improvements.

If you want this plan adjusted (e.g., prioritize a specific Admin page first or add a cancel promotion API immediately), tell me and I’ll reshuffle the order accordingly.