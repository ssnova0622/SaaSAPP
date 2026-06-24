/**
 * Access Manager — card-based staff portal permission manager.
 *
 * Each staff member who has a portal login gets a card showing:
 *   • Their name / email / current profile chip
 *   • Quick-assign profile buttons (Viewer / Editor / Manager)
 *   • Collapsible feature × action matrix for custom permissions
 *
 * Design matches the ModulesCapabilities and PortalAccess pages.
 */
import {
  Alert, Box, Button, Card, CardContent, Checkbox,
  Chip, CircularProgress, Collapse, Divider, FormControlLabel,
  Grid, IconButton, Paper, Stack, Tooltip, Typography,
} from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import LockIcon from '@mui/icons-material/Lock'
import PersonIcon from '@mui/icons-material/Person'
import { useEffect, useMemo, useState } from 'react'
import {
  listUsers, getPermissionProfiles, updateUserCaps,
  type User, type PermissionProfile, type AssignableCap,
} from '@api/users'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useAuth } from '../../contexts/AuthContext'

// ─── Feature matrix (mirrors ModulesCapabilities & PortalAccess) ─────────────
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
        { label: 'PII / Sensitive', cap: 'core.customers.edit_sensitive' },
      ]},
      { label: 'Staff Records', description: 'Staff management', actions: [{ label: 'Manage', cap: 'core.staff' }] },
      { label: 'Portal Users', description: 'Portal logins & caps', actions: [
        { label: 'View', cap: 'core.users.view' },
        { label: 'Edit', cap: 'core.users.edit' },
      ]},
      { label: 'Reports', description: 'Reports & analytics', actions: [{ label: 'View', cap: 'core.reports.view' }] },
      { label: 'Settings', description: 'Tenant configuration', actions: [
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
      { label: 'Inventory', description: 'Stock levels', actions: [{ label: 'Manage', cap: 'store.inventory' }] },
    ],
  },
]

const ALL_FEATURE_CAPS = new Set(MODULE_DEFS.flatMap(m => m.features.flatMap(f => f.actions.map(a => a.cap))))

const PROFILE_META: Record<string, { label: string; color: 'info' | 'primary' | 'success' | 'warning' | 'default'; bg: string }> = {
  viewer:  { label: 'Viewer',  color: 'info',    bg: '#e0f2fe' },
  editor:  { label: 'Editor',  color: 'primary',  bg: '#dbeafe' },
  manager: { label: 'Manager', color: 'success',  bg: '#dcfce7' },
  custom:  { label: 'Custom',  color: 'warning',  bg: '#fef9c3' },
  none:    { label: 'No caps', color: 'default',  bg: '#f1f5f9' },
}

function detectProfileName(userCaps: string[], profiles: PermissionProfile[], tenantCaps: Set<string>): string {
  const effective = new Set(userCaps.map(c => c.toLowerCase()).filter(c => tenantCaps.has(c)))
  for (const p of profiles) {
    if (p.id === 'custom') continue
    const pCaps = new Set((p.caps || []).map(c => c.toLowerCase()).filter(c => tenantCaps.has(c)))
    if (pCaps.size === effective.size && [...pCaps].every(c => effective.has(c))) return p.id
  }
  return effective.size === 0 ? 'none' : 'custom'
}

// ─── Staff card ───────────────────────────────────────────────────────────────
interface StaffCardProps {
  staffUser: User
  profiles: PermissionProfile[]
  assignableCaps: AssignableCap[]
  tenantCaps: Set<string>
  onSaved: (updated: User) => void
}

function StaffCard({ staffUser, profiles, assignableCaps: _ac, tenantCaps, onSaved }: StaffCardProps) {
  const initCaps = useMemo(() => (staffUser.caps || []).map(c => c.toLowerCase()), [staffUser.caps])
  const [selectedCaps, setSelectedCaps] = useState<Set<string>>(new Set(initCaps))
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<{ ok?: string; error?: string } | null>(null)
  const [expanded, setExpanded] = useState(false)

  const currentProfile = detectProfileName([...selectedCaps], profiles, tenantCaps)
  const meta = PROFILE_META[currentProfile] ?? PROFILE_META.none

  const isDirty = useMemo(() => {
    const init = new Set(initCaps)
    if (init.size !== selectedCaps.size) return true
    for (const c of selectedCaps) if (!init.has(c)) return true
    return false
  }, [initCaps, selectedCaps])

  function applyProfile(profileId: string) {
    const p = profiles.find(x => x.id === profileId)
    if (!p || profileId === 'custom') return
    setSelectedCaps(new Set((p.caps || []).map(c => c.toLowerCase())))
  }

  function toggleCap(cap: string) {
    setSelectedCaps(prev => {
      const next = new Set(prev)
      next.has(cap) ? next.delete(cap) : next.add(cap)
      return next
    })
  }

  async function save() {
    setSaving(true); setMsg(null)
    try {
      const updated = await updateUserCaps(staffUser.id!, [...selectedCaps])
      onSaved(updated)
      setMsg({ ok: 'Permissions saved.' })
    } catch {
      setMsg({ error: 'Failed to save.' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent sx={{ pb: 1 }}>

        {/* ── Header: name + profile chip ── */}
        <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ sm: 'center' }} spacing={1} sx={{ mb: 1.5 }}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Box sx={{ width: 36, height: 36, borderRadius: '50%', background: meta.bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <PersonIcon sx={{ fontSize: 20, color: `${meta.color}.main` }} />
            </Box>
            <Box>
              <Typography variant="subtitle2" fontWeight={700}>{staffUser.display_name || staffUser.email}</Typography>
              <Typography variant="caption" color="text.secondary">{staffUser.email}</Typography>
            </Box>
          </Stack>
          <Chip
            label={meta.label}
            color={meta.color}
            size="small"
            sx={{ fontWeight: 600 }}
          />
        </Stack>

        <Divider sx={{ mb: 1.5 }} />

        {/* ── Quick-assign profile buttons ── */}
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, fontWeight: 600 }}>
          QUICK ASSIGN
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 1.5 }}>
          {profiles.filter(p => p.id !== 'custom').map(p => {
            const active = currentProfile === p.id
            const pm = PROFILE_META[p.id] ?? PROFILE_META.none
            return (
              <Button
                key={p.id}
                size="small"
                variant={active ? 'contained' : 'outlined'}
                color={pm.color}
                onClick={() => applyProfile(p.id)}
                sx={{ textTransform: 'none', borderRadius: 2, fontWeight: active ? 700 : 400 }}
              >
                {p.label}
              </Button>
            )
          })}
        </Stack>

        {/* ── Custom matrix toggle ── */}
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Button
            size="small"
            variant="text"
            startIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            onClick={() => setExpanded(e => !e)}
            sx={{ textTransform: 'none', color: 'text.secondary' }}
          >
            {expanded ? 'Hide' : 'Custom'} permission matrix
          </Button>
          <Stack direction="row" spacing={1} alignItems="center">
            {msg?.ok && <Typography variant="caption" color="success.main">{msg.ok}</Typography>}
            {msg?.error && <Typography variant="caption" color="error">{msg.error}</Typography>}
            <Button
              size="small"
              variant="contained"
              disabled={!isDirty || saving}
              onClick={save}
              startIcon={saving ? <CircularProgress size={12} /> : <CheckCircleIcon />}
              sx={{ textTransform: 'none' }}
            >
              Save
            </Button>
          </Stack>
        </Stack>
      </CardContent>

      {/* ── Collapsible capability matrix ── */}
      <Collapse in={expanded} unmountOnExit>
        <Divider />
        <Box sx={{ px: 2, py: 2, background: '#f8fafc' }}>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
            Enable individual capabilities — selecting any combination that doesn't match a preset will set the profile to <strong>Custom</strong>.
          </Typography>
          <Grid container spacing={2}>
            {MODULE_DEFS.map(mod => {
              const modCaps = new Set(mod.features.flatMap(f => f.actions.map(a => a.cap)))
              const hasAnyModCap = [...modCaps].some(c => tenantCaps.has(c))
              if (!hasAnyModCap) return null
              return (
                <Grid item xs={12} md={6} key={mod.id}>
                  <Box sx={{ mb: 1 }}>
                    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.5 }}>
                      <Typography fontSize={14}>{mod.emoji}</Typography>
                      <Typography variant="caption" fontWeight={700} color="primary.main">{mod.label}</Typography>
                    </Stack>
                    {mod.features.map(feature => {
                      const featureCaps = feature.actions.filter(a => tenantCaps.has(a.cap))
                      if (featureCaps.length === 0) return null
                      return (
                        <Box key={feature.label} sx={{ mb: 0.5 }}>
                          <Stack direction="row" alignItems="center" spacing={0.5} flexWrap="wrap">
                            <Typography variant="caption" color="text.secondary" sx={{ minWidth: 110 }}>
                              {feature.label}
                            </Typography>
                            {featureCaps.map(action => (
                              <Tooltip key={action.cap} title={action.cap} arrow placement="top">
                                <FormControlLabel
                                  control={
                                    <Checkbox
                                      size="small"
                                      checked={selectedCaps.has(action.cap)}
                                      onChange={() => toggleCap(action.cap)}
                                      sx={{ p: 0.5 }}
                                    />
                                  }
                                  label={<Typography variant="caption">{action.label}</Typography>}
                                  sx={{ mr: 0.5, ml: 0 }}
                                />
                              </Tooltip>
                            ))}
                          </Stack>
                        </Box>
                      )
                    })}
                    <Divider sx={{ mt: 0.5 }} />
                  </Box>
                </Grid>
              )
            })}

            {/* Preserve caps outside the feature matrix */}
            {(() => {
              const extra = [...selectedCaps].filter(c => !ALL_FEATURE_CAPS.has(c) && tenantCaps.has(c))
              if (!extra.length) return null
              return (
                <Grid item xs={12}>
                  <Typography variant="caption" color="text.secondary" fontWeight={700}>Other / Custom</Typography>
                  <Stack direction="row" flexWrap="wrap" spacing={0.5} sx={{ mt: 0.5 }}>
                    {extra.map(c => (
                      <Chip key={c} label={c} size="small" onDelete={() => toggleCap(c)} />
                    ))}
                  </Stack>
                </Grid>
              )
            })()}
          </Grid>
        </Box>
      </Collapse>
    </Card>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function AccessManager() {
  const { effectiveTenant } = useEffectiveTenant()
  const { isTenantAdmin, isSuperAdmin } = useAuth()
  const tenant = effectiveTenant || ''

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [staffUsers, setStaffUsers] = useState<User[]>([])
  const [profiles, setProfiles] = useState<PermissionProfile[]>([])
  const [assignableCaps, setAssignableCaps] = useState<AssignableCap[]>([])
  const [tenantCaps, setTenantCaps] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!tenant) return
    setLoading(true); setError(null)
    Promise.all([
      listUsers({ tenant, role: 'staff', size: 100 }),
      getPermissionProfiles(tenant),
    ])
      .then(([users, profilesRes]) => {
        setStaffUsers(users.items)
        setProfiles(profilesRes.profiles)
        setAssignableCaps(profilesRes.assignable_caps)
        setTenantCaps(new Set(profilesRes.assignable_caps.map((c: AssignableCap) => c.id)))
      })
      .catch(e => setError(String(e?.response?.data?.detail || e?.message || 'Failed to load')))
      .finally(() => setLoading(false))
  }, [tenant])

  const handleSaved = (updated: User) => {
    setStaffUsers(prev => prev.map(u => u.id === updated.id ? { ...u, caps: updated.caps } : u))
  }

  if (!isTenantAdmin && !isSuperAdmin) {
    return <Alert severity="error" sx={{ m: 2 }}>Access denied — Tenant Admin role required.</Alert>
  }

  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
        <LockIcon fontSize="small" color="primary" />
        <Typography variant="subtitle1" fontWeight={700}>Access Manager</Typography>
      </Stack>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Control what each staff member can see and do after logging in to the portal.
        Tenant Admin always has full access to all enabled modules.
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loading ? (
        <Box display="flex" justifyContent="center" py={6}><CircularProgress /></Box>
      ) : staffUsers.length === 0 ? (
        <Paper variant="outlined" sx={{ p: 4, textAlign: 'center' }}>
          <PersonIcon sx={{ fontSize: 40, color: 'text.disabled', mb: 1 }} />
          <Typography color="text.secondary">
            No staff portal accounts found. Create portal access from the <strong>Staff</strong> page.
          </Typography>
        </Paper>
      ) : (
        staffUsers.map(u => (
          <StaffCard
            key={u.id}
            staffUser={u}
            profiles={profiles}
            assignableCaps={assignableCaps}
            tenantCaps={tenantCaps}
            onSaved={handleSaved}
          />
        ))
      )}
    </Box>
  )
}
