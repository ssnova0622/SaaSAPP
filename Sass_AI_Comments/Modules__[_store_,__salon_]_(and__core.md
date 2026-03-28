### Modules reintroduced (Core/Store/Salon) and enforced per tenant — next steps to verify
I’ve implemented your request to separate modules again and make them assignable per tenant. Capabilities now sit under their module. Tenant Admins (Option B) automatically gain access to tenant‑enabled capabilities; Staff still require per‑user caps.

#### What changed (server)
- app/modules/registry.py
  - Added explicit modules: `core`, `store`, `salon` (type=`module`).
  - Each capability is mapped to its owning module via a `module` field.
  - `module_defaults(modules)` returns default capabilities for the selected modules only.
  - `normalize_selection(modules, capabilities)` now:
    - Validates requested modules.
    - Starts with defaults for the selected modules.
    - Adds only capabilities that belong to those selected modules.
    - Returns normalized `mods` and `caps` (lowercase, sorted, unique).
- app/routers/deps.py
  - `ensure_module_enabled(module_id)` is no longer a no‑op. It now checks the tenant’s `modules` list and returns 403 if the module isn’t enabled for that tenant.
  - `ensure_capability_enabled(cap)` remains Option B:
    - Tenant Admin bypasses per‑user caps (only tenant capability must be enabled).
    - Staff must have the capability in their user caps AND the tenant must have it enabled.

This integrates with existing routes like `catalog.py` which still do `Depends(ensure_module_enabled("store"))` + `Depends(ensure_capability_enabled("store.catalog"))`.

#### What changed (Admin UI)
- admin_ui/src/pages/Settings.tsx
  - Super Admin now sees a “Modules & Capabilities” section:
    - Modules section (checkboxes for `core`, `store`, `salon`).
    - Capabilities are grouped and disabled if their owning module is not enabled.
    - “Select defaults” adds default capabilities only for modules currently enabled.
    - Save sends both `modules` and `capabilities` to the backend. The backend prunes capabilities that don’t belong to enabled modules and adds missing defaults.

RequireCapability behavior for Tenant Admin/Staff (Option B) is unchanged from earlier fixes.

---

### How to use it now
1) As Super Admin, open Settings for the tenant (e.g., ss-salon):
   - Enable desired modules (for example: `salon`, `store`, and usually `core`).
   - Check the capabilities within those modules as needed (or click “Select defaults”).
   - Click “Save Capabilities”.
2) Confirm the tenant settings reflect your selection:
   - `GET /v1/tenants/ss-salon` should show e.g.:
     - `modules`: `["core", "salon", "store"]` (whatever you selected)
     - `capabilities`: includes defaults for enabled modules plus any extra you selected.
3) Log in as the Tenant Admin (Option B):
   - The pages/routes under enabled modules should be visible and usable immediately (no per‑user caps required for Tenant Admin).
   - Example: If `store` is enabled and `store.catalog` capability is present, `GET /v1/tenants/ss-salon/catalog/products` should return 200.
4) For Staff users:
   - Assign them specific caps (subset of tenant caps) in the Users screen or via API.
   - Staff will only see/use what both the tenant and their user caps allow.

---

### Notes on existing tenants
- Existing tenants that previously only had capabilities may now need `modules` set explicitly by Super Admin to pass the reinstated `ensure_module_enabled` checks. Use the Settings page to enable the correct modules and re‑save.

---

### Troubleshooting checklist if a Tenant Admin still can’t see a module
- Verify tenant settings:
  - `GET /v1/tenants/<tenant>` → confirm `modules` includes the module, and `capabilities` includes the capability.
- Verify the URL uses the correct tenant:
  - For Tenant Admin, the path must match their token tenant (scope check enforces this).
- If a specific route returns 403, the `detail` tells you exactly why:
  - `Module 'store' is not enabled for this tenant` → enable the module.
  - `Capability 'store.catalog' is not enabled for this tenant` → enable that capability in Settings.
  - `User lacks capability ...` (only for staff) → add the capability to that staff user.

---

### What I suggest testing now
- For `ss-salon`:
  1) Enable modules `core` and `salon` (and `store` if you want store features) in Settings; click Save.
  2) Ensure the expected capabilities are present (defaults will be included automatically).
  3) Log in as `ss-salon@example.com` and visit a capability‑guarded page (e.g., Appointments for `salon`). It should be visible and functional.

If anything still doesn’t behave as above, tell me:
- The `modules` and `capabilities` arrays from `GET /v1/tenants/ss-salon`
- One failing API call’s status and `detail`
- Which page is hidden in the UI
I’ll pinpoint the exact line to adjust. 