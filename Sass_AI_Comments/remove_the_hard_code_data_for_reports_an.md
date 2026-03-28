### Goal
Replace hardcoded report content with real data fetched per-tenant from your Mongo collections, so daily reports reflect actual appointments, professionals, customers, and computed totals.

### High-level approach
- Introduce a data aggregation layer that builds a daily snapshot from Mongo for a given `tenant` and `day`.
- Refactor PDF builder to accept this snapshot (instead of synthesizing rows and totals itself).
- Keep storage and delivery mechanics (S3/local; download endpoint) unchanged.

### Detailed plan
1. Data model and indexing
- Appointments collection
  - Ensure each appointment stores: `tenant`, `professional`, `customer_name`, `customer_phone`, `price`, `status` ('booked'|'canceled'|...), and an ISO `date` (YYYY-MM-DD) and `time` (HH:MM) or a single datetime.
  - Add indexes (if missing):
    - `(tenant, date)` for daily listing
    - `(tenant, date, professional)` for per-pro reporting (optional)
- Professionals & Customers
  - Professionals: `(tenant, name)` unique index already present.
  - Customers: `(tenant, phone)` unique index already present.

2. Aggregation API in storage layer
- Add a function in `app/services/storage_mongo.py`:
  - `Storage.get_daily_appointments(tenant: str, day: date) -> List[Dict[str, Any]]`
    - Query `appointments` for the day and tenant.
    - Project needed fields: `time`, `professional`, `customer_name` (fallback resolve via phone), `price`, `status`.
    - Sort by `time` ascending for table display.
  - `Storage.get_daily_totals(tenant: str, day: date) -> Dict[str, Any]`
    - Compute counts and revenue: `appointments_count`, `cancellations_count`, `revenue` (sum of price where status == 'booked').
  - Optional combined helper:
    - `Storage.get_daily_report_snapshot(tenant: str, day: date) -> Dict[str, Any]`:
      - `{ tz, rows: [{ time, professional, customer, price, status }...], totals: { appointments, cancellations, revenue } }`
  - Timezone handling:
    - Fetch tenant settings to obtain `tz`. If appointment times are stored as local strings (e.g., '09:00'), we can use them as-is. If stored as UTC datetimes, convert each to local time using `tz`.

3. Refactor PDF builder to consume snapshot
- Update `app/services/reports.py`:
  - Change signature: `build_daily_report(tenant: str, day: date, snapshot: Dict[str, Any]) -> Tuple[str, bytes]`
  - Remove hardcoded `data` rows and `totals` line.
  - Build table rows from `snapshot['rows']` with headers `Time | Professional | Customer | Price | Status`.
  - Compute Totals text from `snapshot['totals']`.
  - Use tenant’s timezone string from snapshot for the “Timezone” line (instead of `DEFAULT_TZ`).
- Backward-compatible wrapper (optional during transition):
  - If you want to keep existing callers temporarily, add a small wrapper that fetches the snapshot and calls the new builder.

4. Wire snapshot into report generation
- Update `app/services/reports_store.py`:
  - In `generate_and_store_report(tenant, day)`:
    - Fetch snapshot via storage: `snapshot = Storage.get_daily_report_snapshot(tenant, day)`.
    - Call: `fname, pdf = build_daily_report(tenant, day, snapshot)`.
    - Persist as today (S3/local + `reports` collection), unchanged.

5. No changes needed in download/list endpoints or Admin UI
- `GET /v1/tenants/{tenant}/reports/daily` and `GET /v1/tenants/{tenant}/reports/{date}/download` remain the same.
- Admin UI `Reports/Index.tsx` and `reportDownloadUrl()` remain unchanged.

6. Timezone and date boundaries
- If appointments are stored as UTC datetimes, daily slicing must respect the tenant’s tz:
  - Compute `[start, end)` window in UTC for the given `day` at tenant tz and query using that range.
  - If you currently store separate `date` and `time` strings (local), slice by `date` directly.
- Ensure the PDF header shows the tenant tz. If tz missing, default to `Asia/Kolkata` (existing default) but prefer tenant-specific.

7. Edge cases and formatting
- If no appointments:
  - Show header and a table with just the header row and a single “No appointments” line, and totals all zero.
- Status normalization:
  - Map internal status codes to display strings (e.g., 'booked', 'canceled').
- Price formatting:
  - Format to two decimals, currency can remain generic unless tenant currency exists.

8. Performance & safety
- Query projections should include only necessary fields.
- Add `(tenant, date)` index on `appointments` if not present to keep daily queries fast.
- Guard nulls: if a professional or customer was deleted, still render the row with graceful fallbacks.

9. Testing & verification
- Unit-level:
  - Snapshot builder returns correct rows and totals for a seeded day with mixed statuses.
  - Timezone conversion yields expected `time` values when using UTC stored datetimes.
- Integration:
  - Generate and store a report; verify `reports` doc is persisted with correct `storage` and `date`.
  - Download endpoint streams the generated PDF.
- Manual E2E:
  - Create a few appointments for a tenant on a date with varied statuses and prices.
  - Generate report for that date; open via Admin UI and check rows and totals match DB.

10. Migration/rollout
- This change is backward compatible for existing report listing and download.
- If you need to regenerate historical reports, run the generate endpoint for previous dates.

### Minimal code touchpoints
- storage_mongo.py: add `get_daily_appointments`, `get_daily_totals`, `get_daily_report_snapshot`.
- reports.py: refactor `build_daily_report` to accept `snapshot` and remove hardcoded `data`/`totals`.
- reports_store.py: call new storage functions and pass snapshot into `build_daily_report`.
- Optional: add appointment index in `app/services/db.py` for `(tenant, date)`.

### Optional enhancements (later)
- Add filters to Admin UI report list by date range.
- Add revenue by professional section or summary chart.
- Include cancellations detail page link from the PDF/table (requires extra endpoints).

If you confirm, I’ll implement steps 2–4 and add the `(tenant, date)` index, then verify with a seeded dataset. Would you like the report to include only “booked” rows or also show “canceled” rows with a different style?