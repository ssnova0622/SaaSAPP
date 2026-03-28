# Permission model (role-based, plugin-style)

## Backend

- **Dependencies** (`app/routers/deps.py`):
  - `ensure_capability_any_enabled([cap_ids])` – tenant (and staff user) must have at least one of the caps.
  - `ensure_permission(scope, action)` – same idea with scope/action naming; maps scope to capability list (e.g. `salon.appointments` → `["salon.appointments", "salon.appointments.view", ...]`). Use for route protection: `Depends(ensure_permission("salon.appointments", "create"))`.
  - `ensure_tenant_scope()` – restricts tenant_admin/staff to their tenant.
  - `ensure_super_admin` – Super Admin only.

- **Roles:** `super_admin` (all), `tenant_admin` (all for their tenant), `staff` (by user caps + tenant caps).

- **Granularity:** Today, having a capability (e.g. `salon.appointments`) grants read/create/update/delete for that scope. Future: add `scope.create`, `scope.delete` caps for finer control.

## Frontend

- **RequireCapability** – wrap routes/pages; requires tenant + user to have the cap (or alias).
- **useCapabilities** – hook with `canView*`, `canEdit*`, `canCreate*`, `canDelete*` per module, and generic **`can(scope, action)`** for read/create/update/delete. Use to show/hide create/edit/delete buttons: `if (can('salon.appointments', 'create')) ...`.

## Scope naming

- `core.settings`, `core.users`, `core.customers`, `core.reports`, `core.dashboard`, `core.followups`, `core.whatsapp_menu`
- `salon.appointments`, `salon.professionals`, `salon.services`, `salon.no_show_blocked`
- `store.orders`, `store.catalog`, …

Actions: `read`, `create`, `update`, `delete`. Backend uses `ensure_permission(scope, action)`; frontend uses `can(scope, action)`.
