### Plan to remove all AI-related code

#### Scope
Remove all AI functionality from both backend and frontend so there are no AI routes, services, UI pages, navigation, capabilities, or module toggles left. Preserve non-AI features (WhatsApp, Store, Salon/Clinic, Settings, etc.).

#### High-level steps
1) Backend removal
- Delete AI service and endpoints:
  - Remove file `app/services/ai.py` and all references to `AIPredictor`.
  - Remove router `app/routers/ai.py`; unregister if included in app factory.
- Purge AI usage in other routers:
  - `app/routers/whatsapp.py`: remove all logic that imports or calls `AIPredictor` and any checks for `ai.appointment_recs`; simplify timeslot flow to non-AI order.
- Tenant settings normalization:
  - `app/routers/tenants.py`: remove `_normalize_ai_caps` and any logic that derives `ai.*` capabilities; ensure save/get endpoints no longer mention AI.
- Modules registry cleanup:
  - `app/modules/registry.py`: remove `ai` module entry and AI capabilities (`ai.predictions`), and any references.

2) Frontend removal
- API layer:
  - Delete `admin_ui/src/api/ai.ts` and remove imports/usages.
- Pages and routes:
  - Remove `/ai` routes from `admin_ui/src/App.tsx` and delete pages:
    - `admin_ui/src/pages/AI/Index.tsx`
    - `admin_ui/src/pages/AI/Predictions.tsx` (if present)
    - `admin_ui/src/pages/AI/AppointmentsAssist.tsx`
- Navigation:
  - `admin_ui/src/components/AppShell/AppShell.tsx`: remove dynamic AI menu logic and any AI flags.
- Settings UI:
  - `admin_ui/src/pages/Settings.tsx`: remove AI Module toggle/section and any AI mentions; remove cache events related to AI if dedicated.
- Any residual components/hooks pointing to AI should be removed.

3) Capabilities and guards cleanup
- Remove any capability checks for `ai.*` in UI guards (`RequireCapability`) and backend deps where present.
- Ensure no tenant documents rely on `ai.*`; backend should ignore unknown caps safely.

4) Data/storage considerations
- If `Storage` has AI-related methods (predictions, forecasts), remove or leave as dead code if not referenced; prefer removal to avoid confusion.
- No schema migration required if capabilities are stored as arrays; unknown entries will be inert but we will stop writing them.

5) Build/test verification
- Backend: run unit/integration tests to ensure all references to AI are gone and app starts.
- Frontend: TypeScript compile without AI imports; run the app and verify navigation and WhatsApp flows work (timeslot without recommendations).

#### Acceptance criteria
- No AI menu/pages in UI; no AI API calls exist in the codebase.
- `whatsapp.py` has no references to `AIPredictor` or `ai.appointment_recs`.
- `tenants.py` does not normalize/derive any `ai.*` capabilities.
- `registry.py` does not contain `ai` module or `ai.*` capabilities.
- Builds pass and non-AI functionality remains intact.