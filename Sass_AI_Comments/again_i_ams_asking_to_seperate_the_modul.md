### Got it — you want modules separated again (Store/Salon as core modules), assignable per tenant
You’re asking to reintroduce “modules” as first‑class toggles (e.g., Store and Salon modules) that the Super Admin assigns to a tenant. After assignment, the tenant can use those modules. Capabilities remain as finer‑grained permissions within each module. That’s clear.

Below is a concrete proposal and a short list of confirmations I need to proceed.

---

### Proposed target model
- Modules: high‑level building blocks of the app (Core, Store, Salon, etc.).
- Capabilities: feature switches inside a module.
- Tenants:
  - Created dark: `modules: []`, `capabilities: []`.
  - Super Admin assigns `modules` (e.g., `store`, `salon`).
  - When saving, the backend normalizes capabilities: it auto‑includes each enabled module’s default capabilities (and any explicitly selected capabilities), storing them in `capabilities`.
- Access policy (unchanged Option B semantics):
  - Backend checks: `ensure_module_enabled('<module>')` AND `ensure_capability_enabled('<cap>')`.
  - Tenant Admin: bypass per‑user caps; they can use any capability enabled for their tenant.
  - Staff: must have the capability in their own `caps` AND the tenant must have it enabled.

---

### Minimal technical changes to get there
1) Registry
- Add back explicit module entries to `app/modules/registry.py`, e.g.:
  - Modules: `core`, `store`, `salon` (type = `module`).
  - Capabilities mapped to their module, with `default` flags.
- `normalize_selection(modules, capabilities)`:
  - Validate modules against registry.
  - Start with all default capabilities of selected modules.
  - Add any explicitly requested capabilities (only those belonging to selected modules).
  - Return normalized: `mods = [ ... ]`, `caps = [ ... ]` (lowercased, sorted, unique).

2) Backend checks
- `ensure_module_enabled(module_id)`:
  - Stop being a no‑op; read tenant settings and require `module_id` to be present in `modules`.
- `ensure_capability_enabled(cap_id)`:
  - Keep current Option B logic (Tenant Admin bypasses per‑user caps; Staff requires per‑user caps).

3) Tenant settings API
- `PUT /tenants/{tenant}`:
  - Accept both `modules` and `capabilities` (existing contract).
  - Use the new `normalize_selection()` to persist a coherent combination (modules drive default caps; explicit caps must belong to enabled modules).

4) Admin UI (Super Admin only)
- Settings → “Modules & Capabilities”:
  - Show a modules section: checkboxes for `store`, `salon`, (optionally `core`).
  - When modules change, gray out capabilities from modules that are not enabled.
  - On save, send both arrays.

5) Backward compatibility
- Existing tenants that only have `capabilities` but no `modules`:
  - On first update, we can infer minimal module set from the capabilities (e.g., any `store.*` → add `store`).
  - Or we leave untouched until Super Admin edits; routes will still be guarded by capability checks (and module no‑op won’t break) until modules are explicitly set.

---

### What I need you to confirm
1) Module list (now):
   - Confirm these: `store`, `salon`. Do you also want an explicit `core` module (for things like Settings/Users/Reports), or should those remain “always on” without a module gate?
2) Default capabilities per module:
   - For `store`: defaults = `store.orders`, `store.payments` (and optionally `store.catalog` if you want it on by default?).
   - For `salon`: defaults = `salon.professionals`, `salon.appointments`.
   - For `core` (if used): defaults = `core.users`, `core.settings` (etc.) or no defaults?
3) UI behavior:
   - Super Admin can toggle modules and then optionally fine‑tune capabilities inside those modules for each tenant. Correct?
4) Keep Option B for Tenant Admin?
   - Tenant Admin auto‑access to tenant capabilities; Staff still require per‑user caps. I will keep this unless you want to change it.

---

### Rollout steps (once you confirm)
- Update registry (modules + capability mapping).
- Reinstate module enforcement in `ensure_module_enabled`.
- Update normalization logic to respect modules.
- Update Admin UI to include a “Modules” section and tie capabilities to enabled modules.
- Verify: create tenant → assign `store` → Catalog/Orders appear for Tenant Admin; Staff see only assigned capabilities.

Please confirm the module list and defaults, especially:
- Modules: `["store", "salon"]` (and `"core"` yes/no?)
- Defaults per module as listed above (feel free to adjust)
Once you confirm, I’ll implement the changes end‑to‑end.