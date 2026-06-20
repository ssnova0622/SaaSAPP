import { NavLink } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import { getTenantSettings, type TenantSettings } from '../api/tenants'
import { useEffectiveTenant } from '../hooks/useEffectiveTenant'
import { useAuth } from '../contexts/AuthContext'
import { TenantSelector, TenantBadge } from './TenantContext'
import {
  SUPER_ADMIN_NAV,
  TENANT_NAV,
  SALON_NAV,
  STORE_NAV,
  AI_NAV,
  WHATSAPP_NAV,
} from '../config/nav'

function navLinkClass(isActive: boolean) {
  return `flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors border-l-2 ${
    isActive
      ? 'bg-[#2563eb] text-white border-[#60a5fa] shadow-md'
      : 'border-transparent text-[#cbd5e1] hover:bg-[#334155] hover:text-white'
  }`
}

export default function Sidebar() {
  const { user, logout, caps } = useAuth()
  const { effectiveTenant: tenant, isSuper } = useEffectiveTenant()
  const role = user?.role ?? 'staff'
  const userCaps = Array.from(caps)
  const [modules, setModules] = useState<string[]>([])
  const [capabilities, setCapabilities] = useState<string[]>([])
  const [category, setCategory] = useState<string | undefined>(undefined)

  useEffect(() => {
    async function fetchTenantCfg() {
      if (!tenant) {
        setModules([])
        setCapabilities([])
        setCategory(undefined)
        return
      }
      try {
        const s: TenantSettings = await getTenantSettings(tenant)
        setModules((s.modules || []).map((m) => m.toLowerCase()))
        setCapabilities((s.capabilities || []).map((c) => c.toLowerCase()))
        setCategory(s.category)
      } catch {
        setModules([])
        setCapabilities([])
        setCategory(undefined)
      }
    }
    fetchTenantCfg()
    function onTenantSettingsChanged(e: CustomEvent<{ tenant?: string }>) {
      const changedTenant = e?.detail?.tenant
      if (!changedTenant || changedTenant === tenant) fetchTenantCfg()
    }
    window.addEventListener('tenantSettingsChanged', onTenantSettingsChanged as EventListener)
    return () => window.removeEventListener('tenantSettingsChanged', onTenantSettingsChanged as EventListener)
  }, [tenant])

  const visibleSuperAdmin = useMemo(() => {
    return SUPER_ADMIN_NAV.filter((item) => {
      if (role !== 'super_admin') return false
      if (item.cap === 'super_admin_only') return true
      const capId = String(item.cap).toLowerCase()
      if (capId === 'core.tenants') return true
      return capabilities.includes(capId)
    })
  }, [role, capabilities])

  const visibleTenant = useMemo(() => {
    return TENANT_NAV.filter((item) => {
      if (item.cap === null) return true
      const capId = String(item.cap).toLowerCase()
      if (role === 'super_admin') {
        if (!tenant) return false
        return capabilities.includes(capId)
      }
      if (role === 'tenant_admin') {
        if (capId === 'core.dashboard' || capId === 'core.dashboard.view') {
          return capabilities.includes('core.dashboard') || capabilities.includes('core.dashboard.view')
        }
        return capabilities.includes(capId)
      }
      const tenantHas =
        capabilities.includes(capId) ||
        (capId === 'core.dashboard' && capabilities.includes('core.dashboard.view'))
      const userHas =
        userCaps.includes(capId) ||
        (capId === 'core.dashboard' && userCaps.includes('core.dashboard.view'))
      return tenantHas && userHas
    })
  }, [role, tenant, capabilities, userCaps])

  const visibleSalon = useMemo(() => {
    const hasSalonOrClinic = modules.includes('salon') || modules.includes('clinic')
    if (!hasSalonOrClinic) return []
    const aiNoShowEnabled = modules.includes('ai') && capabilities.includes('ai.no_show')
    return SALON_NAV.filter((n) => {
      if (n.to === '/no-show-blocked' && !aiNoShowEnabled) return false
      if (!n.cap) return true
      const viewCap = n.cap + '.view'
      const tenantHas = capabilities.includes(n.cap) || capabilities.includes(viewCap)
      // super_admin sees whatever the tenant has enabled (so they can verify the config)
      if (role === 'super_admin') return tenantHas
      const userHas = role === 'tenant_admin' ? tenantHas : userCaps.includes(n.cap) || userCaps.includes(viewCap)
      return tenantHas && userHas
    })
  }, [modules, role, capabilities, userCaps])

  const visibleStore = useMemo(() => {
    return STORE_NAV.filter((item) => {
      const cap = item.cap!
      const viewCap = cap + '.view'
      const tenantHas = capabilities.includes(cap) || capabilities.includes(viewCap)
      if (role === 'super_admin') return tenantHas
      const userHas = role === 'tenant_admin' ? tenantHas : userCaps.includes(cap) || userCaps.includes(viewCap)
      return tenantHas && userHas
    })
  }, [role, capabilities, userCaps])

  const showAI = useMemo(() => {
    const hasAIModule = modules.includes('ai')
    const hasAnyAICap = capabilities.some((c) => String(c).toLowerCase().startsWith('ai.'))
    if (!hasAIModule || !hasAnyAICap) return false
    if (role === 'super_admin') return true
    if (role === 'tenant_admin') return true
    return userCaps.some((c) => String(c).toLowerCase().startsWith('ai.'))
  }, [modules, capabilities, role, userCaps])

  const visibleAI = useMemo(() => {
    if (!showAI) return []
    return AI_NAV.filter((item) => {
      if (!item.cap) return true
      const capId = String(item.cap).toLowerCase()
      const tenantHas = capabilities.includes(capId)
      if (role === 'super_admin') return tenantHas
      const userHas = userCaps.includes(capId)
      return tenantHas && userHas
    })
  }, [showAI, role, userCaps, capabilities])

  const visibleWhatsApp = useMemo(() => {
    const cap = 'core.whatsapp_menu'
    const tenantHas = capabilities.includes(cap)
    if (role === 'super_admin') return tenantHas ? WHATSAPP_NAV : []
    const userHas = role === 'tenant_admin' ? tenantHas : userCaps.includes(cap)
    return tenantHas && userHas ? WHATSAPP_NAV : []
  }, [role, capabilities, userCaps])

  const roleLabel = role === 'super_admin' ? 'Super Admin' : role === 'tenant_admin' ? 'Admin' : 'Staff'

  const renderSection = (title: string, items: typeof TENANT_NAV) => {
    if (!items.length) return null
    return (
      <div key={title} className="mb-1">
        <div className="px-3 pt-3 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-[#64748b]">
          {title}
        </div>
        <div className="space-y-0.5">
          {items.map((item) => {
            const label = category === 'clinic' && item.to === '/professionals' ? 'Doctors' : item.label
            return (
              <NavLink
                key={`${title}-${item.to}`}
                to={item.to}
                end
                className={({ isActive }) => navLinkClass(isActive)}
              >
                {label}
              </NavLink>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <aside className="w-64 min-h-screen bg-[#1e293b] border-r border-[#334155] flex flex-col shrink-0">
      <div className="p-4 border-b border-[#334155]">
        <h1 className="text-lg font-semibold text-[#f1f5f9] tracking-tight">{roleLabel}</h1>
        {user?.email && (
          <p className="text-xs text-[#94a3b8] mt-0.5 truncate" title={user.email}>
            {user.email}
          </p>
        )}
        {!isSuper && user?.tenant && <p className="text-xs text-[#64748b] mt-1">Tenant: {user.tenant}</p>}
        <div className="mt-3">{isSuper ? <TenantSelector /> : <TenantBadge />}</div>
      </div>
      <nav className="flex-1 p-2 overflow-y-auto">
        {renderSection('Super Admin', visibleSuperAdmin)}
        {renderSection('Tenant', visibleTenant)}
        {renderSection('Salon', visibleSalon)}
        {renderSection('Store', visibleStore)}
        {renderSection('AI', visibleAI)}
        {renderSection('WhatsApp', visibleWhatsApp)}
      </nav>
      <div className="p-3 border-t border-[#334155]">
        <button
          type="button"
          onClick={logout}
          className="w-full px-3 py-2.5 text-left text-sm text-[#94a3b8] hover:bg-[#334155] hover:text-white rounded-lg transition-colors"
        >
          Sign out
        </button>
      </div>
    </aside>
  )
}
