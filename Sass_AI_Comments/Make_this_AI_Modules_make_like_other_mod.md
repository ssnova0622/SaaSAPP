### Updated plan for the new issue

Make the AI module behave exactly like other modules (Store/Salon), so Super Admin can simply enable/disable it, and based on tenant’s vertical modules the tenant will only see their relevant AI features. Specifically: if “AI Salon” is enabled, salon tenants see AI items in their menu; if “AI Store” is enabled, store tenants see store AI.

#### What we already have in code
- AI is a separate module (`ai`) and is shown in the sidebar as a single “AI” entry when enabled.
- Admin UI `/ai` hub auto‑redirects when only one feature applies (Predictions for Store; Appointments Assist for Salon/Clinic).
- Backend routes are gated by `ensure_module_enabled('ai')` and appropriate vertical capability guards.
- Tenant settings GET/PUT normalize capabilities from modules so AI behaves like a module with derived caps.

#### What we’ll align to “like other modules”
1) Super Admin → Modules
   - Treat `ai` exactly like `store` or `salon`: a single checkbox in Modules.
   - Remove any separate AI UI controls beyond this one module toggle (no scope radios, no extra AI caps toggles in Settings).
2) Capabilities handling (automatic)
   - When `ai` is ON, backend will derive the correct AI capabilities from vertical modules:
     - If `store` module is enabled → add `ai.predictions`.
     - If `salon` or `clinic` module is enabled → add `ai.appointment_recs`.
     - If both verticals are present → both capabilities apply.
   - When `ai` is OFF → strip all `ai.*` capabilities.
3) Navigation
   - Sidebar shows a single “AI” item only when `ai` module is ON and at least one applicable AI feature is derived.
   - `/ai` hub continues to auto‑redirect to the sole applicable page. Mixed tenants see both cards.
4) Tenant experience
   - Salon tenants with `ai` ON automatically see Appointments AI; store tenants with `ai` ON see Predictions AI, without extra toggles.

#### Validation checklist
- Super Admin checks “AI” module for a salon tenant → tenant sees AI in sidebar; opening `/ai` goes to Appointments.
- Super Admin checks “AI” module for a store tenant → tenant sees AI in sidebar; opening `/ai` goes to Predictions.
- Disabling “AI” removes AI menu and blocks AI endpoints (403).

No risky backend changes are required because the current normalization already enforces this behavior. The remaining work is mainly UI polish in Settings to keep only the `ai` module checkbox and hide AI capability editing (which is already locked).

If you want, I can proceed to ensure the Modules page shows `ai` alongside others and remove any leftover AI‑specific toggles, then verify via quick tests (enable for Salon; enable for Store).