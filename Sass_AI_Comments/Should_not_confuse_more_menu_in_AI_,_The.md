### Plan to simplify the AI module UI per tenant (Salon vs Store)

#### Objective
Show a single AI entry for tenants and render only the relevant AI functionality based on what the Super Admin enabled: Salon/Clinic (appointments) or Store (predictions). Avoid exposing non‑applicable AI features anywhere in the Admin UI.

### 1. Consolidate navigation to a single AI entry
- Remove sidebar items `AI — Predictions` and `AI — Appointments` to avoid multiple AI entries confusing users.
- Keep only one top‑level menu item: `AI` linking to `/ai`.
- Gating rule to show the `AI` entry:
  - Tenant must have `modules` containing `"ai"`, and
  - User must have at least one of the capabilities present on the tenant AND the user token: `ai.predictions` or `ai.appointment_recs`.

### 2. Make the AI hub page auto‑route when only one feature is available
- On `/ai`, compute booleans:
  - `showPredictions` = AI module + Store module + `ai.predictions`.
  - `showAppointments` = AI module + (Salon or Clinic) + `ai.appointment_recs`.
- If exactly one of these is true, auto‑navigate immediately to the corresponding page (`/ai/predictions` or `/ai/appointments`).
- If both are true (mixed tenants), show both cards; if none are true, show an empty state with guidance to enable the desired AI capability in Settings.

### 3. Scope each subpage strictly by capability
- Keep existing route guards:
  - `/ai/predictions` → `RequireCapability("ai.predictions")`.
  - `/ai/appointments` → `RequireCapability("ai.appointment_recs")`.
- These already ensure deep‑link safety; the nav/hub changes are purely for clarity.

### 4. Super Admin controls in Settings
- Ensure Super Admin enables the single AI module and assigns exactly one of the following per tenant (or both if tenant legitimately uses both verticals):
  - `ai.appointment_recs` for Salon/Clinic tenants.
  - `ai.predictions` for Store tenants.
- To minimize confusion, add an optional UI hint: “Pick only the AI capability that matches this tenant’s vertical.” If both are selected, the AI hub will show both tabs.

### 5. Tenant settings caching and refresh
- After Super Admin saves Module/Capability changes, clear cached tenant settings and re‑fetch on the tenant’s next session.
- Already supported by `clearTenantSettingsCache()` on logout and by Settings save flows; verify AppShell re‑requests settings on mount/tenant switch.

### 6. Backend validation (already in place; verify)
- AI endpoints require AI module: `ensure_module_enabled("ai")`.
- Store AI endpoints additionally require `ensure_module_enabled("store")` + `ai.predictions`.
- Appointments AI endpoint requires `ai.appointment_recs`.
- WhatsApp timeslot flow already checks `ai.appointment_recs` and remains unchanged.

### 7. UI polishing rules
- Hide any non‑applicable AI content from the hub and sidebar (single AI entry only).
- On `/ai`, show only the relevant feature(s) and automatically route if exactly one applies.
- Keep card descriptions concise and vertical‑specific labels: `Appointments Assist` (Salon/Clinic) vs `Store Predictions`.

### 8. QA scenarios
- Salon tenant: `modules = [ai, salon]`, `capabilities = [ai.appointment_recs]` → Sidebar shows `AI`; opening AI redirects to `/ai/appointments` directly. Predictions never shown.
- Store tenant: `modules = [ai, store]`, `capabilities = [ai.predictions]` → Sidebar shows `AI`; opening AI redirects to `/ai/predictions`. Appointments never shown.
- Mixed tenant (both modules and both caps): Sidebar shows `AI`; `/ai` displays both cards; each subpage opens with its capability.
- Tenant with AI module but no AI capabilities: Sidebar may hide `AI` completely; if the hub is accessible, it shows an info state with guidance.

### 9. Rollout steps
- Implement nav consolidation (remove per‑feature AI nav items; keep only `AI`).
- Add auto‑redirect logic in `/ai` when a single feature applies.
- Verify route guards and capability checks remain unchanged.
- Validate on sample salon and store tenants.

### Acceptance criteria
- There is only one AI item in the sidebar.
- Salon tenants only see Salon AI; Store tenants only see Store AI.
- Mixed tenants see both, but only within the AI hub.
- Direct routes remain protected and behave as expected.
