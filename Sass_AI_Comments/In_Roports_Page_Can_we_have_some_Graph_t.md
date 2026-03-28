### Plan: Add interactive graphs to the Reports page

#### Goals
- Give a visual overview of store performance with tenant‑scoped charts (fast, accurate, and easy to drill down).
- Keep security and permissions intact (requires `core.reports`; store data only shown if Store module is enabled).

---
### 1) What graphs we will add (MVP)
- Sales over time (line/area)
  - Metrics: orders count, revenue, units sold per day.
  - Controls: 7/14/30/60/90 days range; tenant timezone aware.
- Orders by status (stacked or horizontal bars)
  - Metrics: counts by `placed/confirmed/picking/ready_for_pickup/out_for_delivery/delivered/canceled` over the selected window.
- Category mix (donut/pie + table)
  - Metrics: revenue and quantity share by product category.
- Customers over time (dual line)
  - Metrics: daily counts of new vs. returning customers (by phone/email key).

Optional (Phase 2)
- AOV (Average Order Value) over time.
- Payment method split (ONLINE vs COD) — bar chart.
- Cancellations over time — line/bar.

---
### 2) Backend APIs (tenant‑scoped)
Add lightweight, cached analytics endpoints under Reports router:
- `GET /v1/tenants/{tenant}/reports/sales_timeseries?days=30&interval=day`
  - Returns per‑day points: `{ date, orders_count, units, revenue }`
- `GET /v1/tenants/{tenant}/reports/orders_by_status?days=30`
  - Returns list: `{ status, count }[]`
- `GET /v1/tenants/{tenant}/reports/category_mix?days=30`
  - Returns list: `{ category, qty, revenue, share_revenue }[]`
- `GET /v1/tenants/{tenant}/reports/customers_timeseries?days=30`
  - Returns per‑day points: `{ date, new_customers, returning_customers }`

Rules & safeguards:
- Guards: `ensure_tenant_scope`, `ensure_tenant_active`, `ensure_module_enabled('store')`, `ensure_capability_enabled('core.reports')`.
- Exclude canceled orders from revenue/units and most counts (keep a dedicated status chart for cancels).
- Params clamped: days ∈ [7, 120].
- Use tenant timezone (from settings `tz`) for day boundaries when grouping.
- Add a simple 5–15 min in‑memory cache per tenant+params to keep responses snappy on repeated views.

---
### 3) Storage aggregations (Mongo)
Add methods to `Storage`:
- `sales_timeseries(tenant, days, interval)` — walk orders in window; aggregate by day; compute revenue from `qty × price_snapshot`.
- `orders_by_status(tenant, days)` — count by `status` among orders in window.
- `category_mix(tenant, days)` — join order items → products → sum by `category` (fallback to `Uncategorized`).
- `customers_timeseries(tenant, days)` — derive new vs returning by checking first‑seen date in `customers` collection or first order per phone; aggregate daily counts.

All outputs rounded to sensible precision and safe when empty (return empty arrays).

---
### 4) Frontend API client
Extend `admin_ui/src/api/reports.tsx` with typed clients:
- `getSalesTimeseries(tenant, { days })`
- `getOrdersByStatus(tenant, { days })`
- `getCategoryMix(tenant, { days })`
- `getCustomersTimeseries(tenant, { days })`

---
### 5) Reports page UI (graphs & filters)
- Convert `Reports` page to a tabbed layout:
  - Summary | Sales | Status | Categories | Customers | (Generated Files)
- Controls on top: chips 7/14/30/60/90 days, and Refresh.
- Charts (lightweight library):
  - Prefer Recharts (small, tree‑shakable) or Chart.js with `react-chartjs-2`.
  - Sales: dual‑axis line/area (orders & revenue), with tooltips.
  - Status: stacked bar with color coding per status.
  - Categories: donut/pie + table; hover shows percentage and revenue.
  - Customers: two lines (new vs returning) over time.
- States: loading spinners, empty messages, inline error alerts.
- Drill‑downs:
  - Click a day → navigate to Orders page pre‑filtered by that date.
  - Click a status → Orders page with that status filter.
  - Click a category → Products page filtered to the category.
- Keep existing “Generated daily reports” list in a dedicated “Generated Files” tab (current table you have).

---
### 6) Permissions & visibility
- The Reports page already requires `core.reports`. We’ll keep it.
- If Store module is disabled for a tenant, show a friendly placeholder instead of store charts.

---
### 7) Performance & correctness
- On the server, cache results per tenant for 5–15 minutes.
- Clamp query ranges and only return necessary fields.
- Use tenant timezone to bucket days to avoid off‑by‑one boundaries.

---
### 8) QA checklist
- Empty data → charts render with “No data” safely.
- Date ranges 7/14/30/60/90 work and match Orders list totals.
- Canceled orders excluded from revenue/unit charts; included in Status chart.
- Multi‑tenant isolation verified; capability/module gating honored.
- Drill‑downs navigate with correct filters.

---
### 9) Timeline
- Day 1: Backend endpoints + Storage aggregations + simple cache.
- Day 2: Frontend charts + filters, tabs, drill‑downs.
- Day 3: QA, polish (colors/labels), optional CSV export per widget, and docs.

---
### 10) Success criteria
- Reports page shows 4 interactive charts + the existing Generated Files tab.
- Loads under ~1s after caching on typical data.
- Filters and clicks provide accurate drill‑downs to Orders/Products.

---
### Decisions for you
- Charting library preference: Recharts vs Chart.js? (Default I’ll use Recharts.)
- Default day range chips: keep 7/14/30/60/90? (We can reduce to 30/60/90 if you prefer.)
- Do you want CSV export buttons per chart in MVP, or add that in Phase 2?

If you approve this plan, I’ll start with the backend endpoints and then wire the charts on the Reports page.