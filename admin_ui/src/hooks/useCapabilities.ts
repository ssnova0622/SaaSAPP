import { useMemo } from 'react'
import { tokenStore } from '../api/axios'

/**
 * RBAC: View / Edit / Edit Sensitive / Delete per entity.
 * Tenant Admin & Super Admin = full access (all true). Staff = by assigned caps. Viewer = view only.
 */
export function useCapabilities() {
  const { role, userCaps } = useMemo(() => {
    try {
      const tok = tokenStore.get()
      if (!tok) return { role: 'admin' as string, userCaps: [] as string[] }
      const p = JSON.parse(atob(tok.split('.')[1]))
      const role = String(p?.role || 'admin').toLowerCase()
      const userCaps = Array.isArray(p?.caps) ? p.caps.map((c: string) => String(c).toLowerCase()) : []
      return { role, userCaps }
    } catch {
      return { role: 'admin', userCaps: [] }
    }
  }, [])

  const isTenantAdmin = role === 'tenant_admin'
  const isSuperAdmin = role === 'super_admin'
  const isStaff = role === 'staff'
  const hasFullAccess = isTenantAdmin || isSuperAdmin

  const has = (cap: string) => userCaps.includes(String(cap).toLowerCase())
  const hasAny = (caps: string[]) => caps.some(c => has(c))

  /** Generic permission check: scope (e.g. salon.appointments), action (read|create|update|delete). Uses caps; full access for tenant_admin/super_admin. */
  const can = (scope: string, action: 'read' | 'create' | 'update' | 'delete') => {
    if (hasFullAccess) return true
    const s = String(scope).toLowerCase()
    const aliases = [s, `${s}.view`, `${s}.edit`, `${s}.create`, `${s}.delete`, s.replace(/\.[^.]+$/, '')]
    return hasAny(aliases.filter(Boolean))
  }

  // Legacy "full access" caps: staff with these get tenant-admin-like access for that module (view + edit + edit_sensitive).
  const hasLegacy = (legacyId: string) => has(legacyId)

  // ---- Salon Services (service definitions) ----
  const canViewServices = hasFullAccess || hasAny(['salon.services', 'salon.services.view', 'salon.services.edit'])
  const canEditServices = hasFullAccess || hasLegacy('salon.services') || hasAny(['salon.services.edit'])

  // ---- Professionals ----
  const canViewProfessionals = hasFullAccess || hasAny(['salon.professionals', 'salon.professionals.view', 'salon.professionals.edit', 'salon.professionals.edit_sensitive', 'salon.professionals.manage', 'salon.professionals.create'])
  const canEditProfessionals = hasFullAccess || hasLegacy('salon.professionals') || hasAny(['salon.professionals.edit'])
  const canEditSensitiveProfessionals = hasFullAccess || hasLegacy('salon.professionals') || hasAny(['salon.professionals.edit_sensitive', 'salon.professionals.manage'])
  const canCreateProfessional = hasFullAccess || hasLegacy('salon.professionals') || has('salon.professionals.create')
  const canDeleteProfessional = hasFullAccess || hasLegacy('salon.professionals') || has('salon.professionals.delete')
  const canManageProfessionalDetails = canEditSensitiveProfessionals

  // ---- Appointments ----
  const canViewAppointments = hasFullAccess || hasAny(['salon.appointments', 'salon.appointments.view', 'salon.appointments.edit'])
  const canEditAppointments = hasFullAccess || hasLegacy('salon.appointments') || hasAny(['salon.appointments.edit'])
  const canDeleteAppointments = hasFullAccess || hasLegacy('salon.appointments') || hasAny(['salon.appointments.delete', 'salon.appointments.edit'])

  // ---- No-Show Blocked ----
  const canAccessNoShowBlocked = hasFullAccess || hasAny(['salon.no_show_blocked', 'salon.no_show_blocked.view', 'salon.no_show_blocked.edit'])
  const canEditNoShowBlocked = hasFullAccess || hasLegacy('salon.no_show_blocked') || has('salon.no_show_blocked.edit')

  // ---- Dashboard ----
  const canAccessDashboard = hasFullAccess || hasAny(['core.dashboard', 'core.dashboard.view'])

  // ---- Store Orders ----
  const canViewOrders = hasFullAccess || hasAny(['store.orders', 'store.orders.view', 'store.orders.edit'])
  const canEditOrders = hasFullAccess || hasLegacy('store.orders') || hasAny(['store.orders', 'store.orders.edit'])
  const canEditSensitiveOrders = hasFullAccess || hasLegacy('store.orders') || has('store.orders.edit_sensitive')
  const canDeleteOrders = hasFullAccess || hasLegacy('store.orders') || hasAny(['store.orders.delete', 'store.orders.edit'])

  // ---- Core: Customers ----
  const canViewCustomers = hasFullAccess || hasAny(['core.customers', 'core.customers.view', 'core.customers.edit'])
  const canEditCustomers = hasFullAccess || hasLegacy('core.customers') || hasAny(['core.customers', 'core.customers.edit'])
  const canEditSensitiveCustomers = hasFullAccess || hasLegacy('core.customers') || has('core.customers.edit_sensitive')

  // ---- Core: Reports ----
  const canViewReports = hasFullAccess || hasAny(['core.reports', 'core.reports.view'])

  // ---- Core: Settings ----
  const canViewSettings = hasFullAccess || hasAny(['core.settings', 'core.settings.view', 'core.settings.edit'])
  const canEditSettings = hasFullAccess || hasLegacy('core.settings') || hasAny(['core.settings', 'core.settings.edit'])
  const canEditSensitiveSettings = hasFullAccess || hasLegacy('core.settings') || has('core.settings.edit_sensitive')

  // ---- Core: Users (staff management) ----
  const canViewUsers = hasFullAccess || hasAny(['core.users', 'core.users.view', 'core.users.edit'])
  const canEditUsers = hasFullAccess || hasLegacy('core.users') || hasAny(['core.users', 'core.users.edit'])
  const canEditSensitiveUsers = hasFullAccess || hasLegacy('core.users') || has('core.users.edit_sensitive')

  return {
    role,
    userCaps,
    isTenantAdmin,
    isSuperAdmin,
    isStaff,
    hasFullAccess,
    has,
    hasAny,
    can,
    canViewServices,
    canEditServices,
    canViewProfessionals,
    canEditProfessionals,
    canEditSensitiveProfessionals,
    canManageProfessionalDetails,
    canCreateProfessional,
    canDeleteProfessional,
    canViewAppointments,
    canEditAppointments,
    canDeleteAppointments,
    canAccessNoShowBlocked,
    canEditNoShowBlocked,
    canAccessDashboard,
    canViewOrders,
    canEditOrders,
    canEditSensitiveOrders,
    canDeleteOrders,
    canViewCustomers,
    canEditCustomers,
    canEditSensitiveCustomers,
    canViewReports,
    canViewSettings,
    canEditSettings,
    canEditSensitiveSettings,
    canViewUsers,
    canEditUsers,
    canEditSensitiveUsers,
  }
}
