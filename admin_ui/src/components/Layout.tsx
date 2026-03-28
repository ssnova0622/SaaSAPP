import { Outlet } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useEffectiveTenant } from '../hooks/useEffectiveTenant'
import { getTenantSettings } from '../api/tenants'
import Sidebar from './Sidebar'
import SelectTenantModal from './SelectTenantModal'

/**
 * Main layout: sidebar + content. For Super Admin with no tenant selected, shows a modal to pick one.
 * Tenant can be switched anytime from the left panel. All data loads based on the selected tenant.
 * Shows tenant display name at top when set, otherwise tenant ID.
 */
export default function Layout() {
  const { effectiveTenant: tenant, setEffectiveTenant, isSuper } = useEffectiveTenant()
  const [offline, setOffline] = useState(false)
  const [displayName, setDisplayName] = useState<string | null>(null)

  const fetchDisplayName = () => {
    if (!tenant) return
    getTenantSettings(tenant)
      .then((s) => setDisplayName(s?.display_name?.trim() || null))
      .catch(() => setDisplayName(null))
  }
  useEffect(() => {
    if (!tenant) {
      setDisplayName(null)
      return
    }
    fetchDisplayName()
  }, [tenant])
  useEffect(() => {
    if (!tenant) return
    const handler = () => fetchDisplayName()
    window.addEventListener('tenantSettingsChanged', handler)
    return () => window.removeEventListener('tenantSettingsChanged', handler)
  }, [tenant])

  useEffect(() => {
    function update() {
      setOffline(typeof navigator !== 'undefined' && !(navigator as any).onLine)
    }
    update()
    window.addEventListener('online', update)
    window.addEventListener('offline', update)
    return () => {
      window.removeEventListener('online', update)
      window.removeEventListener('offline', update)
    }
  }, [])

  const showSelectTenantModal = isSuper && !tenant
  const tenantLabel = (displayName && displayName.length > 0) ? displayName : tenant

  return (
    <div className="flex min-h-screen bg-[#0f172a]">
      <Sidebar />
      <main className="flex-1 overflow-auto p-6 lg:p-8">
        {tenant && (
          <div className="mb-3 rounded-lg border border-[#334155] bg-[#1e293b]/80 px-4 py-2 flex items-center gap-2">
            <span className="text-sm text-[#94a3b8]">Tenant:</span>
            <span className="font-bold text-lg bg-gradient-to-r from-[#38bdf8] via-[#a78bfa] to-[#f472b6] bg-clip-text text-transparent">{tenantLabel}</span>
          </div>
        )}
        {offline && (
          <div className="mb-4 rounded-lg border border-[#eab308]/40 bg-[#eab308]/10 px-4 py-2.5 text-[#fde047] text-sm">
            You are offline. Some actions may be unavailable. We will retry when back online.
          </div>
        )}
        <Outlet key={tenant || 'no-tenant'} />
      </main>
      <SelectTenantModal open={showSelectTenantModal} onSelect={(t) => setEffectiveTenant(t)} />
    </div>
  )
}
