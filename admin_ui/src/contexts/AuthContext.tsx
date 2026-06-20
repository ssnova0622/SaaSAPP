/**
 * AuthContext — single source of truth for identity and permissions.
 *
 * The JWT is parsed exactly ONCE here. Every other file that needs role/caps
 * must call `useAuth()` — never re-parse the token directly.
 *
 * Exposed:
 *   user          — { email, tenant, role, displayName }
 *   caps          — Set<string> of lowercase capability IDs from the JWT
 *   isSuperAdmin  — role === 'super_admin'
 *   isTenantAdmin — role === 'tenant_admin'
 *   isStaff       — role === 'staff'
 *   hasCap(cap)   — true when user has the cap (or is admin/super)
 *   hasAnyCap([]) — true when any of the caps match
 *   logout / refreshUser
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { tokenStore } from '../api/axios'
import { clearTenantSettingsCache } from '../api/tenants'

export interface AuthUser {
  email: string
  tenant: string | null
  role: string
  displayName: string
}

interface AuthState {
  user: AuthUser | null
  caps: Set<string>
  loading: boolean
  isSuperAdmin: boolean
  isTenantAdmin: boolean
  isStaff: boolean
  /** True for super_admin and tenant_admin. Staff: check hasCap() instead. */
  hasFullAccess: boolean
  /** Check if user holds a specific capability. Always true for super_admin/tenant_admin. */
  hasCap: (cap: string) => boolean
  /** Check if user holds any of the supplied capabilities. */
  hasAnyCap: (caps: string[]) => boolean
  logout: () => void
  refreshUser: () => void
}

function parseToken(tok: string | null): { user: AuthUser | null; caps: Set<string> } {
  if (!tok) return { user: null, caps: new Set() }
  try {
    const payload = JSON.parse(atob(tok.split('.')[1] || ''))
    const email = String(payload?.email ?? payload?.sub ?? '')
    if (!email) return { user: null, caps: new Set() }
    const tenant = payload?.tenant != null ? String(payload.tenant) : null
    const role = String(payload?.role ?? 'staff').toLowerCase()
    const displayName = String(payload?.display_name ?? payload?.name ?? email.split('@')[0])
    const rawCaps: string[] = Array.isArray(payload?.caps)
      ? payload.caps.map((c: unknown) => String(c).toLowerCase())
      : []
    return {
      user: { email, tenant, role, displayName },
      caps: new Set(rawCaps),
    }
  } catch {
    return { user: null, caps: new Set() }
  }
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [{ user, caps }, setAuth] = useState<{ user: AuthUser | null; caps: Set<string> }>(() =>
    parseToken(tokenStore.get())
  )
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setAuth(parseToken(tokenStore.get()))
    setLoading(false)
  }, [])

  const logout = useCallback(() => {
    try { clearTenantSettingsCache() } catch { /* ignore */ }
    try {
      Object.keys(sessionStorage)
        .filter((k) => k.startsWith('wa_msg_bundle:'))
        .forEach((k) => sessionStorage.removeItem(k))
    } catch { /* ignore */ }
    try { localStorage.removeItem('selected_tenant') } catch { /* ignore */ }
    tokenStore.clear()
    setAuth({ user: null, caps: new Set() })
    window.location.assign('/login')
  }, [])

  const refreshUser = useCallback(() => {
    setAuth(parseToken(tokenStore.get()))
  }, [])

  const role = user?.role ?? ''
  const isSuperAdmin = role === 'super_admin'
  const isTenantAdmin = role === 'tenant_admin'
  const isStaff = role === 'staff'
  const hasFullAccess = isSuperAdmin || isTenantAdmin

  const hasCap = useCallback(
    (cap: string): boolean => {
      if (hasFullAccess) return true
      return caps.has(cap.toLowerCase())
    },
    [caps, hasFullAccess]
  )

  const hasAnyCap = useCallback(
    (capList: string[]): boolean => capList.some((c) => hasCap(c)),
    [hasCap]
  )

  const value = useMemo<AuthState>(
    () => ({ user, caps, loading, isSuperAdmin, isTenantAdmin, isStaff, hasFullAccess, hasCap, hasAnyCap, logout, refreshUser }),
    [user, caps, loading, isSuperAdmin, isTenantAdmin, isStaff, hasFullAccess, hasCap, hasAnyCap, logout, refreshUser]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
