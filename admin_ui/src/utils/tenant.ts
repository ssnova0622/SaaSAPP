/**
 * Append or replace the tenant query parameter in a URL/path.
 * Preserves existing query params and hash.
 */
export function withTenantParam(url: string, tenant: string): string {
  try {
    const hasProtocol = /^https?:\/\//i.test(url)
    const base = hasProtocol ? url : `http://x${url.startsWith('/') ? '' : '/'}${url}`
    const u = new URL(base)
    if (tenant) {
      u.searchParams.set('tenant', tenant)
    } else {
      u.searchParams.delete('tenant')
    }
    const out = u.pathname + (u.search ? `?${u.searchParams.toString()}` : '') + (u.hash || '')
    return hasProtocol ? u.toString() : out
  } catch {
    // Fallback: naive append
    if (!tenant) return url
    const [path, hash] = url.split('#', 2)
    const sep = path.includes('?') ? '&' : '?'
    return `${path}${sep}tenant=${encodeURIComponent(tenant)}${hash ? `#${hash}` : ''}`
  }
}
