### Plan created for the reported issue

I’ve prepared a focused plan to resolve: “After enabling the AI Prediction module for a salon from Super Admin, the AI menu is not showing in the salon tenant login.”

#### Summary of the suspected root cause
- Routes for AI exist, and the AI hub (`/ai`) is reachable, but the left‑nav likely does not render an AI item for salon tenants. The nav probably lacks an AI entry or is gated only by `ai.predictions` (store) instead of `ai.appointment_recs` (salon/clinic). A second possible factor is settings cache not refreshing after Super Admin changes.

#### Action plan
1) Reproduce and verify current behavior (read‑only)
- Log in as a salon tenant admin and try visiting `/ai` directly to confirm the page is accessible.
- Confirm the tenant actually has `modules` including `"ai"` and `capabilities` including `"ai.appointment_recs"`.

2) Inspect Admin UI navigation for AI entry
- Open `admin_ui/src/components/AppShell/AppShell.tsx` (or the file that renders the left navigation) to find current nav items and gating logic.
- Verify whether an AI nav entry exists; if present, check its conditions (should show for salon/clinic when `ai` module enabled AND `ai.appointment_recs` present).

3) Implement AI menu entry visibility rules (Admin UI)
- Add a top‑level “AI” link to `/ai` in the left nav.
- Show it when: `modules` includes `"ai"` AND at least one of `"ai.predictions"` or `"ai.appointment_recs"` is enabled.
- Optionally add sub‑links:
  - Predictions → visible if `ai.predictions`.
  - Appointments Assist → visible if `ai.appointment_recs`.

4) Ensure tenant settings cache coherence
- Review `admin_ui/src/api/tenants.tsx` cache usage. If the nav reads cached settings, ensure the cache is cleared after Super Admin updates modules/caps or when switching tenants/logging in.
- If needed, call `clearTenantSettingsCache()` on logout/tenant switch, and after saving in Settings.

5) Validate routes/guards
- `/ai` remains accessible without a capability guard; it should render context cards based on modules/caps.
- `/ai/appointments` continues to require `ai.appointment_recs`; `/ai/predictions` requires `ai.predictions`.

6) Manual verification scenarios
- Salon only + AI module + `ai.appointment_recs`: AI menu visible; AI hub opens and shows Appointments Assist entry; `/ai/appointments` works.
- Store only + AI module + `ai.predictions`: AI menu visible; Predictions entry and pages work.
- AI disabled: no AI menu entry; direct `/ai` shows empty‑state message (or redirect, as designed).

7) Optional UX polish
- On `/ai`, show a short tip guiding users to Settings → Modules to enable relevant capabilities if AI module is on but no AI caps are active.

8) Lightweight checks/tests
- Ensure TypeScript build is green.
- Quick render test or manual check of AppShell to confirm AI nav visibility per tenant configuration.

I will proceed with step 2 next: open the AppShell navigation and fix the gating so salon tenants with `ai.appointment_recs` see the AI menu.