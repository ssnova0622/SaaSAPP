/**
 * useCapabilities — granular RBAC flags for the current user.
 *
 * Reads identity/caps from AuthContext (JWT parsed once there).
 * Provides named boolean flags consumed by pages and components.
 *
 * For new code, prefer the lighter `usePermissions(module)` hook or
 * the `<Can>` component — they derive from the same AuthContext.
 */
import { useAuth } from '../contexts/AuthContext'

export function useCapabilities() {
  const { hasCap, hasAnyCap, isSuperAdmin, isTenantAdmin, isStaff, hasFullAccess, caps: capsSet } = useAuth()

  const role = isSuperAdmin ? 'super_admin' : isTenantAdmin ? 'tenant_admin' : isStaff ? 'staff' : 'admin'
  const userCaps = Array.from(capsSet)

  const has = (cap: string) => hasCap(cap)
  const hasAny = (capList: string[]) => hasAnyCap(capList)

  /** Generic permission check — prefer `usePermissions()` for new code. */
  const can = (_scope: string, _action: 'read' | 'create' | 'update' | 'delete') => {
    if (hasFullAccess) return true
    const s = _scope.toLowerCase()
    return hasAny([s, `${s}.view`, `${s}.edit`, `${s}.create`, `${s}.delete`])
  }

  // ---- Salon Services ----
  const canViewServices = hasAny(['salon.services', 'salon.services.view', 'salon.services.edit'])
  const canEditServices = hasAny(['salon.services', 'salon.services.edit'])

  // ---- Professionals ----
  const canViewProfessionals = hasAny(['salon.professionals', 'salon.professionals.view', 'salon.professionals.edit', 'salon.professionals.edit_sensitive', 'salon.professionals.manage', 'salon.professionals.create'])
  const canEditProfessionals = hasAny(['salon.professionals', 'salon.professionals.edit'])
  const canEditSensitiveProfessionals = hasAny(['salon.professionals.edit_sensitive', 'salon.professionals.manage', 'salon.professionals'])
  const canCreateProfessional = hasAny(['salon.professionals', 'salon.professionals.create'])
  const canDeleteProfessional = hasAny(['salon.professionals', 'salon.professionals.delete'])
  const canManageProfessionalDetails = canEditSensitiveProfessionals

  // ---- Appointments ----
  const canViewAppointments = hasAny(['salon.appointments', 'salon.appointments.view', 'salon.appointments.edit'])
  const canEditAppointments = hasAny(['salon.appointments', 'salon.appointments.edit'])
  const canDeleteAppointments = hasAny(['salon.appointments', 'salon.appointments.delete', 'salon.appointments.edit'])

  // ---- No-Show Blocked ----
  const canAccessNoShowBlocked = hasAny(['salon.no_show_blocked', 'salon.no_show_blocked.view', 'salon.no_show_blocked.edit'])
  const canEditNoShowBlocked = hasAny(['salon.no_show_blocked', 'salon.no_show_blocked.edit'])

  // ---- Dashboard ----
  const canAccessDashboard = hasAny(['core.dashboard', 'core.dashboard.view'])

  // ---- Store Orders ----
  const canViewOrders = hasAny(['store.orders', 'store.orders.view', 'store.orders.edit'])
  const canEditOrders = hasAny(['store.orders', 'store.orders.edit'])
  const canEditSensitiveOrders = hasAny(['store.orders', 'store.orders.edit_sensitive'])
  const canDeleteOrders = hasAny(['store.orders', 'store.orders.delete', 'store.orders.edit'])

  // ---- Core: Customers ----
  const canViewCustomers = hasAny(['core.customers', 'core.customers.view', 'core.customers.edit'])
  const canEditCustomers = hasAny(['core.customers', 'core.customers.edit'])
  const canEditSensitiveCustomers = hasAny(['core.customers', 'core.customers.edit_sensitive'])

  // ---- Core: Reports ----
  const canViewReports = hasAny(['core.reports', 'core.reports.view'])

  // ---- Core: Settings ----
  const canViewSettings = hasAny(['core.settings', 'core.settings.view', 'core.settings.edit'])
  const canEditSettings = hasAny(['core.settings', 'core.settings.edit'])
  const canEditSensitiveSettings = hasAny(['core.settings', 'core.settings.edit_sensitive'])

  // ---- Core: Users (staff management) ----
  const canViewUsers = hasAny(['core.users', 'core.users.view', 'core.users.edit'])
  const canEditUsers = hasAny(['core.users', 'core.users.edit'])
  const canEditSensitiveUsers = hasAny(['core.users', 'core.users.edit_sensitive'])

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
