### Cause summary
The capability `ai.appointment_recs` is returned only when BOTH of these are true for the tenant:
- The `ai` module is enabled, and
- Either the `salon` or `clinic` module is enabled

Backend normalization in `app/routers/tenants.py` now derives `ai.appointment_recs` automatically from the enabled modules on every GET/PUT of tenant settings. If either `ai` is off or neither `salon/clinic` is present, the capability won’t appear. UI gating also requires a fresh fetch (and staff users may need a token refresh) to reflect changes.

### Quick fix checklist
- Super Admin → Settings → Modules
  - Ensure `ai` is enabled for the tenant
  - Ensure the vertical module is enabled: `salon` or `clinic`
  - Click “Save” (this triggers normalization and broadcasts `tenantSettingsChanged` so the sidebar refreshes)
- Verify from API (evidence):
  - `GET /tenants/{tenant}` → `modules` should include `ai` and `salon` or `clinic`
  - `capabilities` should include `ai.appointment_recs`
- Login context:
  - Tenant Admin: sidebar shows “AI”; visiting `/ai` should auto-redirect to `/ai/appointments`
  - Staff: they must have user-level caps or re-login to refresh JWT; otherwise AI pages may stay hidden
- Appointments Assist page:
  - If professionals list is empty, add at least one professional in `Professionals` page; the dropdown and “Get Recommendations” will then work

### Why this happens (common pitfalls)
- AI module was enabled but `salon/clinic` module was not → no `ai.appointment_recs` derived
- Cache/JWT stale after Super Admin save → UI didn’t reflect until refresh/re-login
- Staff user missing user caps (Tenant Admin is allowed by tenant capability; Staff needs both tenant+user caps)

### What’s already in place
- Backend derives `ai.appointment_recs` automatically (no manual cap toggles needed)
- `clinic` module is registered so it won’t be dropped during normalization
- Sidebar gating: Tenant Admin sees AI when tenant caps have AI; Staff requires both tenant+user caps
- AI hub uses the “effective tenant” and auto-redirects to Appointments when that’s the only applicable AI feature

### If it still fails
- Confirm `GET /tenants/{tenant}` actually includes `ai` and `salon|clinic` in `modules`. If not, enable them and Save again.
- Call `GET /tenants/{tenant}/ai/recommend_slots` as Tenant Admin. Expect 200. If you get 403, either `ai` module or `ai.appointment_recs` is missing.
- Have Staff users re-login or grant user caps explicitly if Staff must access AI.

Once `ai` + `salon|clinic` are enabled and saved, the capability `ai.appointment_recs` will be present and the AI Appointments functionality will work end-to-end.