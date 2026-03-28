### Plan to ensure tenant selection refreshes page data immediately

1. Verify global tenant source-of-truth and selector placement (AppShell).  
- Confirm `TenantSelector` renders only in the AppBar’s top-left.  
- Ensure `TenantBadge` shows only for non‑super users.  
- Validate `useEffectiveTenant` persists to `localStorage('selected_tenant')` and dispatches `tenant-change` for same‑tab updates.

2. Audit pages for tenant-driven refetch behavior.  
- Check effects depend on `tenant` and call loaders on change (e.g., `useEffect(...,[tenant])`).  
- Reconfirm updated pages: Users, Settings, Promotions (New/Detail), Followups, Retention, Professionals, WhatsApp (Config, MenusIndex, MenuEditor).

3. Validate Store module pages (Carts, Orders, Products, Categories).  
- If any still use legacy `useTenant`, ensure they listen to `tenant-change`; migrate to `useEffectiveTenant` only if immediate refresh is not occurring.

4. Manual verification across roles.  
- Super Admin: switch tenants; verify all listed pages update immediately without reload.  
- Tenant Admin/Staff: selector hidden; tenant locked to JWT; data scoped correctly.

5. Optional hardening.  
- Add a lightweight E2E smoke script to switch tenants and assert API calls include the selected tenant.

6. Close out.  
- Summarize findings and confirm no impact to tenant logins while ensuring all data reflects the active tenant selection.