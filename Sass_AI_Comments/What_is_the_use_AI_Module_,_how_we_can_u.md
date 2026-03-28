### What the AI module is
Your project has two AI parts:

1) Appointment recommendations (for clinic/salon)
- File: `app/services/ai.py`
- Class: `AIPredictor`
- Purpose: Suggest the best appointment time slots based on availability and past booking patterns.
- Output: Top N recommended time labels (e.g., `['10:30', '11:00', '12:30']`) and a human‑readable rationale.

2) Retail/store predictions (for tenants using the Store module)
- File: `app/routers/ai.py`
- Endpoints (guarded by capability `ai.predictions` and module `store`):
  - `GET /tenants/{tenant}/ai/forecast_low_stock` → low‑stock forecast and reorder suggestions
  - `GET /tenants/{tenant}/ai/top_sellers` → best sellers
  - `GET /tenants/{tenant}/ai/sales_forecast` → demand forecast
  - `GET /tenants/{tenant}/ai/cart_recovery` → abandoned cart insights
  - `GET /tenants/{tenant}/ai/predictions/summary` → overall summary
- UI client: `admin_ui/src/api/ai.ts` exposes typed helpers for the routes above.

### How to utilize it for Clinic and Salon tenants
For clinic and salon, the main benefit is smarter appointment booking. Use `AIPredictor` to surface “Recommended slots” at the top of every booking flow (web admin, customer portal, and WhatsApp bot).

#### A. Add AI recommendations to booking UX
- Where to integrate:
  - WhatsApp booking flow: `app/routers/whatsapp.py` already has timeslot flow helpers (e.g., `_start_timeslot_flow`, `_handle_timeslot_fsm`). Before listing all available times, call `AIPredictor.recommend(...)` and display the top 2–3 options first (as buttons or numbered choices).
  - Web/Admin UI: When receptionist picks a professional/date, fetch recommended times and highlight them.

- What `AIPredictor` returns:
  - `recommend(tenant: str, professional?: str, top_k: int = 3) -> (List[str], str)`
  - Example result: `(['10:30', '11:00', '12:30'], 'Recommended based on availability, spreading load, and near-term convenience.')`

- Example response shape for a simple endpoint you might expose (optional, if you want a clean API):
```json
{
  "recommended": ["10:30", "11:00", "12:30"],
  "rationale": "Recommended based on availability, spreading load, and near-term convenience.",
  "all_available": ["09:30", "10:00", "10:30", "11:00", "11:30", ...]
}
```
You can return this from a new read‑only route like `GET /tenants/{tenant}/ai/recommend_slots?professional=Jane&top=3`, which internally uses `AIPredictor`.

#### B. Embed AI in WhatsApp menus
- Your WhatsApp router supports actions like `core.select_timeslot` in `whatsapp.py`.
- When a user taps “Book a Slot” in WhatsApp, call `AIPredictor.recommend()`:
  - If there are recommended times, render a quick reply list: “Best times: 10:30, 11:00, 12:30. Or type a different time.”
  - Fall back to normal slot listing if none.
- Benefit: Faster conversions and fewer back‑and‑forth messages.

#### C. Staff and resource planning (operational use)
- For salon: identify rush hours across days to schedule more stylists.
- For clinic: see when doctors/rooms are most in demand.
- How: Log bookings with `POST /tenants/{tenant}/events` and later compute summaries or feed them into a dashboard. The `post_event` endpoint already exists for flexible analytics.

### Concrete workflows per tenant type
- Clinic
  - When a patient requests appointment via WhatsApp or front desk, prefill top 3 recommended times for the selected doctor.
  - If the clinic supports multiple services, consider separate recommendations per service or duration.
- Salon
  - Recommend slots per stylist or “first available” across stylists.
  - For quick services (e.g., beard trim), favor near‑term slots; for longer services, spread load to avoid congestion.

### Admin UI integration ideas
- Add a “Use AI recommendations” toggle in booking screens. On toggle, call the new `recommend_slots` endpoint (or call the service server‑side) and surface the recommended times with a star icon and note like “AI suggested”.
- In appointment reports, add a small widget “Top Recommended Times This Week” for scheduling.

### What’s available out of the box vs. optional
- Available now:
  - The recommendation engine (`AIPredictor`) you can call from backend code handling bookings.
  - Store analytics APIs (for retail tenants with `store` module enabled).
  - Generic event logging endpoint to track user behavior.
- Optional (nice to have):
  - A dedicated endpoint to fetch slot recommendations per tenant/professional for cleaner UI integration.
  - A flag in tenant settings to enable/disable AI suggestions globally.

### Example: using `AIPredictor` in code (backend side)
```python
from app.services.ai import AIPredictor

recs, why = AIPredictor().recommend(tenant="clinic_123", professional="Dr.Sara", top_k=3)
# recs -> ["10:30", "11:00", "12:30"], why -> rationale string
```
Use these `recs` to order your slot list or to show a short “Recommended” section first.

### Summary
- The AI module for clinic/salon = appointment slot recommendations via `AIPredictor`.
- Integrate it into WhatsApp and admin booking flows to show top 2–3 suggested times first.
- Use the event endpoint to collect behavior for future improvements.
- Store‑specific AI endpoints exist, but they mainly help retail tenants; they’re optional for clinic/salon unless you activate the Store module.

If you want, I can outline a lightweight endpoint spec for `GET /ai/recommend_slots` and where exactly to call it in the WhatsApp timeslot flow.