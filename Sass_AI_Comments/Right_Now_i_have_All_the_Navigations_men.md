### Goal
Make the left navigation dynamic per-tenant so you can:
- Rename menu labels from the Admin panel (e.g., change “Carts” to “Stock & Carts”).
- Show/hide items per tenant, and reorder items/groups.
- Keep module/capability rules intact (items still disappear if the tenant doesn’t have access, even if enabled in the config).

Below is a minimal, safe approach that uses your existing tenant settings infrastructure — no major backend changes required.

### What you already have we can reuse
- Tenant settings endpoints and storage:
  - Backend storage: `Storage.get_tenant_settings(tenant)` and `Storage.update_tenant_settings(tenant, updates)`
  - Router: `app/routers/tenants.py` exposes “Admin (JWT) endpoints for tenant settings” (`GET`/`PUT`), guarded by tenant/module/capability checks.
- Module + capability gating (used across your routes/components) so we can filter menu items server- and client-side.

### Data model for dynamic navigation (tenant-scoped)
Add a `nav_config` object inside tenant settings (no new collection needed):
```
nav_config: {
  version: 1,
  groups: [
    {
      id: "store",
      label_override: "Store",   // Optional: override group label
      order: 10,
      items: [
        {
          id: "products",
          route: "/store/products",
          label_default: "Products",
          label_override: "",     // Admin can set e.g., "Catalog"
          enabled: true,
          order: 10,
          required_modules: ["store"],
          required_capabilities: ["store.catalog"],
          visible_for_roles: ["admin","manager"],
          icon: "Inventory2Outlined"
        },
        {
          id: "inventory",
          route: "/store/inventory",
          label_default: "Inventory",
          label_override: "Stock",
          enabled: true,
          order: 20,
          required_modules: ["store"],
          required_capabilities: ["store.catalog"],
          visible_for_roles: ["admin","manager"],
          icon: "WarehouseOutlined"
        },
        {
          id: "carts",
          route: "/store/carts",
          label_default: "Carts",
          label_override: "Stock & Carts", // Example rename from Admin panel
          enabled: true,
          order: 30,
          required_modules: ["store"],
          required_capabilities: ["store.orders"],
          visible_for_roles: ["admin","sales"],
          icon: "ShoppingCartOutlined"
        },
        {
          id: "orders",
          route: "/store/orders",
          label_default: "Orders",
          label_override: "",
          enabled: true,
          order: 40,
          required_modules: ["store"],
          required_capabilities: ["store.orders"],
          visible_for_roles: ["admin","sales"],
          icon: "ReceiptLongOutlined"
        }
      ]
    }
  ]
}
```
Notes:
- `label_default` lives in code as a fallback; `label_override` lives in settings. The UI shows override if non-empty.
- Do not let Admins change `id` or `route` — only label/enable/order and visibility.
- Keep `required_modules`/`required_capabilities` read-only metadata (for information); actual gating remains authoritative.

### Admin UI: Navigation Manager (Settings page)
Add a page: Admin → Settings → Navigation
- Read `GET /tenants/{tenant}/settings` → `nav_config` (if absent, show defaults).
- Features:
  - Toggle visibility (`enabled`) per item.
  - Edit `label_override` text with validation (non-empty, <= 40 chars), leave blank to use default.
  - Drag-and-drop reorder within a group (update `order`).
  - Optional group label override and group sort order.
  - Preview panel on the right that mirrors the left nav in real-time.
- Save → `PUT /tenants/{tenant}/settings` with `{ nav_config: ... }`.
- Permissions: Only tenant admins/super-admins see this page.

### Runtime: render dynamic menu
- On app load (and on tenant switch) fetch `nav_config` and merge with baked-in defaults.
- Filter items by:
  1) `enabled === true` in `nav_config`
  2) Current user role in `visible_for_roles`
  3) Module/capability gating (even if enabled, hide if module/capability missing for the tenant)
- Use `label_override || label_default` for the visible label.
- Cache in a Nav context; provide a “Refresh” button on the Settings page.

### About “if stock – carts i have to update inventory like”
- If your intent is to rename “Carts” → “Stock & Carts”, the above supports it (label override).
- If you want a new combined screen (e.g., a quick page to adjust inventory while creating a cart):
  - Add a new nav item `id: "stock_and_carts"` with route `/store/stock-and-carts`.
  - Initially route it to your current Carts page with a right sidebar that shows inventory of typed SKUs (this is a UI enhancement, independent from nav config itself).
- Stock updates already happen at checkout and at order edits (based on previous work). Navigation changes won’t affect that logic.

### Minimal backend work (if needed)
You already have `get_tenant_settings`/`update_tenant_settings`. If there isn’t a specific field yet:
- Validation on `PUT` should restrict editable fields to `label_override`, `enabled`, and `order` (plus group label/order). Ignore/strip unknown ids/fields.
- Optionally add a specific pair of endpoints for nav for clarity:
  - `GET /tenants/{tenant}/settings/nav`
  - `PUT /tenants/{tenant}/settings/nav`
But it’s fine to use the existing generic settings endpoints.

### Example: change labels from Admin panel
- Open Admin → Settings → Navigation
- Find item “Carts”, set Label to “Stock & Carts”, keep enabled.
- Save. Reload the app: left menu now shows “Stock & Carts” pointing to the same Carts route.

### Safeguards
- Never let a misconfigured label break routing (route is immutable, id is immutable).
- If `GET settings` fails, fall back to defaults and show a small warning toast (super-admin only).
- If the tenant disables a module/capability, the item is hidden regardless of `enabled`.

### Optional niceties (later)
- Per-locale label overrides (i18n): `label_overrides: { en: "Carts", ta: "…" }`.
- Badges (e.g., Low stock count) via a small badge provider hook that maps ids (like `inventory`) to computed counts.
- Import/export nav config JSON for quick cloning across tenants.

### Quick confirmation questions
1) Do you want a dedicated “Navigation” page under Settings now, or is it okay to place nav config in the existing Tenant Settings page for the MVP?
2) Is renaming and toggling visibility enough for the first cut, or do you also want drag-and-drop reordering from day one?
3) Do you want a new “Stock & Carts” combined page, or just a label rename for “Carts”?

Once you confirm, I’ll wire the Settings UI and the runtime menu loader to make labels and visibility fully dynamic per tenant.