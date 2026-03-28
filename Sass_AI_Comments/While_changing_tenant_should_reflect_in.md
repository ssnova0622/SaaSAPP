### Plan to ensure tenant changes reflect across all pages

1) Confirm single source of truth
- Keep `useEffectiveTenant` as the global tenant state (Super Admin: localStorage + `tenant-change` event; non‑super: JWT-locked).
- Verify `AppShell` renders the only selector at top‑left and exports the current tenant everywhere via hooks.

2) Audit and align all pages
- Ensure every page that loads tenant-scoped data reads `effectiveTenant` and refetches on change: dependency arrays include `tenant` (e.g., `useEffect(...,[tenant, ...])`).
- Replace any lingering `useTenant` usage with `useEffectiveTenant` or confirm they listen to `tenant-change` correctly.

3) Fix outliers immediately
- WhatsApp: MenusIndex/Editor/Config should use the global tenant (no in-page selector for Super Admin). If any still have local tenant state, bind them to `useEffectiveTenant`.
- Store module: Orders, Carts, Products, Categories — confirm refetch on tenant switch; migrate to `useEffectiveTenant` if needed.

4) Prevent stale updates during fast switching
- Add lightweight request guards in loaders to ignore stale responses when tenant changes rapidly (request id ref guard pattern).

5) Capability- and module-gated navigation
- Keep `AppShell` gating dependent on the active tenant’s `modules`/`capabilities` and user caps; AI Predictions additionally gated by the per-tenant flag.

6) Verification checklist
- Super Admin: switch tenants rapidly across Users, Settings, Promotions, Followups, Retention, Professionals, Store (Orders/Products/Categories), WhatsApp (Config/Menus/Editor) — all lists/cards refetch immediately.
- Tenant Admin/Staff: selector hidden; badge visible; pages remain scoped to JWT tenant.

7) Optional optimization
- Cache `getTenantSettings(tenant)` per tenant in-memory to avoid duplicate fetches across pages after a switch.

Deliverables
- Minimal code updates (only where outliers found), plus an optional small cache helper for settings and request-guard pattern added to affected pages.