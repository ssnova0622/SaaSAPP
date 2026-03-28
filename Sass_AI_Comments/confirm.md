### New Plan for “proceed” — Complete Appointments Flow end‑to‑end and stabilize Analytics/AI

#### Goals
- Deliver a production‑ready Appointments feature (Admin + WhatsApp) with configurable slot durations (default 30 min), horizons (WhatsApp vs Admin), TZ‑aware availability, atomic booking, reschedule/cancel, and auditability.
- Finish and harden analytics/AI UIs already in place (Reports/Predictions) with consistent chart UX.

---

### Phase 1 — Finalize Booking Core (Milestone 1)
- Validations and integrity
  - Enforce channel horizons on create/reschedule using tenant settings: `whatsapp_max_days` (default 3) vs `admin_max_days` (default 30).
  - Enforce lead‑time/buffer: `now + buffer_minutes` and “no past” bookings; configurable per tenant/professional.
  - Grid alignment: start times must align to effective slot duration (professional override → tenant default).
- Indexes and performance
  - Ensure `{ tenant, professional_id, start }` index on `appointments` for overlap checks and listing performance.
- Tests
  - Unit/API tests for: horizon, buffer, not‑in‑past, grid alignment, concurrency race (two bookings same slot → only one succeeds).
- Outcome
  - Booking create/reschedule/cancel/complete are safe, atomic, and validated server‑side.

---

### Phase 2 — Holds API (WhatsApp safety)
- API
  - `POST /appointments/hold` (default TTL 5 min): validate slot, horizon, buffer; prevent ghost bookings during confirmation.
  - `DELETE /appointments/hold/{id}`: release hold.
- Storage
  - `appointment_holds` collection with TTL index on `expires_at`.
- Tests
  - Hold lifecycle, TTL expiry, races between hold vs direct booking.
- Outcome
  - WhatsApp flow can reserve a slot during user confirmation, reducing double‑booking.

---

### Phase 3 — Professionals CRUD (Schedules & Overrides)
- Model & validation
  - Overrides: `slot_duration_minutes` (5–120), `buffer_minutes` (0–240), `capacity` (≥1), `timezone` (IANA).
  - Schedules: `weekly[]` windows (weekday + `HH:mm` start/end), `special_dates[]` (YYYY‑MM‑DD + windows), `exceptions[]` (blackouts).
  - Strict validation: 24‑hour times, `start < end`, IANA TZ check, dedupe/merge overlaps.
  - Indexes: unique `{ tenant, professional_id }`, lookup `{ tenant, name }`.
- Endpoints
  - `POST /professionals`, `GET /professionals/full`, `PATCH /professionals/{id}`.
- Tests
  - CRUD round‑trip and validation errors.
- Outcome
  - Schedules and capacity/duration overrides are persisted and tenant‑scoped.

---

### Phase 4 — Availability Engine (Consume Schedules/Overrides)
- Logic
  - Effective values: professional override → tenant defaults.
  - Expand `weekly` + `special_dates` in effective TZ; apply `exceptions` and `now + buffer` filter.
  - Remaining capacity = `capacity − overlapping non‑canceled appointments` (accurate availability).
  - Optional 30–60s micro‑cache for repeated reads.
- Tests
  - Weekly/special/exceptions generation, DST boundary day, buffer/horizon clamp, overlap math.
- Outcome
  - Availability endpoint returns correct, TZ/capacity‑aware slots respecting horizons and buffers.

---

### Phase 5 — Admin UI: Settings → Appointments
- UI
  - Toggles: enable appointments, enable WhatsApp booking.
  - Inputs: slot duration (default 30; allow 5–120), buffer minutes, WhatsApp horizon (1–7), Admin horizon (7–60), timezone.
- Persistence
  - Use existing tenant settings API with inline validation & toasts.
- Outcome
  - Tenant admins can configure horizons, duration, buffer, and timezone.

---

### Phase 6 — Admin UI: Professionals Editor
- UI
  - Create/edit professional: name, active, capacity, overrides, timezone.
  - Schedules tab: weekly windows, special dates, exceptions with client‑side validation.
  - “Preview next 2 weeks” button using the Availability API.
- Outcome
  - Admins can define and preview schedules per professional.

---

### Phase 7 — Admin UI: Appointments Page
- UI
  - Professional picker with range chips (Today, Tomorrow, 7d, 30d).
  - Slot cards: start–end, remaining/capacity, Book dialog (customer info, channel=admin, notes).
  - Manage table: filters (date, professional, status), actions (reschedule via slot picker, cancel, complete).
- Outcome
  - Full Admin booking and management flow.

---

### Phase 8 — WhatsApp Booking (MVP)
- Conversation flow
  - Intents: “Book appointment” → Quick replies: Today, Tomorrow, Next 7 days.
  - Availability fetched with `channel=whatsapp`; clamp to `whatsapp_max_days` (default 3). If user chose 7 days, cap results and show a note.
  - List 5–8 slots; on selection create Hold; confirm; finalize booking; send confirmation.
  - Keywords/links for cancel/reschedule.
- Outcome
  - Low‑friction WhatsApp booking within tenant horizon limits.

---

### Cross‑Cutting: Security, Performance, Rollout
- Guards
  - Enforce tenant scope/active, Salon module, and relevant capabilities for all endpoints.
  - Server‑side horizons and buffers; audit timeline on bookings/reschedules/cancel/completions.
- Performance & indexes
  - Verify DB indexes; clamp ranges; paginate availability and appointment lists.
  - Optional short‑TTL cache for availability reads.
- Rollout
  - Feature flags: `appointments.enabled`, `appointments.whatsapp_enabled`.
  - Staged rollout per tenant after internal QA.

---

### QA & Documentation
- Backend unit/API tests for all validations, DST boundary, concurrency, holds, and CRUD.
- Frontend QA checklists for Settings, Professionals editor, Appointments page, and WhatsApp flows.
- Admin guide: configuring horizons/durations/buffer/timezone, defining schedules, booking flows (Admin/WhatsApp).
- API reference: availability, booking, holds, professionals CRUD.

---

### Timeline (estimate)
- Week 1: Phase 1 (final validations) + Phase 2 (Holds API) with tests.
- Week 2: Phase 3–4 (Professionals CRUD + Availability engine consuming schedules) with tests.
- Week 3: Phase 5–7 (Admin Settings/Professionals/Bookings UI) + QA pass.
- Week 4: Phase 8 (WhatsApp flow) + e2e scripts, docs, and staged rollout.

---

### Acceptance Criteria
- Admin can configure slot duration (default 30), buffer, horizons; availability updates immediately.
- Availability is TZ‑aware and capacity‑accurate; WhatsApp users see/book only within WhatsApp horizon; Admin up to Admin horizon.
- Booking is atomic; reschedule/cancel validated; holds prevent double‑booking during confirmation.
- Admin UI provides full creation/management flows; WhatsApp booking works within tenant limits.
- Analytics/AI pages retain consistent chart UX (type selector, legend, axes) and remain functional throughout.
