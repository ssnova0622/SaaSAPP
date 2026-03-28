import { useEffect, useState } from 'react'
import { useEffectiveTenant } from '../hooks/useEffectiveTenant'
import { listTenants } from '../api/tenants'

/** Read-only badge showing the effective tenant for non-super users. */
export function TenantBadge() {
  const { effectiveTenant, isSuper } = useEffectiveTenant()
  if (isSuper) return null
  if (!effectiveTenant) return null
  return (
    <div className="rounded-lg border border-[#334155] bg-[#334155]/50 px-3 py-2 text-sm text-[#e2e8f0]">
      Tenant: <strong>{effectiveTenant}</strong>
    </div>
  )
}

/** Tenant selector for Super Admin. Persists selection via useEffectiveTenant. */
export function TenantSelector(props: { label?: string; size?: 'small' | 'medium' }) {
  const { effectiveTenant, setEffectiveTenant, isSuper } = useEffectiveTenant()
  const [items, setItems] = useState<string[]>([])
  useEffect(() => {
    ;(async () => {
      try {
        const list = await listTenants()
        setItems(list.map((t) => t.tenant))
      } catch {
        setItems([])
      }
    })()
  }, [])
  if (!isSuper) return null
  return (
    <div className="min-w-[200px]">
      <label className="block text-xs font-medium text-[#94a3b8] mb-1">{props.label ?? 'Tenant'}</label>
      <select
        value={effectiveTenant}
        onChange={(e) => setEffectiveTenant(e.target.value)}
        className={`w-full rounded-lg border border-[#334155] bg-[#0f172a] text-[#f1f5f9] px-3 focus:ring-2 focus:ring-[#3b82f6] focus:border-[#3b82f6] outline-none ${props.size === 'small' ? 'py-1.5 text-sm' : 'py-2'}`}
      >
        <option value="">Select tenant</option>
        {items.map((t) => (
          <option key={t} value={t}>{t}</option>
        ))}
      </select>
    </div>
  )
}
