### Plan for removing unwanted code and adding comprehensive tests

Below is a focused, staged plan to safely remove unwanted code and add end‑to‑end test coverage using a new root‑level folder `test/`.

#### 1) Define “unwanted” criteria and guardrails
- Dead code: files/exports with no references anywhere in the app (including dynamic routes/imports). 
- Duplications: consolidate on a single implementation (e.g., charts, tenant hooks). 
- Legacy paths: remove `useTenant` after verifying no remaining imports; standardize on `useEffectiveTenant`. 
- Dev scaffolding: retain only if referenced by UI or tests; otherwise remove.
- Do not remove any public API endpoint or UI route linked in navigation.

#### 2) Code inventory and candidate list
- Search for usages of suspected legacy/duplicate items; build a removal list with evidence of non‑usage. 
- Known targets to verify/remove:
  - Legacy hook `admin_ui/src/hooks/useTenant.ts` (replace last usage in Store/Orders if any remains).
  - Duplicate charts: prefer `admin_ui/src/components/charts/LineChart.tsx`; replace inline chart code in pages with the shared component; remove the inline implementations afterward.
  - Stray or duplicate Tenant selectors: keep `TenantSelector` and `TenantBadge` only via `AppShell`.
  - Commented/outdated helpers and unused exports in API modules.
- Backend (app/): identify unused routers/utilities by checking UI/API call sites; deprecate or remove only when unused.

#### 3) Safe cleanup pass (incremental)
- Remove files confirmed unused; run the app/tests to verify no breakage. 
- Replace inline `LineChart` usages with the shared component, then delete the inline implementations. 
- Delete `useTenant.ts` once no imports remain.

#### 4) Establish testing framework (backend)
- Create `test/` at project root (sibling of `admin_ui/`, `app/`).
- Add pytest scaffolding:
  - `test/conftest.py`: FastAPI `TestClient`, dependency overrides/mocks, seed data helpers.
  - `test/utils.py`: token/JWT helper for roles (super_admin, tenant_admin, staff), fixtures for tenants from `scripts/tenants.json`.
  - Configure `pytest.ini` (test discovery, markers), and README instructions.

#### 5) Backend functional tests by domain
- Auth & roles: login, JWT payload, scoping (401/403 for unauthorized paths).
- Tenants: list/get/update settings, activate/deactivate, capabilities/modules behavior.
- Users: create/update, set password, caps restrictions, role mapping; list/filter.
- Customers: list/search, upsert, import CSV (mocked upload), activate/deactivate.
- Professionals/Appointments: list, slots update, create/cancel appointment; constraints.
- Promotions: create, send (mock delivery), logs list.
- Followups: list, cancel; status transitions.
- Retention: summary and list for segments/days.
- Reports: run and list downloadable files; guard outputs.
- Store Catalog: categories/products CRUD, variants, inventory set/get; duplicate SKU prevention.
- Store Orders: list/detail, change items, update status, enforce edit guard for ONLINE+paid.
- WhatsApp: config get/put validations; menus list/get/upsert/publish; webhook dummy endpoint behavior.

#### 6) External integration mocks
- Twilio/Meta WhatsApp: stub endpoints; validate payload shape and basic flows.
- Payments provider (dummy): simulate statuses where needed; ensure ONLINE+paid guard holds.

#### 7) Optional frontend/e2e (later phase)
- Add a minimal API smoke suite that mirrors UI journeys (already covered by backend tests). 
- Consider adding Playwright/Cypress later for UI flows if required.

#### 8) CI and documentation
- Provide commands in README to run tests: `pytest -q`. 
- Emit a short coverage report; prioritize critical paths first.

#### 9) Execution order and checkpoints
- Step 1: Inventory and mark removal candidates (no code changes yet). 
- Step 2: Implement cleanup in small patches; verify app still runs. 
- Step 3: Create `test/` scaffolding; add core tests (auth, tenants, users). 
- Step 4: Expand tests module‑by‑module, mocking external services. 
- Step 5: Final sweep: remove any newly‑confirmed unused code surfaced by tests; deliver report of removed items and coverage summary.

If you approve this plan, I’ll proceed with: 
- Inventory + removal candidates list (and deduplicate charts). 
- Create the `test/` folder and add initial pytest scaffolding with starter tests for Tenants/Users. 
- Then iterate through the remaining domains until full coverage is in place.