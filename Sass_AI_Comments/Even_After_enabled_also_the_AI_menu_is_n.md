### Plan to resolve: AI menu not showing for tenant; AI hub shows “module disabled” despite being enabled

#### 1) Reproduce and collect evidence
- Login as Super Admin, enable AI module for target tenant, save. Verify modules/capabilities returned by `GET /tenants/{t}`.
- Login as the tenant user (tenant_admin and a staff user):
  - Open `/ai`. Capture what AI Index renders and what the sidebar shows.
  - Open DevTools → Network to confirm `GET /tenants/{t}` response and JWT claims.

#### 2) Validate backend normalization and guards
- Confirm `app/routers/tenants.py` normalization is active:
  - When `modules` includes `ai`:
    - If `store` enabled → `ai.predictions` present in response.
    - If `salon` or `clinic` enabled → `ai.appointment_recs` present in response.
  - When `ai` absent → no `ai.*` in response.
- Verify AI endpoints in `app/routers/ai.py` are gated by:
  - `ensure_module_enabled("ai")` for all
  - plus `ensure_module_enabled("store")` for store analytics, and `ensure_capability_enabled("ai.predictions")`.
  - `ensure_capability_enabled("ai.appointment_recs")` for appointments.

#### 3) Inspect Admin UI gating logic (sidebar + hub)
- AppShell sidebar shows AI only if:
  - `modules` includes `ai` AND
  - user has any applicable AI cap (tenant caps ∩ user JWT caps unless super_admin)
- AI Index (`/ai`) hub decides visibility using fetched tenant settings, not user JWT.
- Cross-check: tenant_admin should see AI menu if tenant has cap; staff requires both tenant cap and user cap.

#### 4) Fix likely causes
- Desync after saving: ensure Settings triggers cache clear + `tenantSettingsChanged`; AppShell listens and refreshes. Already implemented—reconfirm execution.
- JWT not refreshed for staff: instruct re-login OR update staff caps via Tenant Admin Users screen.
- Missing vertical module: If `ai` is ON but no `store/salon/clinic` → hub warns “no features”; sidebar may hide AI. Ensure tenant has appropriate vertical module.
- Case sensitivity: all checks should lowercase; confirm everywhere (already normalized in AI Index, AppShell, Settings).

#### 5) Hardening changes (if needed)
- AppShell AI nav condition tweak for tenant_admin to not require user JWT cap (mirror `RequireCapability` behavior):
  - If role === tenant_admin and tenant capabilities include `ai.predictions` or `ai.appointment_recs`, show AI.
- Ensure AI Index message logic: if hasAI but no derived features, message should guide enabling Store/Salon modules.

#### 6) Verification matrix
- Salon only tenant + AI ON (tenant_admin): Sidebar shows AI; `/ai` auto-redirects to `/ai/appointments`.
- Store only tenant + AI ON (tenant_admin): Sidebar shows AI; `/ai` → `/ai/predictions`.
- Staff user with only tenant caps (no user caps): Sidebar hides AI; `/ai` shows warning via `<RequireCapability>` on subpages.
- AI OFF: Sidebar hides AI; `/ai` warns “AI module disabled for this tenant”.

#### 7) Rollback/Safety
- No schema changes. Only UI gating tweaks if required. Backend normalization is read/write-safe and idempotent.

#### 8) Communication
- After fix, document:
  - “To enable AI: Super Admin → Settings → Modules: toggle AI. Ensure Store or Salon module is enabled for relevant features.”
  - “Tenant Admin sees AI automatically. Staff must be granted matching user capabilities or re-login to refresh JWT.”