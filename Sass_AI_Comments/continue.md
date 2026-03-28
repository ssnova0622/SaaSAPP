### Plan to continue (Effective Issue: continue)

#### Goals
- Finalize Phase 1 of the clean AI module with a reliable tenant-enabled experience.
- Ensure Admin UI reflects AI features simply and correctly for Salon/Clinic tenants.
- Strengthen test coverage for guards and core happy paths.

#### Scope
- Backend: validate AI capability derivation, confirm endpoint gating, and keep WhatsApp AI prepend robust.
- Frontend: ensure single AI entry behaves per tenant, Appointments Assist works with real professionals list, and messaging is clear.

#### Steps
1) Backend verification & tests
- Add/expand tests to cover:
  - Tenant normalization: AI OFF → no `ai.*`; AI ON + salon/clinic → `ai.appointment_recs` present.
  - Endpoint guards: 403 when AI OFF; 200 when AI ON for `GET /ai/recommend_slots`.
  - WhatsApp FSM: unit-style check of ordered list merge with recommendations (if feasible) or targeted integration test.
- Ensure `app/modules/registry.py` includes `ai`, `salon`, and `clinic` modules (already done) and all AI caps.
- Keep `app/routers/ai.py` endpoints gated with `ensure_module_enabled('ai')` + feature caps; no changes unless tests reveal gaps.

2) Admin UI polish
- Sidebar: single “AI” entry remains; visible when tenant has `ai` module and either `ai.appointment_recs` or store AI caps (already wired).
- AI hub `/ai`: auto-redirect to `/ai/appointments` for salon/clinic tenants; keep empty-state messages for missing modules.
- Appointments Assist:
  - Professionals dropdown fetches via `/tenants/{t}/professionals` and handles empty state with link to Professionals page.
  - “Get Recommendations” calls `GET /ai/recommend_slots` and renders `recommended` + `all_available` with rationale.

3) WhatsApp flow
- Keep prepend of “Recommended times” when `ai.appointment_recs` is enabled; ensure graceful fallback when unavailable.
- Validate that session stores merged `available_slots` so numeric replies work.

4) Super Admin Settings consistency
- Retain single-module behavior: enabling `ai` is enough; AI caps are derived automatically based on vertical modules.
- Ensure cache clear + broadcast `tenantSettingsChanged` after save so nav updates instantly (already in place).

5) Documentation
- Add short Admin guide notes:
  - How to enable AI (toggle AI module); auto-derivation for salon/clinic.
  - Where AI appears in UI and how to use Appointments Assist.
  - WhatsApp enhancement behavior.

6) Acceptance criteria
- For a salon/clinic tenant with AI enabled:
  - AI shows as a single nav item; `/ai` redirects to Appointments Assist.
  - `GET /ai/recommend_slots` returns recommended + rationale + all_available.
  - WhatsApp timeslot messages show a “Recommended times” line when available.
- For AI disabled tenants, AI nav is hidden and endpoints return 403.
- Tests for guards and happy path pass.

#### Risks & mitigations
- JWT staleness for staff users: document re-login or grant user caps explicitly; tenant_admin works via tenant cap.
- Data sparsity: UI shows friendly empty states; WhatsApp falls back to regular slots.

#### Timeline
- Tests + small polish: 0.5–1 day
- Docs: 0.25 day