### What these AI summary numbers mean
These four labels are the header cards on the AI — Predictions page (Summary tab). They give a quick, tenant‑scoped snapshot of inventory risk and cart activity. Here’s what each one means and how it’s computed.

#### Low‑stock SKUs — 3
- What it is: Count of SKUs where the suggested reorder quantity is greater than 0.
- How it’s computed:
  - We look at your non‑canceled orders for the last N days (N is the page’s day range chip: 30/60/90).
  - Compute `daily_demand = total_sold_qty / N` for each SKU.
  - Look up current `available_qty` in inventory.
  - With default lead_time=3 days and safety_days=2, target stock = `daily_demand * (lead_time + safety_days)`.
  - `suggested_reorder_qty = max(0, target_stock - available_qty)`.
  - If suggested_reorder_qty > 0, that SKU is counted here.
- Where this comes from in code: `Storage.forecast_low_stock(...)`; the summary uses this list and counts SKUs with `suggested_reorder_qty > 0`.
- What to do: Open the Low‑stock tab (or the Low‑stock panel on Products) and use “Set Inventory” to replenish those SKUs.

#### Predicted OOS ≤ 7d — 3
- What it is: Count of SKUs predicted to run out of stock within 7 days if current sales pace continues.
- How it’s computed:
  - Using the same daily_demand and inventory, we compute `days_to_stockout = available_qty / daily_demand`.
  - If `days_to_stockout ≤ 7`, the SKU is counted here.
- Caveats: If a SKU has effectively zero recent demand, we consider its `days_to_stockout` as ∞ and it won’t be counted.
- What to do: Prioritize reordering these items first.

#### Abandoned carts (24h) — 2
- What it is: Approximate number of carts updated in the last 24 hours that have items in them (a proxy for carts that didn’t convert yet).
- How it’s computed:
  - Counts cart documents with `updated_at ≥ now-24h` and a non‑empty `items` array.
  - It doesn’t try to match carts to subsequent orders in this MVP; it’s a quick opportunity indicator.
- Where to dig deeper: Open the Cart recovery tab. It shows the total for your selected window (6–72h) and the top SKUs appearing in those carts so you can run recoveries (e.g., WhatsApp reminders or offers).
- What to do: Consider sending a timed WhatsApp reminder with a link to resume checkout; keep stock ready for these SKUs.

#### Anomaly alerts — 0
- What it is: Placeholder for upcoming anomaly detection (e.g., sudden demand spikes/drops, unusual discounting, abnormal cancel rate).
- Current behavior: Always 0 in the MVP; no anomalies are computed yet.
- Roadmap: Will flag SKUs or metrics with z‑score/outlier detection and show details in a dedicated tab.

### Things that affect these numbers
- Date range (30/60/90 days): Impacts Low‑stock and Predicted OOS figures by changing the demand window.
- Lead and safety days: Defaults are 3 and 2 in the backend for the forecast; the Summary uses those defaults. The Low‑stock tab may allow parameterized calls (e.g., different lead time) depending on your UI setup.
- Cancellations: Canceled orders are excluded from demand.
- Variants: Variant SKUs are included and shown with attribute labels (e.g., “Shirt (color: Red, size: M)”).

### How to act on the summary
- Click into tabs:
  - Low‑stock: See each SKU’s `available_qty`, `daily_demand`, `days_to_stockout`, and `suggested_reorder_qty`. Use “Set Inventory” to update stock.
  - Cart recovery: Choose a time window, see the total abandoned carts and top SKUs; plan outreach.
  - Top sellers and Sales forecast: Identify movers and plan procurement and promotions.

### Guardrails and access
- Visibility requires the AI Predictions capability and, for store‑related widgets, the Store module. Super Admin can enable the “Predictions screen” toggle for each tenant in Settings → AI Features.

If you’d like, I can tailor the thresholds (e.g., change the default 7‑day OOS cutoff), or add an alert when `days_to_stockout` falls below your supplier lead time.