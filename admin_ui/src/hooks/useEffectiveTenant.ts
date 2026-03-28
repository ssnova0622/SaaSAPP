import { useEffect, useMemo, useState } from 'react'
import { listTenants, clearTenantSettingsCache, getWhatsAppTemplateBundle } from '../api/tenants'
import { tokenStore } from '../api/axios'

type AuthInfo = { role: string; tenant: string }

function parseAuth(): AuthInfo {
  try{
    const tok = tokenStore.get()
    if(!tok) return { role:'', tenant:'' }
    const p = JSON.parse(atob(tok.split('.')[1] || ''))
    const role = String(p?.role || '').toLowerCase()
    const tenant = String(p?.tenant || '')
    return { role, tenant }
  }catch{ return { role:'', tenant:'' } }
}

/**
 * Returns the effective tenant for the current user.
 * - For tenant_admin/staff: the JWT tenant is returned, ready immediately.
 * - For super_admin: returns the last selected tenant from localStorage if available, otherwise
 *   loads the tenant list and picks the first one. It also exposes setEffectiveTenant to switch.
 */
export function useEffectiveTenant(){
  const { role, tenant: jwtTenant } = parseAuth()
  const isSuper = role === 'super_admin'
  const [effectiveTenant, setEffectiveTenant] = useState<string>(() => {
    try {
      const { role: r, tenant: jt } = parseAuth()
      if (r !== 'super_admin') return jt || ''
      return localStorage.getItem('selected_tenant') || ''
    } catch {
      return ''
    }
  })
  const [ready, setReady] = useState<boolean>(false)

  useEffect(()=>{
    let mounted = true
    async function init(){
      if(!isSuper){
        if(mounted){ setEffectiveTenant(jwtTenant || ''); setReady(true) }
        return
      }
      // super_admin: only use stored selection; do not auto-pick. User must choose from modal or sidebar.
      try{
        const stored = localStorage.getItem('selected_tenant') || ''
        if(mounted){ setEffectiveTenant(stored); setReady(true) }
      }catch{ if(mounted){ setEffectiveTenant(''); setReady(true) } }
    }
    init()
    return ()=>{ mounted = false }
  },[isSuper, jwtTenant])

  // Keep all hook instances in sync when any component calls setEffectiveTenant (modal or sidebar dropdown).
  useEffect(()=>{
    const handler = (e: Event) => {
      const next = (e as CustomEvent<string>)?.detail
      if (typeof next === 'string') setEffectiveTenant(next)
    }
    window.addEventListener('tenant-change', handler)
    return () => window.removeEventListener('tenant-change', handler)
  }, [])

  const api = useMemo(()=>({
    effectiveTenant,
    setEffectiveTenant: (t: string)=>{
      setEffectiveTenant(t)
      try { if (isSuper) localStorage.setItem('selected_tenant', t) } catch { /* ignore */ }
      // Clear tenant settings cache so sidebar and all pages refetch for the new tenant (full refresh)
      try { clearTenantSettingsCache() } catch { /* ignore */ }
      try { window.dispatchEvent(new CustomEvent<string>('tenant-change', { detail: t })) } catch { /* ignore */ }
      if (t) {
        void getWhatsAppTemplateBundle(t)
          .then((bundle) => {
            try {
              sessionStorage.setItem(`wa_msg_bundle:${t}`, JSON.stringify(bundle))
            } catch {
              /* ignore */
            }
          })
          .catch(() => {
            /* ignore */
          })
      }
    },
    ready,
    isSuper,
    role,
  }),[effectiveTenant, ready, isSuper, role])

  return api
}
