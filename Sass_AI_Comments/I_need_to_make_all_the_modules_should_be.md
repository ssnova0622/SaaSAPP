### Plan to make all modules private by default and visible only to Super Admin unless explicitly assigned
I will implement the following adjustments so that:
- Only Super Admin sees/uses all modules by default.
- Super Admin assigns modules and capabilities per tenant and per user.
- For non–Super Admin users (tenant_admin/staff), if no module/capability is assigned, they will only see the Dashboard (no Settings, Tenants, Users, Customers, Staff, Promotions, etc.).

### Backend enforcement (authoritative)
Already adjusted or to be confirmed:
- No auto-enabling modules/capabilities from tenant category. `Storage.get_tenant_settings()` returns empty `modules` and `capabilities` unless assigned by Super Admin.
- Capability guard requires BOTH:
  - Tenant has the capability enabled (tenant-level), and
  - The user has that capability in their JWT `caps` (user-level), except Super Admin. I’ve updated `ensure_capability_enabled()` to enforce this for both `tenant_admin` and `staff` accounts (and any `admin` role other than `super_admin`).
- Scope guard `ensure_tenant_scope()` blocks cross-tenant access for tenant_admin/staff.
- Super Admin is required to update tenants’ `modules`/`capabilities`.

Result: Even if a tenant has a capability enabled, a user must also have it in their token `caps` or it’s a 403. Super Admin bypasses this restriction by design.

### Admin UI gating (to implement now)
- Core menus (Settings, Tenants, Users, Customers, Staff, Promotions, Follow-ups, Reports, Retention) must be hidden unless the current user has the required capability.
- If a non–Super Admin user has no `caps` at all, navigation must only show Dashboard.
- Menus appear only when BOTH tenant capability and user capability exist. Example mappings:
  - Settings: core.settings (new capability)
  - Tenants: core.tenants (Super Admin only)
  - Users: core.users (Super Admin and tenant_admin)
  - Customers: core.customers
  - Staff: core.staff
  - Promotions: core.promotions
  - Follow-ups: core.followups
  - Reports: core.reports
  - Retention: core.retention
  - Salon pages: salon.professionals, salon.appointments
  - Store pages:
    - Orders/Carts: store.orders
    - Catalog: store.catalog

If you confirm these capability IDs, I will:
- Extend the registry (`app/modules/registry.py`) to include new core capabilities (core.settings, core.tenants, core.users) and set defaults to false so that Super Admin must assign them.
- Update UI sidebar (`AppShell`) to show links only when required capability is present in BOTH tenant settings and user `caps`.
- Add deep-link guards for routes so direct URL access is blocked with a friendly message if the capability is missing.

### Token/user capability assignment
- Super Admin can assign capabilities per user (already supported via Users UI). For tenant_admin/staff, this governs what menus appear.
- When a user has no caps: show only Dashboard (plus banner indicating limited access).

### Minimal UI changes planned
- Update `AppShell` filtering logic to check tenant capabilities AND user caps for every menu entry. Super Admin continues to see everything.
- Add a route guard `<RequireCapability id="..." />` to prevent deep-links when capability is missing.

### Optional: Capability presets
- In Super Admin → Settings → Modules, I can add a “default presets” button to quickly assign core capabilities to tenant_admin (e.g., core.users, core.customers) and store/salon capabilities as needed. This is optional.

### Next steps
- Confirm capability IDs for Settings/Tenants/Users (e.g., `core.settings`, `core.tenants`, `core.users`).
- I will then:
  1) Extend registry and ensure tenant capabilities include these core caps (all default false).
  2) Update UI navigation to require both tenant capability and user cap for each item.
  3) Add `<RequireCapability>` wrappers to routes.

Please confirm the capability names for Settings, Tenants, and Users (or tell me your preferred names), and I’ll apply the changes immediately.