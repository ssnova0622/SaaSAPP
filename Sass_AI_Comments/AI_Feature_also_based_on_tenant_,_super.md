### Plan: Tenant‑scoped AI Predictions screen (Super Admin controlled)

#### Goals
- Provide a single “AI — Predictions” screen that aggregates actionable AI insights (low‑stock forecast, sales forecast, top sellers, abandoned carts, anomalies) for a tenant.
- Visibility controlled by Super Admin; tenants can only see the page after the Super Admin enables it for their tenant.
- Ship it as a separate Core nav item so it’s not tied to the Store module only (but Store‑specific widgets respect module/capability gates).

---
### 1) Access control and feature flags
- Capability registry
  - Add module: `ai` (Core), capability: `ai.predictions`.
  - Optional split: `ai.predictions.view` (tenant users) and `ai.predictions.manage` (Super Admin only) if you want finer control later.
- Tenant flag
  - Extend tenant settings `ai.predictions_enabled: boolean` (defaults to false).
  - Only Super Admin can set this flag in Settings → AI Features (already have AI flags card; we’ll add this toggle).
- Gating rules (frontend and backend)
  - Frontend nav item “AI — Predictions” is visible if:
    - User is Super Admin (to preview) OR (tenant.settings.ai.predictions_enabled === true AND user has capability `ai.predictions`).
  - Each widget additionally checks relevant module/capability:
    - Store widgets (low‑stock, top sellers, cart/checkout insights) require `store` module + `store.catalog`/`store.orders` capabilities.
  - Backend endpoints are tenant‑scoped and require `ensure_tenant_scope`, `ensure_tenant_active`, and capability `ai.predictions`.

---
### 2) Backend API surface
- Summary (cards for page header)
  - `GET /v1/tenants/{tenant}/ai/predictions/summary`
    - Returns: date range used, computed at timestamp, and counters like { low_stock_count, predicted_oos_next_7d, top_seller_skus, abandoned_carts_24h, anomaly_alerts }
- Details (widgets)
  - Low stock forecast (already exists): `GET /ai/forecast_low_stock` (reuse)
  - Sales forecast (MVP)
    - `GET /v1/tenants/{tenant}/ai/sales_forecast?days=30&horizon=14`
    - Output per‑day demand forecast and total expected revenue (simple moving average or Prophet later).
  - Top sellers
    - `GET /v1/tenants/{tenant}/ai/top_sellers?days=30&top=20` → aggregates orders by SKU, joins product names.
  - Cart recovery insights
    - `GET /v1/tenants/{tenant}/ai/cart_recovery?window_hours=24` → count of carts not converted, and top 5 SKUs in abandoned carts.
  - Anomaly detection (MVP)
    - `GET /v1/tenants/{tenant}/ai/anomalies?days=30` → items with spikes/drops or outlier discounts; simple z‑score first.
- Performance
  - Implement cheap, on‑demand queries first with short in‑memory/Redis cache (TTL 5–15 min) keyed by tenant + params.
  - Later: batch precompute jobs (see §4) and cache results in a collection.
- Multi‑tenant safety
  - All queries filter by `tenant`; no cross‑tenant reads. Existing guards apply.

---
### 3) Data contracts and responses
- Common response envelope for detail endpoints:
```
{
  "items": [...],
  "params": { ... },
  "generated_at": "ISO timestamp",
  "tenant": "<id>"
}
```
- Sales forecast `items`: [{ date, demand_units, revenue_estimate }]
- Top sellers `items`: [{ sku, name, qty, revenue }]
- Cart recovery `items`: { total_abandoned, top_skus: [{ sku, name, qty }], sample_carts?: [...] }
- Anomalies `items`: [{ type: "price|demand|cancel_rate", sku?, name?, score, details }]

---
### 4) Batch jobs (Phase 2, optional for MVP)
- Nightly/hourly aggregations to collections:
  - `ai_product_stats`: per‑SKU totals (views, add_to_cart, orders, qty, revenue)
  - `ai_sales_forecast`: per‑day forecasts for the next horizon
  - `ai_abandonments`: rolling windows of abandoned carts and top SKUs
  - `ai_anomalies`: flagged events with scores
- Jobs run per tenant using existing APScheduler in `app/main.py`.

---
### 5) Frontend — new Predictions page
- Route and navigation
  - Route: `/ai/predictions` under Core.
  - Nav item label “AI — Predictions”; visible per gating rules in §1.
- Layout
  - Header controls: tenant switch (for Super Admin), date range (7/14/30/90d), category filter (optional), Refresh.
  - Summary cards row (uses `/ai/predictions/summary`).
  - Tabs or stacked panels:
    - Low Stock (table): reuse current forecast with actions (Set Inventory).
    - Sales Forecast (chart): area/line chart for predicted demand/revenue.
    - Top Sellers (table): with links to Products and Orders.
    - Cart Recovery (table): counts and top abandoned SKUs with link to Carts.
    - Anomalies (table): highlight severity with tooltips.
- Client API
  - Extend `admin_ui/src/api/ai.ts` with new typed clients for the endpoints in §2.
- UX
  - All widgets: loading/error/empty states, CSV export per widget, pagination where needed.

---
### 6) Settings and enabling flow
- Settings → AI Features card: add switch “Predictions screen” (writes `ai.predictions_enabled`). Only Super Admin sees/edits.
- When off: the nav item is hidden for tenant admins/staff; Super Admin can still open it for QA (label badge “Disabled for tenant”).
- Optional: nav_config can rename the page per tenant (e.g., “AI — Insights”).

---
### 7) Security and compliance
- All endpoints require JWT + tenant scope + `ai.predictions` capability.
- PII: avoid exposing raw customer details in predictions; aggregate metrics only.
- Rate limits: simple per‑tenant throttling for heavy endpoints; caching enabled.

---
### 8) Acceptance criteria
- Super Admin can enable Predictions for a tenant in Settings.
- After enabling, tenant admin with `ai.predictions` can see `/ai/predictions` and all eligible widgets.
- Widgets only surface data when required Store capabilities exist; otherwise show helpful placeholders.
- Low‑stock table matches existing endpoint outputs and actions work.
- API and UI are tenant‑scoped and multi‑tenant safe.

---
### 9) Rollout plan & timeline
- Iteration 1 (2–3 days)
  - Add capability `ai.predictions` and tenant flag.
  - Backend: `summary`, `top_sellers` (simple aggregate), wire to guards + caching.
  - Frontend: new page, nav gating, summary cards, Top Sellers panel.
- Iteration 2 (2–3 days)
  - Sales Forecast endpoint (moving average) + chart; integrate date range.
  - Cart Recovery insights (based on carts/order deltas).
- Iteration 3 (2 days)
  - Integrate existing Low‑stock widget into Predictions page.
  - Anomalies MVP (z‑score spike/drop) + table.
- Iteration 4 (1–2 days)
  - CSV export, polish, docs, feature flag QA.

---
### 10) Deliverables
- Backend: new AI endpoints (`summary`, `top_sellers`, `sales_forecast`, `cart_recovery`, `anomalies`) with tests and guards.
- Frontend: `/ai/predictions` page, components, and API client; nav gating and Settings toggle.
- Docs: Admin guide for enabling and interpreting insights; API reference.

If this plan looks good, I can start with Iteration 1: add the capability/flag, implement `summary` and `top_sellers`, and scaffold the Predictions page with gated navigation.