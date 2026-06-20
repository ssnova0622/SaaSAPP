/**
 * usePermissions(module) — clean per-module permission flags.
 *
 * Usage:
 *   const { canView, canEdit, canDelete, canEditSensitive } = usePermissions('salon.appointments')
 *   const { canEdit: canEditSettings } = usePermissions('core.settings')
 *
 * This is the preferred hook for new code. Legacy code can continue using
 * useCapabilities() which exposes named flags like `canViewAppointments`.
 */
import { useAuth } from '../contexts/AuthContext'

export interface ModulePermissions {
  canView: boolean
  canEdit: boolean
  canDelete: boolean
  canEditSensitive: boolean
}

export function usePermissions(moduleCap: string): ModulePermissions {
  const { hasAnyCap } = useAuth()
  const base = moduleCap.toLowerCase().replace(/\.$/, '')

  return {
    canView: hasAnyCap([base, `${base}.view`, `${base}.edit`]),
    canEdit: hasAnyCap([base, `${base}.edit`]),
    canDelete: hasAnyCap([base, `${base}.delete`, `${base}.edit`]),
    canEditSensitive: hasAnyCap([base, `${base}.edit_sensitive`]),
  }
}
