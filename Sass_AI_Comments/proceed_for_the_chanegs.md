### Update
- Reintroduced a clean AI module on the backend, with tenant-based enablement and granular capabilities matching your requested features. Core endpoints are in place and gated correctly.
- Restored automatic derivation of AI capabilities from enabled modules (AI + Salon/Clinic/Store) in tenant settings GET/PUT.
- Included the AI router in the app so APIs are available at `/v1/tenants/{tenant}/ai/...`.

#### Delivered endpoints (first cut)
- Smart Booking: `GET /ai/recommend_slots`
- No‑Show Risk: `GET /ai/no_show/scores`
- Auto‑Reschedule (proposals): `POST /ai/reschedule/propose`
- Personalization: `GET /ai/personalize/services`
- Staff Load Balance: `GET /ai/workload/balance`
- Dynamic Pricing (guardrailed): `GET /ai/pricing/quote`
- WhatsApp Follow‑ups queue: `POST /ai/followup/queue`
- Treatment Insights (Clinic): `GET /ai/insights/treatments`
- Business Insights: `GET /ai/insights/summary`
- Voice → Actions (ingest): `POST /ai/voice/ingest`

All are capability‑gated under the `ai` module with appropriate per‑feature caps.

### Next steps (planned)
- Add API tests for guards and happy paths (recommendations, no‑show, reschedule, insights).
- Reintroduce a single AI entry in the Admin UI (hub + Appointments Assist), guarded by the derived capabilities.
- Optional: Enhance WhatsApp timeslot flow to prepend recommendations when `ai.appointment_recs` is enabled.

If you’d like, I can proceed immediately with UI wiring (single AI menu + minimal pages) and the tests in the next pass.