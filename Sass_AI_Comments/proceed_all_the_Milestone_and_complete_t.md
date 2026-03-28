### Execution Plan to Complete Appointments End‑to‑End

#### Milestone 1 — Booking core (backend)
- Validations (create/reschedule):
  - Enforce channel horizons from tenant settings: `whatsapp_max_days` (default 3) vs `admin_max_days` (default 30).
  - Enforce lead‑time/buffer: block bookings before `now + buffer_minutes` (effective timezone) and no past bookings.
  - Enforce slot grid alignment to effective duration (per‑professional override → tenant default).
- Atomicity & indexing:
  - Ensure `{tenant, professional_id, start}` index for overlaps/lists.
  - Implement atomic conflict prevention (only one booking can occupy the same slot).
- Tests:
  - Unit and API: horizon clamp, buffer/no‑past, grid alignment, and concurrency race where only one booking can succeed.

Deliverables:
- Updated booking/reschedule logic with all validations.
- Index migration (idempotent) for `{tenant, professional_id, start}`.
- Test suite covering validations and atomicity.

Acceptance:
- Double bookings prevented, invalid requests clearly rejected, tests pass.

---

#### Milestone 2 — Holds API (WhatsApp safety)
- Endpoints:
  - `POST /v1/tenants/{tenant}/appointments/hold` (default TTL 5 minutes), `DELETE /v1/tenants/{tenant}/appointments/hold/{id}`.
- Behavior:
  - Validate slot validity, horizon, buffer, grid alignment; create hold with TTL index; idempotent behavior.
  - Booking may reference an active hold to finalize.
- Tests:
  - Hold lifecycle, TTL expiry, race between a hold and a direct booking.

Deliverables:
- Holds collection with TTL, endpoints, and tests.

Acceptance:
- Holds prevent double‑booking during WhatsApp confirmation; TTL expiration releases slots reliably.

---

#### Milestone 3 — Professionals CRUD (schedules/overrides) & validation
- Model:
  - Overrides: `slot_duration_minutes (5–120)`, `buffer_minutes (0–240)`, `capacity (≥1)`, optional `timezone` (IANA).
  - Schedules: `weekly[]` (weekday + `HH:mm` start/end), `special_dates[]` (YYYY‑MM‑DD + `HH:mm` start/end), `exceptions[]` (blackouts).
- Endpoints:
  - `POST /professionals`, `GET /professionals/full`, `PATCH /professionals/{id}`.
- Validation:
  - 24‑hour `HH:mm`, `start < end`, clamp ranges, IANA TZ validation, dedupe/merge overlaps with precise error messages.
- Indexes:
  - Unique `{tenant, professional_id}`, lookup `{tenant, name}`.
- Tests:
  - CRUD round‑trip and invalid schedule/override inputs.

Deliverables:
- Storage schema, CRUD endpoints, validation helpers, tests.

Acceptance:
- Only valid schedules/overrides persist; error messages are clear.

---

#### Milestone 4 — Availability engine consumes schedules
- Effective values:
  - Resolve `slot_duration_minutes`, `buffer_minutes`, `capacity`, `timezone` per professional (override → tenant default).
- Generation:
  - Expand weekly + special_dates across `[from,to]` in effective timezone; apply `exceptions` and `now + buffer` filters.
  - Compute `remaining = capacity − overlapping non‑canceled appointments`; optional 30–60s micro‑cache.
- Tests:
  - Weekly/special/exceptions, DST boundary days, buffer/horizon clamps, capacity overlap math.

Deliverables:
- Updated availability endpoint using persisted schedules and overrides.

Acceptance:
- Availability reflects schedules, exceptions, capacity and timezone accurately.

---

#### Milestone 5 — Admin UI: Settings → Appointments
- UI controls:
  - Switches: `appointments.enabled`, `appointments.whatsapp_enabled`.
  - Inputs: `slot_duration_minutes` (5–120), `buffer_minutes` (0–240), `whatsapp_max_days` (1–7), `admin_max_days` (7–60), `timezone`.
- Behavior:
  - Persist with `updateTenantSettings`; inline validation and success/error toasts.

Deliverables:
- Settings card with form and persistence.

Acceptance:
- Changing settings updates backend and is respected by availability/booking.

---

#### Milestone 6 — Admin UI: Professionals Editor
- Features:
  - Create/edit: name, active, capacity, overrides, timezone.
  - Schedules tab: weekly windows, special dates, exceptions with inline validation.
  - "Preview next 2 weeks" button (calls Availability API before saving).

Deliverables:
- Professionals editor page/dialogs wired to CRUD endpoints.

Acceptance:
- Admins can edit schedules and see accurate previews.

---

#### Milestone 7 — Admin UI: Appointments Page
- Features:
  - Professional picker and quick range chips (Today, Tomorrow, 7d, 30d).
  - Slot cards (start–end, remaining/capacity), Book dialog (customer, channel=admin, notes).
  - Manage table: filters (date, professional, status) and actions (reschedule, cancel, complete) with server validation.

Deliverables:
- Appointments management UI and API integration.

Acceptance:
- Admin can book, reschedule, cancel, and complete appointments end‑to‑end.

---

#### Milestone 8 — WhatsApp Booking (MVP)
- Conversation:
  - Quick replies: Today, Tomorrow, Next 7 days (results clamped to `whatsapp_max_days`).
  - Availability listing (5–8 slots/page) using `channel=whatsapp`; create hold on selection; confirmation; finalize booking; send confirmation message.
  - Cancel/reschedule keywords supported.
- Safety:
  - Holds TTL cleanup and rate‑limits.

Deliverables:
- Bot handlers, message templates, holds integration, and tests.

Acceptance:
- WhatsApp bookings respect horizons/buffers/durations and avoid race conditions.

---

### Cross‑Cutting Requirements
- Security & permissions
  - Enforce `ensure_tenant_scope`, `ensure_tenant_active`, `ensure_module_enabled('salon')`, and relevant capabilities on all endpoints.
  - Server‑side horizons/buffer; audit timeline entries for create/reschedule/cancel/complete; negative tests for unauthorized/forbidden.
- Performance & indexing
  - Validate indexes for overlap and lists, clamp query ranges, paginate availability and appointment lists.
  - Optional short‑TTL cache for availability reads.
- QA & documentation
  - Backend unit/API suites; Frontend QA (Settings, Professionals, Appointments); WhatsApp e2e scripts.
  - Admin guide & API reference (availability, booking, holds, schedules/overrides).
- Rollout
  - Feature flags: `appointments.enabled`, `appointments.whatsapp_enabled`.
  - Staged rollout per tenant; changelog & release notes.

### Timeline (estimate)
- Week 1: Milestone 1 (booking core) + Milestone 2 (holds) with tests.
- Week 2: Milestones 3–4 (professionals CRUD + availability engine) with tests.
- Week 3: Milestones 5–7 (Admin settings/professionals/appointments UI) + QA.
- Week 4: Milestone 8 (WhatsApp flow) + e2e tests + docs and staged rollout.

### Next Action
- Start Milestone 1 now: implement booking validations, `{tenant, professional_id, start}` index, atomic conflict checks, and unit/API tests. I’ll report progress as soon as the booking core is in place.