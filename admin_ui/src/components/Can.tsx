/**
 * <Can> — declarative permission gate.
 *
 * Renders `children` when the user has the required permission.
 * Renders `fallback` (default: nothing) when they don't.
 *
 * Usage:
 *   // Hide edit button from viewers
 *   <Can do="edit" on="salon.appointments">
 *     <Button onClick={save}>Save</Button>
 *   </Can>
 *
 *   // Show disabled placeholder instead
 *   <Can do="delete" on="core.staff" fallback={<DisabledButton />}>
 *     <DeleteButton />
 *   </Can>
 *
 *   // Sensitive data — hide revenue from staff without edit_sensitive
 *   <Can do="edit_sensitive" on="core.reports">
 *     <RevenueCard />
 *   </Can>
 *
 * action values:  "view" | "edit" | "delete" | "edit_sensitive"
 *
 * Note: tenant feature gating (whether a module is enabled at all) is handled
 * by <RequireCapability> at the route level. <Can> only checks user permission
 * within an already-accessible page.
 */
import { ReactNode } from 'react'
import { usePermissions } from '../hooks/usePermissions'

type Action = 'view' | 'edit' | 'delete' | 'edit_sensitive'

interface CanProps {
  /** The action being checked. */
  do: Action
  /** The module/capability scope, e.g. "salon.appointments" or "core.staff". */
  on: string
  /** Rendered instead of children when access is denied. Defaults to null. */
  fallback?: ReactNode
  children: ReactNode
}

export default function Can({ do: action, on: module, fallback = null, children }: CanProps) {
  const perms = usePermissions(module)

  const allowed =
    action === 'view'           ? perms.canView :
    action === 'edit'           ? perms.canEdit :
    action === 'delete'         ? perms.canDelete :
    action === 'edit_sensitive' ? perms.canEditSensitive :
    false

  return <>{allowed ? children : fallback}</>
}
