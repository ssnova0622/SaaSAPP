import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { tokenStore } from '../api/axios'
import { clearTenantSettingsCache } from '../api/tenants'

export interface AuthUser {
  email: string
  tenant: string | null
  role: string
}

interface AuthState {
  user: AuthUser | null
  loading: boolean
  isSuperAdmin: boolean
  logout: () => void
  /** Call after login to sync context with stored token so protected routes see the user. */
  refreshUser: () => void
}

function getStoredUser(): AuthUser | null {
  try {
    const tok = tokenStore.get()
    if (!tok) return null
    const payload = JSON.parse(atob(tok.split('.')[1] || ''))
    const email = String(payload?.email ?? payload?.sub ?? '')
    const tenant = payload?.tenant != null ? String(payload.tenant) : null
    const role = String(payload?.role ?? 'admin').toLowerCase()
    if (!email) return null
    return { email, tenant, role }
  } catch {
    return null
  }
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setUser(getStoredUser())
    setLoading(false)
  }, [])

  const logout = useCallback(() => {
    try {
      clearTenantSettingsCache()
    } catch {
      /* ignore */
    }
    try {
      Object.keys(sessionStorage)
        .filter((k) => k.startsWith('wa_msg_bundle:'))
        .forEach((k) => sessionStorage.removeItem(k))
    } catch {
      /* ignore */
    }
    try {
      localStorage.removeItem('selected_tenant')
    } catch {
      /* ignore */
    }
    tokenStore.clear()
    setUser(null)
    window.location.assign('/login')
  }, [])

  const refreshUser = useCallback(() => {
    setUser(getStoredUser())
  }, [])

  const isSuperAdmin = user?.role === 'super_admin'

  return (
    <AuthContext.Provider value={{ user, loading, isSuperAdmin, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
