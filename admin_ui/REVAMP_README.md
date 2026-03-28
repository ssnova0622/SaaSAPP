# admin_ui – Revamp Summary

This folder has been revamped to **match the new admin-ui theme** (Tailwind, slate palette, sidebar layout) while **keeping all existing logic**.

## What changed

- **Theme:** Tailwind CSS v4 added. New layout uses `Layout` + `Sidebar` (replacing MUI AppShell).
- **Migrated to Tailwind:** Login, Dashboard, Promotions/Index, Customers/Index, WhatsApp/MenusIndex, TenantContext, RequireCapability, TimezoneSelect.
- **Still MUI (same logic):** All other pages and a few components (see project `docs/REVAMP_REPORT.md`). They can be migrated using the same pattern (replace MUI components with Tailwind equivalents; keep all state and API calls).

## Run

```bash
npm install
npm run dev
```

## Full documentation

See **`docs/REVAMP_REPORT.md`** in the project root for the complete change report and migration pattern for remaining pages.
