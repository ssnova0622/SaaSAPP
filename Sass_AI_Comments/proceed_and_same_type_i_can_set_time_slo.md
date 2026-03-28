### Consolidated Plan for the Issue

This plan covers both parts of your request:
1) Unified chart-type dropdown (Line, Bar, Pie, Area) across analytics pages.
2) Appointment time-slot selection with different horizons for WhatsApp users vs Admin, including support for weekly/monthly availability.

---

### Part A — Unified Chart-Type Dropdown (Line, Bar, Pie, Area)

#### A1) Shared types and toolbar
- Add a shared `ChartType` union: `'line' | 'area' | 'bar' | 'pie'`.
- Enhance `ChartToolbar` to always show these 4 options and support:
  - `disabledValues?: string[]` to gray out non-applicable types with a tooltip (e.g., Pie for time-series).
  - `persistKey?: string` to save selection (localStorage) per tab/page.
  - Auto-coerce to a valid type if the persisted value is disabled.

#### A2) Chart components support
- Line/Area: use current `LineChart` with `area` flag; include legend and X/Y labels.
- Bar:
  - Time-series: vertical bars (`BarChartVertical`) with X=Date, Y=Value.
  - Categorical: horizontal bars (`BarChartHorizontal`) with X=Count, Y=Category/Status. Optional orientation toggle.
- Pie: extend donut chart to `pie` mode (no inner hole) with legend; used for categorical datasets (Status, Categories).

#### A3) Per-tab rules and UX
- Reports → Sales, Customers (time-series): enable Line, Area, Bar; disable Pie with tooltip “Not applicable for time‑series”.
- Reports → Status, Categories (categorical totals): enable Bar and Pie; disable Line/Area with tooltip “Not meaningful for categorical totals”.
- AI → Predictions → Sales forecast (time‑series): enable Line, Area, Bar; disable Pie.

#### A4) Persistence and validation
- Persist selection per tab: `reports.salesChart`, `reports.statusChart`, `reports.catsChart`, `reports.custChart`, `ai.salesForecastChart`.
- On mount, if stored type is disabled, switch to the first valid fallback (Line → Area → Bar → Pie) and persist silently.

#### A5) Accessibility and consistency
- Legends on all charts; X/Y labels on Line/Area/Bar; role/aria-label on SVGs.
- Shared color palette from `SERIES_COLORS` for consistent series/slice colors.

#### A6) Acceptance criteria
- Every analytics tab shows the same dropdown with Line/Bar/Pie/Area.
- Non-applicable types are disabled with a tooltip and never render invalid charts.
- Selection persists per tab and is auto-corrected if incompatible.
- Legends and axis labels are present and correct.

---

### Part B — Appointment Time Slots (WhatsApp vs Admin Horizons)

#### B1) Requirements recap
- WhatsApp users: can select Today/Tomorrow and (optionally) up to 3 days ahead. You also mentioned “7 days” — we’ll clarify below.
- Admin users: can assign appointments up to 30 days ahead.
- Professionals (e.g., doctors) may be available weekly or monthly (e.g., once a week or once a month). Slots must respect availability and capacity.

#### B2) Tenant settings (backend)
- Extend tenant settings with channel-specific horizons and feature flags:
  - `appointments.enabled: boolean`
  - `appointments.whatsapp_enabled: boolean`
  - `appointments.user_max_days: number` (default 3)
  - `appointments.whatsapp_max_days: number` (default 3)
  - `appointments.admin_max_days: number` (default 30)
  - `appointments.timezone: string` (defaults to tenant tz)
  - Defaults applied if missing; editable from Admin Settings.

#### B3) Professional availability model
- Collection: `professionals_availability` (per tenant, per professional):
  - `weekly`: array of windows (weekday, start_time, end_time), e.g., Mon 10:00–13:00, 30‑min slots.
  - `monthly`: rules optionally supported:
    - Recurrence options: `nth_weekday` (e.g., 1st Saturday) OR `dates[]` (specific YYYY‑MM‑DD occurrences).
  - `slot_duration_minutes` (e.g., 15/30/60), `buffer_minutes` (prep time), `capacity` (1 for one‑on‑one; >1 allowed if group).
  - `exceptions`: date ranges or specific datetimes (blackouts/overrides).
  - `timezone` (optional override per professional).

#### B4) Availability computation API
- `GET /v1/tenants/{tenant}/professionals/{prof_id}/availability`
  - Query: `from=YYYY-MM-DD`, `to=YYYY-MM-DD`, `channel=whatsapp|admin`.
  - Server clamps `to` within `[from, from + channel_max_days]` for the channel (e.g., WhatsApp 3, Admin 30).
  - Returns discrete slot list with `start`, `end`, `capacity`, `remaining`, `bookable: boolean`.
  - Excludes past times and applies buffer from “now”. Timezone‑aware.

#### B5) Booking API
- `POST /v1/tenants/{tenant}/appointments`
  - Body: `{ professional_id, start, end, channel, customer, notes? }`.
  - Validates slot, ensures within channel horizon, and decrements capacity atomically.
  - Optional `POST /hold` to reserve a slot for 2–5 minutes during confirmation (esp. WhatsApp flows); expired holds auto‑release.
  - Admin path bypasses WhatsApp horizon and uses `admin_max_days`.

#### B6) Admin UI changes (Appointments page)
- Filters and quick range chips: Today, Tomorrow, 7 days, 30 days.
- Professional picker → shows calendar/slot list within chosen range, honoring tenant settings and professional availability.
- Slot detail shows remaining capacity and duration.
- Settings page adds controls to configure appointment horizons and enable WhatsApp booking.
- Availability editor: forms to enter weekly windows, monthly rules, one‑off dates, exceptions, slot duration, buffer, capacity.

#### B7) WhatsApp flow
- Quick replies: Today, Tomorrow, Next 7 days.
  - If `whatsapp_max_days = 3`, still accept “Next 7 days” intent but cap results to +3 days and show a note (“Showing up to 3 days of slots”).
- Slot list paginated (5–8 options per message) with “More” navigation.
- Confirmation message shows professional, date, time, and policy. On confirm, finalize booking.

#### B8) Validation and edge cases
- Timezone boundaries (midnight, daylight saving) handled server-side.
- No booking in the past; apply minimum lead time if desired (e.g., 2 hours from now).
- Prevent double booking via atomic updates or unique constraints on (professional_id, start_time, tenant) + capacity decrement.
- Allow reschedule/cancel flows with policy checks.

#### B9) Security and permissions
- Capabilities: `appointments.view`, `appointments.manage`, `appointments.book_admin` (for 30‑day scheduling).
- WhatsApp booking gated by `appointments.whatsapp_enabled` and tenant module enablement.

#### B10) Testing
- Unit tests for availability generation (weekly, monthly, one‑off), exceptions, clamping to horizons, and buffer logic.
- API tests for each channel horizon, holds expiration, and booking conflicts.
- UI QA: Admin 30‑day view, WhatsApp 3‑day cap, monthly clinics rendering.

#### B11) Timeline
- Week 1: Backend settings + availability generation + read API (availability).
- Week 2: Booking API + Admin UI slot explorer + Settings controls.
- Week 3: WhatsApp flow + holds + QA and docs.

#### B12) Open questions for your confirmation
- WhatsApp/user limit: strictly 3 days or allow 7 days? (Your message mentioned both.)
  - Proposal: keep `whatsapp_max_days=3` but allow the “Next 7 days” button while capping results to 3 days with an explanatory note.
- Which roles besides Admin should get 30‑day scheduling (e.g., Manager)?
- Default slot duration (30 minutes?) and default weekly hours if not configured?
- Monthly rule preference: “Nth weekday” (e.g., 1st Saturday) vs explicit list of dates?

---

### Next steps
- If this plan looks good, please confirm the open questions (especially the WhatsApp 3‑day vs 7‑day behavior). Upon confirmation, I’ll implement:
  1) The unified chart dropdown with the four chart types in Reports and AI screens.
  2) The backend availability/booking settings and APIs, followed by the Admin UI slot explorer and WhatsApp integration.