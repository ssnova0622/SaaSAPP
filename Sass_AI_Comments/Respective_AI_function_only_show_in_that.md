### Updated plan for the AI page visibility

You asked: “Respective AI function only show in that AI page.” Interpreting this as: the AI page should show only the AI features that are actually applicable and enabled for the currently selected tenant (based on modules and capabilities), not all features and not features for other verticals.

#### Target behavior
- AI hub (`/ai`) shows only the features that the tenant can use now.
- Determination is based on:
  - Tenant modules include `ai` AND
  - Capabilities include the needed AI capability for each feature, and (when applicable) the vertical module (e.g., `salon` or `clinic` for appointments; `store` for predictions/pricing).
- If exactly one feature is available, auto-redirect to it to reduce clicks.
- If none is available, show a concise message guiding how to enable the correct module/capability.

#### Implementation outline (front-end only)
- File: `admin_ui/src/pages/AI/Index.tsx`
  - Keep using `useEffectiveTenant()` and `getTenantSettings(tenant)`.
  - Compute:
    - `hasAI = modules.includes('ai')`
    - `hasSalonOrClinic = modules.includes('salon') || modules.includes('clinic')`
    - `hasStore = modules.includes('store')`
    - Cap flags: `canAppt = caps.includes('ai.appointment_recs')`, `canPred = caps.includes('ai.predictions')`, plus any other AI caps that are already wired.
  - Visibility flags:
    - Appointments Assist → `hasAI && hasSalonOrClinic && canAppt`
    - Predictions (if page exists) → `hasAI && hasStore && canPred`
    - For any future AI features, follow the same pattern with their capability + vertical check.
  - Auto-redirect if exactly one is true; else render only those true cards.

#### Current repo status
- The AI hub already implements this conditional show logic (appointments vs. predictions) and auto-redirect when only one feature applies.
- Subpage `/ai/appointments` is gated with `RequireCapability('ai.appointment_recs')`.

#### What I will do now
- Keep the “respective features only” behavior as the source of truth (it’s already in place).
- Ensure no extra/locked AI cards are shown on `/ai` to avoid confusion.
- Leave backend route guards unchanged.

#### Acceptance criteria
- Salon/Clinic tenant with AI: Only “Appointments Assist” is shown (and `/ai` redirects to it).
- Store tenant with AI: Only “Predictions” (when present) is shown (and `/ai` redirects to it).
- Mixed tenants: Both applicable features show.
- AI disabled: No features; show guidance message on `/ai`.

This matches your request to show only the respective AI function(s) on the AI page for the selected tenant.