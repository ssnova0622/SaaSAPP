import { ReactNode, useEffect, useState } from 'react'
import { getTenantSettings, TenantSettings } from '@api/tenants'
import { Alert } from '@components/ui/Alert'
import { tokenStore } from '@api/axios'
import { useEffectiveTenant } from '../hooks/useEffectiveTenant'

function useAuthClaims(){
  try{
    const tok = tokenStore.get()
    if(!tok) return { role:'admin', caps:[] as string[], tenant: null as string | null }
    const p = JSON.parse(atob(tok.split('.')[1]))
    const role = String(p?.role || 'admin').toLowerCase()
    const caps = Array.isArray(p?.caps) ? p.caps.map((c:string)=>String(c).toLowerCase()) : []
    const tenant = (p?.tenant ? String(p.tenant) : null)
    return { role, caps, tenant }
  }catch{ return { role:'admin', caps:[] as string[], tenant: null } }
}

const VIEW_CAP_ALIASES: Record<string, string[]> = {
  'core.dashboard': ['core.dashboard', 'core.dashboard.view'],
  'salon.services': ['salon.services', 'salon.services.view', 'salon.services.edit'],
  'salon.professionals': ['salon.professionals', 'salon.professionals.view'],
  'salon.appointments': ['salon.appointments', 'salon.appointments.view'],
  'salon.no_show_blocked': ['salon.no_show_blocked', 'salon.no_show_blocked.view'],
  'store.orders': ['store.orders', 'store.orders.view'],
  'core.reports': ['core.reports', 'core.reports.view'],
  'core.customers': ['core.customers', 'core.customers.view'],
  'core.settings': ['core.settings', 'core.settings.view'],
  'core.users': ['core.users', 'core.users.view'],
}

export default function RequireCapability({ cap, caps: capsProp, children }: { cap?: string, caps?: string[], children: ReactNode }){
  const { effectiveTenant: selectedTenant } = useEffectiveTenant()
  const { role, caps: userCaps, tenant: tokenTenant } = useAuthClaims()
  const [tenantCaps, setTenantCaps] = useState<string[]|null>(null)
  const capList = capsProp ?? (cap ? VIEW_CAP_ALIASES[cap] ?? [cap] : [])
  const capId = (cap || capList[0] || '').toLowerCase()

  useEffect(()=>{
    (async()=>{
      // Determine which tenant to fetch settings for
      const targetTenant = role === 'super_admin' ? selectedTenant : (tokenTenant || selectedTenant || '')
      // For non-super roles, require token tenant
      if(role !== 'super_admin' && !tokenTenant){ setTenantCaps([]); return }
      if(!targetTenant){ setTenantCaps([]); return }
      try{
        const s: TenantSettings = await getTenantSettings(targetTenant)
        setTenantCaps((s.capabilities||[]).map(c=>String(c).toLowerCase()))
      }
      catch{
        // If selected tenant was wrong (stale localStorage), try token tenant once
        if(role !== 'super_admin' && tokenTenant && targetTenant !== tokenTenant){
          try{
            const s: TenantSettings = await getTenantSettings(tokenTenant)
            setTenantCaps((s.capabilities||[]).map(c=>String(c).toLowerCase()))
            return
          }catch{/* ignore */}
        }
        setTenantCaps([])
      }
    })()
  },[role, tokenTenant, selectedTenant])

  // Super Admin: always allowed
  if(role === 'super_admin') return <>{children}</>
  // Wait for tenant caps to load — show loading state so pages don't appear broken
  if(tenantCaps === null) {
    return (
      <div className="min-h-[200px] flex items-center justify-center text-[#94a3b8]">
        <p>Checking access…</p>
      </div>
    )
  }

  const capListLower = capList.map(c => c.toLowerCase())
  const hasTenantCap = capListLower.some(c => tenantCaps.includes(c))
  const userHasAny = capListLower.some(c => userCaps.includes(c))
  let allowed = false
  if(role === 'tenant_admin') {
    allowed = hasTenantCap
  } else {
    allowed = hasTenantCap && (capListLower.length === 0 || userHasAny)
  }

  if(allowed) return <>{children}</>

  // Tailored messages for clearer guidance
  const message = !hasTenantCap
    ? `This feature is not enabled for this tenant. Please ask the Super Admin to enable capability: ${capId}.`
    : (role === 'staff'
        ? `Your account doesn't have access to this feature. Ask your Tenant Admin to grant capability: ${capId}.`
        : `Access denied for role '${role}'.`)

  return (
    <div className="mb-4">
      <Alert variant="warning">{message}</Alert>
    </div>
  )
}
