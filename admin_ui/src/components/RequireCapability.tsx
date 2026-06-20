/**
 * RequireCapability — route-level tenant feature gate.
 *
 * Guards entire pages based on:
 *   1. Tenant having the capability enabled (license / feature flag)
 *   2. Staff users also having the capability in their user.caps
 *
 * Super Admins bypass all checks.
 * Tenant Admins are allowed when the tenant has the cap.
 * Staff are allowed when both tenant AND user have the cap.
 *
 * Reads identity from AuthContext (JWT parsed once there — no duplication).
 */
import { ReactNode, useEffect, useState } from 'react'
import { getTenantSettings, TenantSettings } from '@api/tenants'
import { Alert } from '@components/ui/Alert'
import { useAuth } from '../contexts/AuthContext'
import { useEffectiveTenant } from '../hooks/useEffectiveTenant'

const VIEW_CAP_ALIASES: Record<string, string[]> = {
  'core.dashboard':        ['core.dashboard', 'core.dashboard.view'],
  'salon.services':        ['salon.services', 'salon.services.view', 'salon.services.edit'],
  'salon.professionals':   ['salon.professionals', 'salon.professionals.view'],
  'salon.appointments':    ['salon.appointments', 'salon.appointments.view'],
  'salon.no_show_blocked': ['salon.no_show_blocked', 'salon.no_show_blocked.view'],
  'store.orders':          ['store.orders', 'store.orders.view'],
  'core.reports':          ['core.reports', 'core.reports.view'],
  'core.customers':        ['core.customers', 'core.customers.view'],
  'core.settings':         ['core.settings', 'core.settings.view'],
  'core.users':            ['core.users', 'core.users.view'],
}

export default function RequireCapability({
  cap,
  caps: capsProp,
  children,
}: {
  cap?: string
  caps?: string[]
  children: ReactNode
}) {
  const { effectiveTenant: selectedTenant } = useEffectiveTenant()
  const { isSuperAdmin, isTenantAdmin, hasCap, user } = useAuth()
  const tokenTenant = user?.tenant ?? null

  const [tenantCaps, setTenantCaps] = useState<string[] | null>(null)

  const capList = capsProp ?? (cap ? (VIEW_CAP_ALIASES[cap] ?? [cap]) : [])
  const capId = (cap || capList[0] || '').toLowerCase()

  useEffect(() => {
    ;(async () => {
      const targetTenant = isSuperAdmin ? selectedTenant : tokenTenant || selectedTenant || ''
      if (!isSuperAdmin && !tokenTenant) { setTenantCaps([]); return }
      if (!targetTenant) { setTenantCaps([]); return }
      try {
        const s: TenantSettings = await getTenantSettings(targetTenant)
        setTenantCaps((s.capabilities || []).map((c) => String(c).toLowerCase()))
      } catch {
        if (!isSuperAdmin && tokenTenant && targetTenant !== tokenTenant) {
          try {
            const s: TenantSettings = await getTenantSettings(tokenTenant)
            setTenantCaps((s.capabilities || []).map((c) => String(c).toLowerCase()))
            return
          } catch { /* ignore */ }
        }
        setTenantCaps([])
      }
    })()
  }, [isSuperAdmin, tokenTenant, selectedTenant])

  // Super Admin always allowed
  if (isSuperAdmin) return <>{children}</>

  // Waiting for tenant caps to load
  if (tenantCaps === null) {
    return (
      <div className="min-h-[200px] flex items-center justify-center text-[#94a3b8]">
        <p>Checking access…</p>
      </div>
    )
  }

  const capListLower = capList.map((c) => c.toLowerCase())
  const hasTenantCap = capListLower.some((c) => tenantCaps.includes(c))
  const userHasAny = capListLower.some((c) => hasCap(c))

  let allowed = false
  if (isTenantAdmin) {
    allowed = hasTenantCap
  } else {
    // Staff: need both tenant cap and user cap
    allowed = hasTenantCap && (capListLower.length === 0 || userHasAny)
  }

  if (allowed) return <>{children}</>

  const message = !hasTenantCap
    ? `This feature is not enabled for this tenant. Ask the Super Admin to enable: ${capId}.`
    : `Your account doesn't have access to this feature. Ask your Tenant Admin to grant: ${capId}.`

  return (
    <div className="mb-4">
      <Alert variant="warning">{message}</Alert>
    </div>
  )
}
