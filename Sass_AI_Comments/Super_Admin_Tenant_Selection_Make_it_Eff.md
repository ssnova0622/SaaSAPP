### A quick improvement pass to make Super Admin tenant selection more efficient

Your app already centralizes tenant selection and broadcasts changes. To make it more efficient for Super Admins, apply these targeted optimizations (no UX change, better responsiveness and resilience):

1) Debounce duplicate reloads on rapid tenant switches
- Problem: rapid switching can fire multiple `useEffect` loads concurrently on many pages.
- Improvement: wrap page loaders with a simple abort-guard.
```ts
// pattern
const reqId = useRef(0)
async function load(){
  if(!tenant) return
  const id = ++reqId.current
  setLoading(true)
  try {
    const res = await apiCall(...)
    if (id !== reqId.current) return // ignore stale
    setState(res)
  } finally {
    if (id === reqId.current) setLoading(false)
  }
}
```

2) Preselect and persist last‑used tenant fast
- Already done in `useEffectiveTenant` via `localStorage('selected_tenant')`. Ensure initial render uses this value synchronously to avoid a "blank" phase. Your hook already sets state from `localStorage` first; that’s good.

3) Prefetch tenant capabilities/settings after selection
- Problem: opening a page immediately after a switch can trigger multiple identical `/tenants/{id}` calls.
- Improvement: memoize the latest fetched `TenantSettings` in a simple in‑memory cache keyed by tenant. Expose a helper (read‑through cache) so pages read from cache first and only fetch once per tenant.
```ts
// admin_ui/src/api/tenantSettingsCache.ts
const cache = new Map<string, any>()
export async function getTenantSettingsCached(tenant: string, fetcher: ()=>Promise<any>){
  if (cache.has(tenant)) return cache.get(tenant)
  const val = await fetcher()
  cache.set(tenant, val)
  return val
}
export function clearTenantSettingsCache(){ cache.clear() }
```
- Use it where `getTenantSettings` is called frequently (e.g., `AppShell`, Users page).

4) Broadcast a single, consistent event
- You already use `tenant-change`. Keep it; avoid additional custom events to minimize listeners.
- Consider adding the previous tenant in `detail` if you later need differential updates: `{ current, previous }`.

5) Guard against unavailable tenant on startup
- If `listTenants` fails, keep the last known tenant from `localStorage` instead of clearing to empty.
- Your try/catch in `useEffectiveTenant` already prevents crashes; optionally show a toast if no tenants are available.

6) Ensure Store pages refresh efficiently
- They still use `useTenant` but it already listens to `tenant-change`; performance is fine. If you notice lag, migrate them to `useEffectiveTenant` to avoid extra `localStorage` reads.

7) Micro‑UX tweak (optional)
- Disable selector briefly while a tenant change is in flight to prevent accidental double switches. Maintain a tiny local `switching` state in `TenantSelector` and re-enable when the first data response returns (or after a short timeout).

These changes keep your current behavior intact while reducing redundant requests and eliminating stale updates during fast tenant switches. If you want, I can implement the caching helper and load guards next.