### Plan: Rebuild a clean, efficient AI module delivering the requested features

#### Objective
Design and implement a modular, tenant‑enabled AI system that cleanly integrates with Salon/Clinic and Store verticals, covering the 10 requested capabilities while remaining maintainable, privacy‑conscious, and switchable per tenant.

#### Guiding principles
- Single AI module toggle per tenant; features auto‑derive from active vertical modules (Salon/Clinic, Store) and data availability.
- API‑first: thin, well‑typed endpoints; AI services encapsulated behind adapters for easy upgrades (heuristics → ML models later).
- Event‑driven where beneficial; fall back to scheduled jobs for heavy analytics.
- Safe defaults, explainable outputs, and graceful degradation when data is insufficient.

---

### Phase 0 — Foundations (module skeleton, data, guards)
1) Restore AI module and capability registry
- Module: `ai`
- Derived capabilities (auto‑managed server‑side):
  - `ai.appointment_recs` (Salon/Clinic)
  - `ai.reschedule` (auto‑rescheduling)
  - `ai.no_show` (no‑show prediction)
  - `ai.personalize` (service recommendations)
  - `ai.staff_balance` (load balancing)
  - `ai.dynamic_pricing` (store/salon pricing experiments)
  - `ai.whatsapp_followup` (follow‑up bot)
  - `ai.treatment_insights` (clinic insights)
  - `ai.voice_actions` (voice note understanding)
  - `ai.biz_insights` (owner dashboard)

2) Backend scaffolding
- Service layer in `app/services/ai/`:
  - `scheduler.py` (jobs), `events.py` (ingest), `features.py` (feature builders), `models.py` (heuristics/ML placeholders), `recommendations.py` (slot + services), `risk.py` (no‑show), `pricing.py` (dynamic pricing), `workload.py` (staff balancing), `insights.py` (biz/treatment), `whatsapp_bot.py` (follow‑ups), `voice.py` (voice → intent/actions).
- Router `app/routers/ai.py` with cohesive endpoints, all guarded by `ensure_module_enabled('ai')` plus vertical checks.
- Tenant normalization: re‑introduce AI caps derivation from modules (AI ON → add caps per vertical).
- Storage additions (if needed) via `Storage`: tables/collections for `events`, `no_show_scores`, `reschedule_rules`, `pricing_rules`, `voice_tasks`, `insights_cache`.

3) Data contracts
- Appointments, customers, staff/professionals, orders (store), WhatsApp messages, events (generic) — confirm existing schemas; add minimal fields: `appt.metadata.no_show_score`, `appt.source`, `appt.rescheduled_from`, `customer.tags/preferences`.

---

### Phase 1 — AI Smart Appointment Booking
- Endpoint: `GET /tenants/{t}/ai/recommend_slots?professional=&date=&top=3`
- Logic: heuristic ranker initially (time proximity, spread load, historical popularity); pluggable ML later.
- Integrations:
  - WhatsApp flow: prepend “Recommended slots” with 2–3 quick options.
  - Admin booking UI: star‑highlight recommended slots; toggle to sort by recommendation.
- Telemetry: log chosen vs. offered for model improvement.

### Phase 2 — AI Auto‑Rescheduling
- Detect disruptions (staff sick, overbook, equipment down) or high no‑show risk.
- Endpoint: `POST /tenants/{t}/ai/reschedule/propose` → returns candidate moves (slot → new slot, message templates).
- WhatsApp outreach: ask customers to confirm new slot; auto‑apply on acceptance.
- Constraints: respect staff availability, service duration, buffers.

### Phase 3 — AI No‑Show Prediction & Prevention
- Heuristic features: past attendance, lead time, time‑of‑day, day‑of‑week, service type, price, customer history.
- Endpoint: `GET /tenants/{t}/ai/no_show/scores?window_days=7`.
- Prevention playbooks: reminders, deposits, double‑confirm, overbooking threshold guidance.

### Phase 4 — AI Personalized Service Recommendation
- For Salon/Clinic: “next best service” (add‑ons, follow‑up treatments).
- Endpoints:
  - `GET /tenants/{t}/ai/personalize/services?customer_id=`
  - `GET /tenants/{t}/ai/personalize/addons?service_id=`
- Surfaces: booking screen upsell, WhatsApp suggestions post‑booking.

### Phase 5 — AI Staff Load Balancing
- Goal: distribute demand across professionals to reduce wait and burnout.
- Endpoint: `GET /tenants/{t}/ai/workload/balance?date=` returns recommended allocation weights, priority rules.
- Usage: influence recommendation ranking, admin hints, scheduling calendar overlays.

### Phase 6 — AI Dynamic Pricing (advanced)
- Simple rules to start: off‑peak discounts, peak surcharges bounds.
- Endpoint: `GET /tenants/{t}/ai/pricing/quote?service_id=&time=` → suggested price and rationale.
- Guardrails: min/max price, fairness, transparent reason string. A/B test flag.

### Phase 7 — AI WhatsApp Follow‑Up & Retention Bot
- Templates for post‑visit NPS, re‑engagement, missed appointment recovery.
- Endpoint: `POST /tenants/{t}/ai/followup/queue`.
- Scheduler sends via WhatsApp provider; opt‑out honored; per‑tenant throttle.

### Phase 8 — AI Treatment History & Insights (Clinic)
- Aggregate treatments by diagnosis/procedure; outcomes and recurrence hints.
- Endpoints:
  - `GET /tenants/{t}/ai/insights/treatments?range=`
  - `GET /tenants/{t}/ai/insights/patients?segment=`
- UI: clinician view with filters, printable summary.

### Phase 9 — AI Voice Notes → Actions
- Intake: WhatsApp audio or admin voice notes.
- Pipeline: transcribe (pluggable provider), intent extract (rules/ML), map to actions (create appt, add note, task).
- Endpoints: `POST /tenants/{t}/ai/voice/ingest` (audio URL/id), `GET /tenants/{t}/ai/voice/tasks`.

### Phase 10 — AI Business Insights Dashboard
- Owner summary: utilization, no‑show risk, revenue at risk, top services, staff load, follow‑up ROI.
- Endpoint: `GET /tenants/{t}/ai/insights/summary?range=28d`.
- UI card on Dashboard if AI enabled.

---

### Architecture & implementation details
- Guards: every AI route → `ensure_module_enabled('ai')` and tenant active; plus vertical checks (e.g., salon/clinic for appointments, store for pricing in retail context) if needed.
- Feature flags: per‑tenant derived from modules; can soft‑disable subsets via settings (`ai_config` with booleans), default ON for applicable features.
- Storage schema additions are minimal and backward‑compatible; all writes are optional.
- WhatsApp: actions are encapsulated; if AI suggests content, the bot renders it as buttons with safe fallbacks.
- Explainability: every recommendation/pricing returns `rationale` and key factors.

### Testing strategy
- Unit tests for rankers (deterministic with fixed inputs).
- API tests for guards and typical responses (empty data, normal, error handling).
- WhatsApp flow tests: FSM paths with/without AI enabled.
- Scheduler/cron dry‑run tests for follow‑ups.

### Rollout plan
1) Reintroduce AI module and minimal endpoints: `recommend_slots`, biz insights summary, follow‑up queue; wire WhatsApp recommendations and Admin booking hints.
2) Add no‑show scores and auto‑reschedule proposals.
3) Add personalization and staff load balancing.
4) Add dynamic pricing (A/B off by default).
5) Add voice notes → actions; clinic treatment insights.

### Security & privacy
- Tenant data isolation; PII masked in logs.
- Opt‑in for follow‑ups and retention messages with clear opt‑out.
- Rate limits and idempotency keys for outbound messaging.

### Acceptance criteria (Milestone 1)
- AI module visible like other modules; enabling it for Salon/Clinic shows Appointments AI; enabling it for Store shows Store AI.
- `GET /ai/recommend_slots` returns recommended + all_available; WhatsApp and Admin UI surface it when applicable.
- Follow‑up queue endpoint exists and schedules WhatsApp messages (dev mode stub ok).
- Business Insights summary endpoint returns sensible aggregates.

If you approve, I will implement Milestone 1 and deliver the endpoints, guards, UI wiring, and tests. 