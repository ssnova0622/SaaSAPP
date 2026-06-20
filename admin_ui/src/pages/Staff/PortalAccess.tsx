/**
 * Staff Portal Access
 *
 * Visual, card-based portal permission manager. Shows every staff member and
 * which portal modules/pages they can access after logging in.
 *
 * Design: same feature × action matrix style as Modules & Capabilities in Settings.
 * Profile quick-assign (Viewer / Editor / Manager / Custom) + granular checkbox matrix.
 */
import {
  Alert, Box, Button, Card, CardContent, Checkbox, Chip,
  CircularProgress, Collapse, Divider, FormControlLabel, Grid,
  IconButton, Stack, Switch, Tooltip, Typography,
} from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import PersonAddIcon from '@mui/icons-material/PersonAdd'
import BlockIcon from '@mui/icons-material/Block'
import LockOpenIcon from '@mui/icons-material/LockOpen'
import { useEffect, useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { listStaff, type Staff } from '@api/staff'
import {
  listUsers, createUser, updateUser, getPermissionProfiles, setPassword,
  type User, type PermissionProfile,
} from '@api/users'
import { getTenantSettings } from '@api/tenants'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useAuth } from '../../contexts/AuthContext'
import { useAlert } from '@contexts/AlertContext'

// ─── Feature matrix definition (same as ModulesCapabilities) ────────────────
interface FeatureAction { label: string; cap: string }
interface Feature { label: string; description: string; actions: FeatureAction[] }
interface ModuleDef { id: string; label: string; emoji: string; color: string; features: Feature[] }

const MODULE_DEFS: ModuleDef[] = [
  {
    id: 'core', label: 'Core', emoji: '⚙️', color: '#2563eb',
    features: [
      { label: 'Dashboard', description: 'Analytics overview', actions: [{ label: 'View', cap: 'core.dashboard.view' }] },
      { label: 'Customers', description: 'Customer profiles', actions: [
        { label: 'View', cap: 'core.customers.view' },
        { label: 'Edit', cap: 'core.customers.edit' },
        { label: 'PII', cap: 'core.customers.edit_sensitive' },
      ]},
      { label: 'Staff', description: 'Staff records', actions: [{ label: 'Manage', cap: 'core.staff' }] },
      { label: 'Users', description: 'Portal logins', actions: [
        { label: 'View', cap: 'core.users.view' },
        { label: 'Edit', cap: 'core.users.edit' },
      ]},
      { label: 'Reports', description: 'Reports & analytics', actions: [{ label: 'View', cap: 'core.reports.view' }] },
      { label: 'Settings', description: 'Tenant config', actions: [
        { label: 'View', cap: 'core.settings.view' },
        { label: 'Edit', cap: 'core.settings.edit' },
      ]},
      { label: 'Promotions', description: 'Campaigns', actions: [{ label: 'Access', cap: 'core.promotions' }] },
      { label: 'Follow-ups', description: 'Auto follow-ups', actions: [{ label: 'Access', cap: 'core.followups' }] },
      { label: 'WhatsApp Bot', description: 'Bot builder', actions: [{ label: 'Manage', cap: 'core.whatsapp_menu' }] },
    ],
  },
  {
    id: 'salon', label: 'Salon / Clinic', emoji: '💇', color: '#0d9488',
    features: [
      { label: 'Services', description: 'Service catalog', actions: [
        { label: 'View', cap: 'salon.services.view' },
        { label: 'Edit', cap: 'salon.services.edit' },
      ]},
      { label: 'Professionals', description: 'Stylists / doctors', actions: [
        { label: 'View', cap: 'salon.professionals.view' },
        { label: 'Edit', cap: 'salon.professionals.edit' },
        { label: 'Sensitive', cap: 'salon.professionals.edit_sensitive' },
      ]},
      { label: 'Appointments', description: 'Booking management', actions: [
        { label: 'View', cap: 'salon.appointments.view' },
        { label: 'Edit', cap: 'salon.appointments.edit' },
        { label: 'Delete', cap: 'salon.appointments.delete' },
      ]},
      { label: 'No-Show Blocked', description: 'Blocked customers', actions: [
        { label: 'View', cap: 'salon.no_show_blocked.view' },
        { label: 'Edit', cap: 'salon.no_show_blocked.edit' },
      ]},
    ],
  },
  {
    id: 'store', label: 'Store', emoji: '🛒', color: '#d97706',
    features: [
      { label: 'Orders', description: 'Customer orders', actions: [
        { label: 'View', cap: 'store.orders.view' },
        { label: 'Edit', cap: 'store.orders.edit' },
        { label: 'Sensitive', cap: 'store.orders.edit_sensitive' },
      ]},
      { label: 'Catalog', description: 'Products', actions: [{ label: 'Manage', cap: 'store.catalog' }] },
      { label: 'Inventory', description: 'Stock', actions: [{ label: 'Manage', cap: 'store.inventory' }] },
    ],
  },
]

// All caps referenced in MODULE_DEFS
const ALL_FEATURE_CAPS = new Set(MODULE_DEFS.flatMap((m) => m.features.flatMap((f) => f.actions.map((a) => a.cap))))

// Profile colours & labels
const PROFILE_META: Record<string, { label: string; color: 'info' | 'primary' | 'success' | 'warning' | 'default' }> = {
  viewer:  { label: 'Viewer',  color: 'info' },
  editor:  { label: 'Editor',  color: 'primary' },
  manager: { label: 'Manager', color: 'success' },
  custom:  { label: 'Custom',  color: 'warning' },
  none:    { label: 'No caps', color: 'default' },
}

function detectProfileName(userCaps: string[], profiles: PermissionProfile[], tenantCaps: Set<string>): string {
  const effectiveCaps = new Set(userCaps.map((c) => c.toLowerCase()).filter((c) => tenantCaps.has(c)))
  for (const p of profiles) {
    if (p.id === 'custom') continue
    const pCaps = new Set((p.caps || []).map((c) => c.toLowerCase()).filter((c) => tenantCaps.has(c)))
    if (pCaps.size === effectiveCaps.size && [...pCaps].every((c) => effectiveCaps.has(c))) return p.id
  }
  return effectiveCaps.size === 0 ? 'none' : 'custom'
}

function capsForProfile(profileId: string, profiles: PermissionProfile[], tenantCaps: Set<string>): string[] {
  const p = profiles.find((x) => x.id === profileId)
  if (!p) return []
  return (p.caps || []).map((c) => c.toLowerCase()).filter((c) => tenantCaps.has(c))
}

// ─── Single staff portal access card ─────────────────────────────────────────

interface StaffCardProps {
  staff: Staff
  portalUser: User | null
  tenantCaps: Set<string>
  profiles: PermissionProfile[]
  onSave: (userId: string | null, email: string, caps: string[], isNew: boolean) => Promise<void>
  onRevoke: (userId: string) => Promise<void>
}

function StaffPortalCard({ staff, portalUser, tenantCaps, profiles, onSave, onRevoke }: StaffCardProps) {
  const [expanded, setExpanded] = useState(false)
  const [caps, setCaps] = useState<string[]>((portalUser?.caps ?? []).map((c) => String(c).toLowerCase()))
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)

  // Reset when portalUser changes (after save)
  useEffect(() => {
    setCaps((portalUser?.caps ?? []).map((c) => String(c).toLowerCase()))
    setDirty(false)
  }, [portalUser])

  const capsSet = new Set(caps)
  const profileName = portalUser ? detectProfileName(caps, profiles, tenantCaps) : 'none'
  const profileMeta = PROFILE_META[profileName] ?? PROFILE_META.custom
  const hasAccess = !!portalUser && portalUser.status !== 'disabled'
  const isDisabled = portalUser?.status === 'disabled'

  function toggleCap(cap: string, on: boolean) {
    setCaps((prev) => {
      const s = new Set(prev)
      if (on) s.add(cap); else s.delete(cap)
      return Array.from(s)
    })
    setDirty(true)
  }

  function applyProfile(profileId: string) {
    const newCaps = capsForProfile(profileId, profiles, tenantCaps)
    setCaps(newCaps)
    setDirty(true)
  }

  async function handleSave() {
    setSaving(true)
    try {
      await onSave(portalUser?.id ?? null, staff.email || '', caps, !portalUser)
      setDirty(false)
      setExpanded(false)
    } finally {
      setSaving(false)
    }
  }

  // Which modules are "touched" (any cap enabled)
  const activeMods = MODULE_DEFS.filter((m) => m.features.some((f) => f.actions.some((a) => capsSet.has(a.cap))))

  return (
    <Card variant="outlined" sx={{ mb: 2, borderLeft: `4px solid ${hasAccess ? '#2563eb' : '#e2e8f0'}` }}>
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        {/* Header row */}
        <Stack direction="row" alignItems="center" spacing={1.5}>
          {/* Avatar letter */}
          <Box sx={{ width: 36, height: 36, borderRadius: '50%', bgcolor: hasAccess ? '#eff6ff' : '#f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid #e2e8f0' }}>
            <Typography fontWeight={700} color={hasAccess ? 'primary.main' : 'text.secondary'} fontSize={15}>
              {(staff.name || '?')[0].toUpperCase()}
            </Typography>
          </Box>

          <Box flex={1}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <Typography variant="subtitle2" fontWeight={700}>{staff.name}</Typography>
              {staff.role && <Chip label={staff.role} size="small" variant="outlined" sx={{ fontSize: 10 }} />}
              {hasAccess && <Chip label={profileMeta.label} color={profileMeta.color} size="small" />}
              {isDisabled && <Chip label="Access revoked" color="error" size="small" variant="outlined" />}
              {!portalUser && <Chip label="No portal access" size="small" variant="outlined" color="default" />}
            </Stack>
            <Typography variant="caption" color="text.secondary">{staff.email || 'No email'}</Typography>
          </Box>

          {/* Quick module pills (collapsed view) */}
          {hasAccess && !expanded && activeMods.length > 0 && (
            <Stack direction="row" spacing={0.5} flexWrap="wrap">
              {activeMods.map((m) => (
                <Chip key={m.id} label={m.emoji + ' ' + m.label} size="small" sx={{ fontSize: 11, bgcolor: '#f0fdf4' }} />
              ))}
            </Stack>
          )}

          {/* Actions */}
          <Stack direction="row" spacing={0.5}>
            {!staff.email?.trim() && (
              <Tooltip title="Add an email to this staff record first">
                <span>
                  <Button size="small" disabled startIcon={<PersonAddIcon />}>Grant access</Button>
                </span>
              </Tooltip>
            )}
            {staff.email?.trim() && !portalUser && (
              <Button size="small" variant="outlined" startIcon={<PersonAddIcon />} onClick={() => setExpanded(true)}>
                Grant access
              </Button>
            )}
            {portalUser && (
              <>
                {isDisabled ? (
                  <Button size="small" variant="outlined" color="success" startIcon={<LockOpenIcon />} onClick={() => onRevoke(portalUser.id!)}>
                    Restore access
                  </Button>
                ) : (
                  <Tooltip title="Revoke portal access">
                    <IconButton size="small" color="error" onClick={() => onRevoke(portalUser.id!)}>
                      <BlockIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                )}
                <IconButton size="small" onClick={() => setExpanded((v) => !v)}>
                  {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              </>
            )}
          </Stack>
        </Stack>

        {/* Expanded editor */}
        <Collapse in={expanded} unmountOnExit>
          <Divider sx={{ my: 2 }} />

          {/* Profile quick-assign buttons */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>Quick assign profile</Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              {(['manager', 'editor', 'viewer'] as const).map((pid) => (
                <Button
                  key={pid}
                  size="small"
                  variant={profileName === pid ? 'contained' : 'outlined'}
                  color={PROFILE_META[pid].color as any}
                  onClick={() => applyProfile(pid)}
                >
                  {PROFILE_META[pid].label}
                </Button>
              ))}
              <Button size="small" variant="outlined" color="warning" onClick={() => { setCaps([]); setDirty(true) }}>
                Clear All
              </Button>
            </Stack>
          </Box>

          <Divider sx={{ my: 1.5 }} />

          {/* Feature matrix */}
          <Typography variant="body2" fontWeight={600} sx={{ mb: 1 }}>
            Or choose specific page access
          </Typography>
          <Grid container spacing={2}>
            {MODULE_DEFS.map((mod) => {
              // Only show modules that are in the tenant caps
              const hasAnyModCap = mod.features.some((f) => f.actions.some((a) => tenantCaps.has(a.cap)))
              if (!hasAnyModCap) return null
              return (
                <Grid item xs={12} md={6} key={mod.id}>
                  <Card variant="outlined" sx={{ borderLeft: `3px solid ${mod.color}`, bgcolor: `${mod.color}08` }}>
                    <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                      <Typography variant="subtitle2" fontWeight={700} sx={{ color: mod.color, mb: 1 }}>
                        {mod.emoji} {mod.label}
                      </Typography>
                      {mod.features.map((feature) => {
                        const visibleActions = feature.actions.filter((a) => tenantCaps.has(a.cap))
                        if (visibleActions.length === 0) return null
                        return (
                          <Stack key={feature.label} direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
                            <Typography variant="caption" color="text.secondary" sx={{ minWidth: 100 }}>
                              {feature.label}
                            </Typography>
                            <Stack direction="row" flexWrap="wrap">
                              {visibleActions.map((action) => (
                                <FormControlLabel
                                  key={action.cap}
                                  control={
                                    <Checkbox
                                      size="small"
                                      checked={capsSet.has(action.cap)}
                                      onChange={(e) => toggleCap(action.cap, e.target.checked)}
                                    />
                                  }
                                  label={<Typography variant="caption">{action.label}</Typography>}
                                  sx={{ mr: 0, ml: 0 }}
                                />
                              ))}
                            </Stack>
                          </Stack>
                        )
                      })}
                    </CardContent>
                  </Card>
                </Grid>
              )
            })}
          </Grid>

          <Divider sx={{ my: 2 }} />
          <Stack direction="row" spacing={1}>
            <Button variant="contained" onClick={handleSave} disabled={saving} startIcon={saving ? <CircularProgress size={14} /> : <CheckCircleIcon />}>
              {saving ? 'Saving…' : (portalUser ? 'Save access' : 'Grant portal access')}
            </Button>
            <Button variant="outlined" onClick={() => { setExpanded(false); setCaps((portalUser?.caps ?? []).map((c) => String(c).toLowerCase())); setDirty(false) }}>
              Cancel
            </Button>
            {dirty && <Typography variant="caption" color="warning.main" sx={{ alignSelf: 'center' }}>Unsaved changes</Typography>}
          </Stack>
        </Collapse>
      </CardContent>
    </Card>
  )
}

// ─── Main page ───────────────────────────────────────────────────────────────

export default function StaffPortalAccess() {
  const { effectiveTenant: tenant, role } = useEffectiveTenant()
  const { isSuperAdmin, isTenantAdmin } = useAuth()
  const { showAlert, showConfirm } = useAlert()
  const qc = useQueryClient()

  const canManage = isSuperAdmin || isTenantAdmin || role === 'tenant_admin'

  const { data: staffData, isLoading: staffLoading } = useQuery({
    queryKey: ['staff', tenant, { size: 200 }],
    queryFn: async () => {
      if (!tenant) return { items: [] as Staff[] }
      return await listStaff(tenant, { page: 1, size: 200 })
    },
    enabled: !!tenant,
  })

  const { data: portalUsersData } = useQuery({
    queryKey: ['users', tenant, 'staff'],
    queryFn: async () => {
      if (!tenant) return { items: [] as User[] }
      return await listUsers({ tenant, role: 'staff', page: 1, size: 200 })
    },
    enabled: !!tenant,
  })

  const { data: tenantSettings } = useQuery({
    queryKey: ['tenantSettings', tenant],
    queryFn: () => getTenantSettings(tenant!),
    enabled: !!tenant,
  })

  const { data: profilesData } = useQuery({
    queryKey: ['permissionProfiles', tenant],
    queryFn: async () => {
      if (!tenant) return { profiles: [] as PermissionProfile[], assignable_caps: [] }
      return await getPermissionProfiles(tenant)
    },
    enabled: !!tenant,
  })

  const tenantCaps = useMemo(() => {
    const raw = (tenantSettings?.capabilities ?? []).map((c: string) => c.toLowerCase())
    const set = new Set(raw)
    // Expand legacy caps into their fine-grained equivalents
    const legacy: Record<string, string[]> = {
      'salon.appointments': ['salon.appointments.view', 'salon.appointments.edit', 'salon.appointments.delete'],
      'salon.services': ['salon.services.view', 'salon.services.edit'],
      'core.dashboard': ['core.dashboard.view'],
      'core.customers': ['core.customers.view', 'core.customers.edit', 'core.customers.edit_sensitive'],
      'core.reports': ['core.reports.view'],
      'salon.professionals': ['salon.professionals.view', 'salon.professionals.edit'],
      'store.orders': ['store.orders.view', 'store.orders.edit', 'store.orders.edit_sensitive', 'store.orders.delete'],
    }
    for (const [leg, list] of Object.entries(legacy)) {
      if (set.has(leg)) list.forEach((c) => set.add(c))
    }
    return set
  }, [tenantSettings])

  const portalUserByEmail = useMemo(() => {
    const map: Record<string, User> = {}
    for (const u of portalUsersData?.items ?? []) {
      const email = (u.email || '').trim().toLowerCase()
      if (email) map[email] = u
    }
    return map
  }, [portalUsersData])

  const profiles = profilesData?.profiles ?? []

  async function handleSave(userId: string | null, email: string, caps: string[], isNew: boolean) {
    if (!tenant || !email.trim()) {
      showAlert('Staff email is required to grant portal access.', 'error')
      return
    }
    try {
      if (userId) {
        await updateUser(userId, { caps })
        showAlert('Portal access updated.', 'success')
      } else {
        try {
          await createUser({
            email: email.trim().toLowerCase(),
            password: crypto.getRandomValues(new Uint8Array(12)).reduce((a, b) => a + b.toString(16).padStart(2, '0'), ''),
            role: 'staff',
            tenant,
            display_name: email.split('@')[0],
            caps,
          })
          showAlert('Portal access granted. Set their password via Change Password.', 'success')
        } catch (err: any) {
          const msg = String(err?.response?.data?.detail || '')
          if (msg.toLowerCase().includes('already exists') || msg.toLowerCase().includes('unique')) {
            const fresh = await listUsers({ tenant, role: 'staff', page: 1, size: 200 })
            const existing = fresh.items.find((u) => (u.email || '').trim().toLowerCase() === email.trim().toLowerCase())
            if (existing?.id) {
              await updateUser(existing.id, { caps })
              showAlert('Portal access updated.', 'success')
            } else throw err
          } else throw err
        }
      }
      await qc.refetchQueries({ queryKey: ['users', tenant, 'staff'] })
    } catch (e: any) {
      showAlert(String(e?.response?.data?.detail || e?.message || 'Failed to save'), 'error')
      throw e
    }
  }

  async function handleRevoke(userId: string) {
    const user = portalUsersData?.items.find((u) => u.id === userId)
    const isDisabled = user?.status === 'disabled'
    if (isDisabled) {
      // Restore
      try {
        await updateUser(userId, { status: 'active' })
        showAlert('Portal access restored.', 'success')
        await qc.refetchQueries({ queryKey: ['users', tenant, 'staff'] })
      } catch (e: any) {
        showAlert(String(e?.response?.data?.detail || 'Failed to restore'), 'error')
      }
      return
    }
    const ok = await showConfirm({ title: 'Revoke portal access', message: 'This staff member will no longer be able to log in. You can restore access later.' })
    if (!ok) return
    try {
      await updateUser(userId, { status: 'disabled' })
      showAlert('Portal access revoked.', 'success')
      await qc.refetchQueries({ queryKey: ['users', tenant, 'staff'] })
    } catch (e: any) {
      showAlert(String(e?.response?.data?.detail || 'Failed to revoke'), 'error')
    }
  }

  if (!canManage) {
    return <Alert severity="warning">Only Tenant Admins can manage portal access.</Alert>
  }

  return (
    <Box>
      <Stack direction="row" alignItems="flex-start" justifyContent="space-between" sx={{ mb: 1 }}>
        <Box>
          <Typography variant="h6" fontWeight={700}>Staff Portal Access</Typography>
          <Typography variant="body2" color="text.secondary">
            Control which pages each staff member can see after they log in to the portal.
            Use quick profiles (Viewer / Editor / Manager) or choose individual page permissions.
          </Typography>
        </Box>
      </Stack>

      {/* Profile legend */}
      <Stack direction="row" spacing={1} sx={{ mb: 3 }} flexWrap="wrap">
        <Typography variant="caption" color="text.secondary" sx={{ alignSelf: 'center' }}>Profiles:</Typography>
        <Chip label="Viewer — read-only" color="info" size="small" />
        <Chip label="Editor — view + edit" color="primary" size="small" />
        <Chip label="Manager — full operations" color="success" size="small" />
        <Chip label="Custom — specific pages" color="warning" size="small" />
      </Stack>

      {staffLoading ? (
        <Box display="flex" justifyContent="center" py={4}><CircularProgress /></Box>
      ) : (staffData?.items ?? []).length === 0 ? (
        <Alert severity="info">No staff found. Add staff members first.</Alert>
      ) : (
        (staffData?.items ?? []).map((s) => {
          const email = (s.email || '').trim().toLowerCase()
          const portalUser = email ? portalUserByEmail[email] ?? null : null
          return (
            <StaffPortalCard
              key={s.id}
              staff={s}
              portalUser={portalUser}
              tenantCaps={tenantCaps}
              profiles={profiles}
              onSave={handleSave}
              onRevoke={handleRevoke}
            />
          )
        })
      )}
    </Box>
  )
}
