### Progress update — Phase 1 code changes started

I’ve begun implementing the agreed improvements with safe, minimal changes.

#### What’s done
- Tenant settings cache
  - Added a lightweight in‑memory read‑through cache for `getTenantSettings(tenant)` to reduce duplicate fetches during quick navigations/switches.
  - Cache is updated on `setTenantActive` and a `clearTenantSettingsCache()` helper is provided.
  - Wired cache clear on logout in `AppShell` so stale settings aren’t reused after session changes.
- Axios interceptors
  - Added `X-Client-Version` and `X-Requested-With` headers on every request (uses `VITE_APP_VERSION`/`VITE_COMMIT` if available).
  - Kept 401 handling (JWT expiry) → clears token and redirects to `/login`.
  - Implemented a one‑shot retry for GET requests when offline: waits for the browser to come online, then retries once.
  - Broadcasts a lightweight `api-error` event with `{ status, message }` so a unified banner/toast can be attached anywhere without coupling to axios.

#### Next steps (in this order)
1) Request guards
- Apply the request‑id guard pattern to loaders on key pages (Users, Products, Orders, Reports, Professionals, Appointments, Promotions, Followups, Retention) to ignore stale responses on rapid tenant switches.

2) Optional UI for error/offline
- Add a tiny global listener in the shell to show/hide a small offline banner and optionally show a unified error toast on `api-error`.

3) Verify
- Rapidly switch tenants across pages and ensure there are no stale flashes and fewer duplicate `/tenants/{id}` requests.

If you want me to proceed immediately with the request guards and the small offline/error banners, I’ll continue now and report back succinctly after those changes are in.