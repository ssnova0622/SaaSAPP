### Which 3 SKUs are “Predicted OOS ≤ 7d”?
That number comes from the same Low‑stock forecast used elsewhere. To see exactly which SKUs they are, use either the UI (quickest) or the API.

#### See them in the UI (no code)
- Go to AI — Predictions → Summary tab (where you saw the card).
- Switch to the Low‑stock tab.
- Make sure the day‑range (30/60/90) matches the Summary chips you were using.
- Sort the table by “Days to SO” ascending or just scan for rows with `Days to SO ≤ 7`.
  - Those rows are the SKUs counted in the card. Variant SKUs show attributes (e.g., `T‑Shirt (color: Red, size: M)`).

Tip: The header card uses default lead/safety buffers (lead_time=3, safety_days=2). If you change those in the Low‑stock view, the list may differ from the card’s count.

#### Get the list via API
- Call the low‑stock forecast endpoint with the same day‑range as the Summary (default 30) and default buffers:
```
GET /v1/tenants/{tenant}/ai/forecast_low_stock?days=30&lead_time=3&safety_days=2&top=200
```
- Filter the response to items with `days_to_stockout <= 7`. Those SKUs are the ones behind the “Predicted OOS ≤ 7d” count.

Example (pseudo‑code):
```js
const res = await api.get(`/v1/tenants/${tenant}/ai/forecast_low_stock`, { params: { days: 30, lead_time: 3, safety_days: 2, top: 200 }})
const oosSoon = res.data.items.filter(x => Number(x.days_to_stockout) <= 7)
// oosSoon is the exact list of SKUs counted by the card
```

#### Why counts can differ from expectations
- Day‑range mismatch: The Summary chips (30/60/90) change the demand window; use the same value in the Low‑stock tab/API.
- Buffer assumptions: The card uses lead_time=3 and safety_days=2. Using different values changes the threshold.
- Zero‑demand SKUs: If recent demand is ~0, `days_to_stockout` is treated as ∞ and they won’t be counted.

If you’d like, I can add a small UX tweak: clicking the “Predicted OOS ≤ 7d” card could jump straight to the Low‑stock tab with a pre‑applied `≤ 7 days` filter.