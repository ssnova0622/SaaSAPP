### Status
No additional code changes are required to satisfy “Respective AI function only show in that AI page.” The current AI hub implementation already adheres to this behavior.

### What’s already in place (and matches your request)
- File `admin_ui/src/pages/AI/Index.tsx`:
  - Reads the effective tenant and its `modules`/`capabilities`.
  - Shows only applicable AI features:
    - `Appointments Assist` when: `modules` include `ai` AND (`salon` or `clinic`) AND capability `ai.appointment_recs` exists.
    - `Store Predictions` when: `modules` include `ai` AND `store` AND capability `ai.predictions` exists.
  - If exactly one feature applies, it auto‑redirects to that page to keep the UI simple.
  - If AI is enabled but no applicable vertical is enabled, it shows a concise guidance message.
- Sub‑routes remain strictly guarded:
  - `/ai/appointments` is protected by `RequireCapability('ai.appointment_recs')`.

### How to verify quickly
- Salon/Clinic tenant with AI enabled:
  - Sidebar → AI opens and auto‑redirects to `/ai/appointments`.
  - The AI hub will not show Store‑only features.
- Store tenant with AI enabled:
  - Sidebar → AI opens and auto‑redirects to the Store AI page (when present); Salon features will not be shown.
- Mixed tenant with both verticals + AI:
  - AI hub shows both cards.
- AI disabled:
  - AI menu hidden; `/ai` shows a guidance message.

### Notes
- Backend guards also enforce the same rules, so even deep links stay consistent.
- If a staff user does not see AI despite tenant enablement, ensure their JWT caps include the corresponding AI capability or have them re‑login. Tenant Admins rely on tenant capability and do not need user‑level caps.

If you’d still like the AI hub to always show all features with “Locked/Enable” hints, I can implement that alternate behavior; otherwise, the current, tenant‑specific visibility is already live.