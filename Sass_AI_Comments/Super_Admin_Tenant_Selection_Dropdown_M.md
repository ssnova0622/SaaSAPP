### Status: single Super Admin tenant dropdown in one place

- The tenant selector is now rendered only once in the AppBar’s left side via `admin_ui/src/components/AppShell/AppShell.tsx` using `TenantSelector`. It has been removed from the Drawer and from all individual pages.
- Pages that previously had their own selector (e.g., Users, Settings, WhatsApp Config, WhatsApp Menus/Editor) now rely on the single global selector. Non‑super users only see a read‑only `TenantBadge` in the same spot.
- All updated pages refresh their data when the tenant changes because they depend on `useEffectiveTenant` and listen for changes.

If you still see a duplicate selector anywhere, tell me the page/route and I’ll remove it, but based on current code it should appear only in the top‑left AppBar.