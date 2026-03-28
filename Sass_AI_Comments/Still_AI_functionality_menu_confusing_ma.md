### New plan to make AI “simple enable/disable” (no confusion)

#### Goal
One switch to enable AI per tenant. When AI is ON, the system automatically shows only the AI features relevant to the tenant’s vertical modules (Salon/Clinic vs Store). No separate AI checkboxes or multi-step setup.

#### Plan
1. Single AI toggle in Super Admin Settings (UI)
- Keep only one switch: `Enable AI for this tenant`.
- ON → add `ai` to tenant `modules`.
- OFF → remove `ai` from `modules` and strip all `ai.*` capabilities.
- Remove the current scope radios and any direct checkboxes for `ai.predictions` / `ai.appointment_recs`.

2. Backend: auto‑derive AI capabilities from vertical modules
- On tenant save (and on read normalization), if `ai` is enabled:
  - If `store` module present → include `ai.predictions`.
  - If `salon` or `clinic` present → include `ai.appointment_recs`.
  - If both verticals present → include both.
- If `ai` is disabled → ensure no `ai.*` capability remains.
- Centralize this logic so UI doesn’t need to manage AI capabilities at all.

3. Navigation and AI hub behavior
- Sidebar: show a single `AI` menu only when `ai` module is enabled and at least one derived AI feature applies.
- `/ai` hub:
  - If only one feature applies, auto‑redirect to it.
  - If both apply (mixed tenant), show exactly those two cards.
  - If none apply (rare), show a minimal info message.

4. Remove/conflict‑proof UI controls
- In the registry‑driven capabilities UI, hide or lock editing of `ai.*` caps and show a note: "AI features are controlled by the AI toggle and tenant modules."

5. Guards and validation (backend)
- Keep `ensure_module_enabled('ai')` for all AI routes.
- Store AI routes additionally require `ensure_module_enabled('store')`.
- Appointment recommendations additionally require at least one of `salon` or `clinic` modules.
- When AI is OFF, reject all AI routes regardless of stale caps.

6. Data migration/backfill
- On first read/save after deploy, normalize: add missing derived `ai.*` caps when `ai` is ON; remove any `ai.*` caps when `ai` is OFF.

7. Cache and instant refresh
- After Settings save, clear the tenant settings cache and broadcast `tenantSettingsChanged` so the sidebar updates immediately (already wired).

8. QA scenarios
- Salon only + AI ON → Sidebar shows `AI`; `/ai` redirects to Appointments; Predictions not visible.
- Store only + AI ON → Sidebar shows `AI`; `/ai` redirects to Predictions; Appointments not visible.
- Both modules + AI ON → Sidebar shows `AI`; `/ai` shows both cards.
- AI OFF → No AI in sidebar; `/ai` shows guidance only.

#### What’s already done vs. next
- Already done in this repo: single AI menu in sidebar, `/ai` auto‑redirect when only one feature applies, and cache‑refresh after Settings save.
- Next steps to fully meet “simple enable/disable”:
  - Remove scope radios and any lingering AI capability checkboxes from Settings.
  - Add backend normalization that derives `ai.*` capabilities from modules and strips them when AI is OFF.
  - Hide/lock `ai.*` in registry UI.

If you want, I can proceed to implement the backend normalization and remove the last UI scope controls in one pass.