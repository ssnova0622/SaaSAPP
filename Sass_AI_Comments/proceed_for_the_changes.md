### Progress update and next steps

I’ve started rebuilding a clean, efficient AI module and delivered the backend foundation with guarded endpoints and capability normalization. This lays the base for your requested features while keeping a simple, tenant‑enabled switch like other modules.

#### What’s implemented now (backend)
- AI module restored in the registry with focused capabilities aligned to your 10 features: `ai.appointment_recs`, `ai.reschedule`, `ai.no_show`, `ai.personalize`, `ai.staff_balance`, `ai.dynamic_pricing`, `ai.whatsapp_followup`, `ai.treatment_insights`, `ai.voice_actions`, `ai.biz_insights`.
- Tenant settings normalization: on GET/PUT we now auto‑derive AI capabilities from enabled modules and the AI module flag. If AI is off, all `ai.*` caps are stripped; if AI is on, applicable AI caps are added (Salon/Clinic and/or Store).
- AI router reintroduced and included in the app with guarded endpoints:
  - Smart booking: `GET /v1/tenants/{t}/ai/recommend_slots` → recommended times + rationale + all_available (uses existing `AIPredictor` heuristic, easily replaceable with ML later).
  - No‑show prediction: `GET /v1/tenants/{t}/ai/no_show/scores` → heuristic risk scores for upcoming appts.
  - Auto‑rescheduling: `POST /v1/tenants/{t}/ai/reschedule/propose` → suggested alternate slots (safe stub, respects availability).
  - Personalized services: `GET /v1/tenants/{t}/ai/personalize/services` → simple next‑best services (stub via recent top services).
  - Staff load balancing: `GET /v1/tenants/{t}/ai/workload/balance` → even weights baseline.
  - Dynamic pricing: `GET /v1/tenants/{t}/ai/pricing/quote` → guardrailed suggestion (off‑peak discount heuristic).
  - WhatsApp follow‑ups: `POST /v1/tenants/{t}/ai/followup/queue` → queues events for follow‑ups.
  - Treatment insights (Clinic): `GET /v1/tenants/{t}/ai/insights/treatments`.
  - Business insights: `GET /v1/tenants/{t}/ai/insights/summary`.
  - Voice notes → actions: `POST /v1/tenants/{t}/ai/voice/ingest` → queues a processing task.
- All AI endpoints are capability‑gated and require the AI module enabled (`ensure_module_enabled('ai')`) and the tenant to be active; store‑specific ones keep store module checks where applicable.

This means you can enable AI like any other module, and Salon/Clinic tenants will see appointment‑related AI while Store tenants can use pricing/insights, etc. The logic is consistent and easy to expand.

#### What’s next
- Tests: add API tests for guards and happy paths (recommendations, no‑show, reschedule, insights) and verify tenant normalization for AI caps.
- UI (single AI entry): re‑add the simple AI hub page and one Appointments Assist page; guard with `RequireCapability`. Keep the sidebar to a single “AI” entry.
- WhatsApp flow (optional next): prepend recommended times in the timeslot FSM when `ai.appointment_recs` is enabled (falls back cleanly if disabled).
- Incremental improvements: refine heuristics; add basic schedulers for follow‑ups; improve Business Insights with more KPIs.

If you want me to also wire the Admin UI now (single AI menu and minimal pages) and add the WhatsApp recommended slots step, I can proceed in the next iteration. 