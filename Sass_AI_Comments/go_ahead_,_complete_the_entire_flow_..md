### Objective
Complete the full Appointments flow (Admin + WhatsApp) end‑to‑end, and finalize the analytics/AI UX. This includes: robust availability, booking/reschedule/cancel, per‑professional schedules and overrides, admin settings and editors, WhatsApp booking with holds, permissions, tests, and rollout.

### Scope Overview
- Backend
  - Professionals model (schedules + overrides) with CRUD and validation
  - Availability (TZ + buffer + horizon + capacity) [foundation done]
  - Appointments booking APIs (create/list/reschedule/cancel) with atomic capacity handling
  - Optional holds API for WhatsApp
  - Indexes, guards, and audit fields
- Admin UI (tenant)
  - Settings → Appointments card (slot duration, horizons, buffer, timezone, WhatsApp toggle)
  - Professionals editor (weekly windows, special dates, exceptions, overrides, preview)
  - Appointments page (slot explorer + booking + manage list with reschedule/cancel)
- WhatsApp flow (tenant‑scoped)
  - Quick replies (Today/Tomorrow/Next 7 days), availability listing (capped to WhatsApp horizon), slot hold, confirm booking, confirmation message
- QA/Tests and rollout
  - Unit/API tests (backend), manual QA scenarios (UI + WhatsApp), performance safety (indexes), and staged rollout behind flags

---
### Data Model & Settings
- Tenant settings (appointments)
  - `enabled: boolean` (default false)
  - `whatsapp_enabled: boolean` (default false)
  - `whatsapp_max_days: number` (default 3; 1–7)
  - `admin_max_days: number` (default 30; 7–60)
  - `slot_duration_minutes: number` (default 30; 5–120)
  - `buffer_minutes: number` (default 0; 0–240)
  - `timezone: string` (IANA; fallback to tenant tz)
- Professionals (tenant‑scoped collection)
  - Core: `professional_id` (slug/uuid), `name`, `active`, `timezone?`
  - Overrides: `slot_duration_minutes?`, `buffer_minutes?`, `capacity?` (≥1)
  - Schedules:
    - `weekly[]`: `{ weekday: 0..6, start: 'HH:mm', end: 'HH:mm' }`
    - `special_dates[]`: `{ date: 'YYYY-MM-DD', start: 'HH:mm', end: 'HH:mm' }`
    - `exceptions[]`: `{ date: 'YYYY-MM-DD', reason? }`
- Appointments (tenant‑scoped collection)
  - `{ id, tenant, professional_id, start: ISO, end: ISO, channel: 'admin'|'whatsapp', customer: { name?, phone, email? }, notes?, status: 'booked'|'canceled'|'completed', created_at, updated_at, created_by?, timeline?: [] }`
- Holds (optional; WhatsApp) — `appointment_holds`
  - `{ id, tenant, professional_id, start, end, customer?, expires_at }` (TTL index)

Indexes:
- `appointments`: `{ tenant, professional_id, start }`
- `holds`: TTL on `expires_at`
- `professionals`: `{ tenant, professional_id }` unique; `{ tenant, name }` for lookups

---
### Backend Endpoints (tenant‑scoped)
- Professionals CRUD (Salon guards)
  - POST `/v1/tenants/{tenant}/professionals` → create with overrides & schedules
  - GET `/v1/tenants/{tenant}/professionals/full` → list with schedules/overrides (filter `active?`)
  - PATCH `/v1/tenants/{tenant}/professionals/{id}` → update overrides/schedules
  - PATCH `/v1/tenants/{tenant}/professionals/{id}/status` → activate/deactivate
- Availability (Phase 1 done; will consume schedules/overrides fully)
  - GET `/v1/tenants/{tenant}/professionals/{id}/availability?from=YYYY-MM-DD&to=YYYY-MM-DD&channel=whatsapp|admin`
    - TZ‑aware; clamps by channel horizon; enforces buffer; expands weekly/special; drops exceptions; computes `remaining` via overlap subtraction
- Booking
  - POST `/v1/tenants/{tenant}/appointments` → validate grid alignment, buffer, horizon, past; atomic capacity check; create timeline entry
  - GET `/v1/tenants/{tenant}/appointments?from&to&professional_id?&status?&page?&size?` → list/manage
  - PATCH `/v1/tenants/{tenant}/appointments/{id}` → reschedule (same validations, atomic) or cancel (frees capacity), complete
- Holds (optional; WhatsApp safety)
  - POST `/v1/tenants/{tenant}/appointments/hold` → create 5‑min hold (validates slot); DELETE to release

Validation (all endpoints):
- Effective duration: professional override → tenant default
- Minimum start: `now + buffer_minutes` (effective TZ)
- Horizon: `whatsapp_max_days` vs `admin_max_days`
- Grid alignment: slot starts align to duration within daily windows; end = start + duration
- Overlap/Capacity: appointment start < end AND end > start; capacity decremented atomically
- TZ/DST: use IANA tz with robust handling (skip nonexistent times)
- Guards: tenant scope/active + Salon module + appropriate capability

---
### Admin UI
- Settings → Appointments card
  - Switches: enable appointments, enable WhatsApp booking
  - Inputs: slot duration (10/15/20/30/45/60 + Custom 5–120), buffer minutes, horizons (WhatsApp/Admin), timezone
  - Save with inline validation and toasts
- Professionals editor
  - List/search professionals; create/edit dialog (name, active, capacity, overrides, timezone)
  - Schedules tab: weekly windows (weekday/start/end), special dates (date/start/end), exceptions (date); client validation; “Preview next 2 weeks” via availability API
- Appointments page
  - Professional picker (autocomplete), chips (Today, Tomorrow, 7d, 30d)
  - Slot list/cards (start–end, remaining/capacity), Book button → booking dialog (customer, channel=admin, notes), confirm
  - Manage table: filters (date, professional, status); actions: reschedule (slot picker), cancel, complete

---
### WhatsApp Booking (Phase 3)
- Conversation flow
  - Intent: “Book appointment” → ask professional (or list top), quick replies: Today, Tomorrow, Next 7 days
  - Call availability with `channel=whatsapp`, clamp to `whatsapp_max_days`; if user chose 7 days but tenant limit is 3, cap and add note
  - Show 5–8 slots per message, add “More” pagination; on selection, create hold; ask to confirm; on confirm, finalize booking and send confirmation
- Safety & cleanup
  - Holds TTL auto‑expire; rate limits; clear error messages
- Notifications
  - Confirmation text with appointment details and keywords/links to cancel/reschedule

---
### Security & Permissions
- Reuse Salon module and capabilities for Phase 1/2 (can split later):
  - `salon.professionals` (manage/view professionals)
  - `salon.appointments` (view/manage appointments)
  - Admin UI routes/component guards mirror these
- Tenant scope and active checks on every request
- Audit trail for bookings: timeline entries (created/rescheduled/canceled/completed) with who/when/channel

---
### Tests & QA
- Backend unit tests
  - Schedule validation (HH:mm, start<end, dedupe), overrides precedence
  - Availability expansion (weekly, special, exceptions), buffer, horizon clamp, DST day
  - Atomic booking (two concurrent requests on same slot → only one succeeds)
  - Reschedule validation; cancel frees capacity
  - Holds TTL expiry behavior
- API tests
  - Guards (scope/active/module/caps), param validation, pagination
- Frontend QA
  - Settings saves; Professionals editor (validation + preview); Appointments booking, reschedule, cancel; availability refresh
  - Error state coverage (no slots, outside horizon, buffer violations)
- WhatsApp scripted QA
  - List → hold → confirm; limited to horizon; “More” pagination; cancel/reschedule flows

---
### Performance & Reliability
- Indexes: `{ tenant, professional_id, start }` on appointments; TTL on holds
- Clamp day ranges and provide pagination for large windows
- Optional short TTL micro‑cache (30–60s) on availability reads to stabilize repeated UI views
- Log failures with clear messages; add metrics for bookings per professional/day

---
### Deployment & Rollout
- Feature flags: `appointments.enabled`, `appointments.whatsapp_enabled`
- Migrations: ensure indexes exist (idempotent) before deploying APIs
- Staged rollout: enable for internal tenant first → selected tenants → broad enablement
- Admin documentation: configuration guide (settings, schedules), booking workflows, WhatsApp flow

---
### Timeline (estimate)
- Week 1
  - Professionals CRUD with schedules/overrides (backend) + validations + indexes
  - Availability engine consumes schedules fully; unit/API tests
- Week 2
  - Booking APIs (create/list/reschedule/cancel) with atomic capacity + tests
  - Admin Settings card (appointments)
- Week 3
  - Professionals editor UI + “Preview next 2 weeks”
  - Appointments page (slot explorer, booking dialog, manage table)
  - Manual QA cycle
- Week 4
  - WhatsApp flow (holds + quick replies + confirmations); e2e test scripts
  - Docs, polish, staged rollout

---
### Acceptance Criteria
- Admin can configure slot duration (default 30), buffer, horizons; availability updates immediately and is TZ‑aware
- Professionals can have weekly/special/exceptions schedules; availability expands correctly; exceptions respected
- Admin can book up to Admin horizon; WhatsApp users can book up to WhatsApp horizon; holds prevent double booking during confirmation
- Reschedule/cancel validated and capacity accurate; audit timeline maintained
- UI flows (settings, professionals, appointments) and WhatsApp flow are stable and clearly validated

### Next Action
I will start with Professionals CRUD (schedules/overrides + validation) and wire them into the availability engine, then implement Booking APIs (atomic) and the Admin UI pieces in the order above. Let me know if you want specific default weekly hours or capacity seeded for new professionals; otherwise defaults will be capacity=1 and no weekly windows (fallback to 09:00–19:00/30m when none configured).