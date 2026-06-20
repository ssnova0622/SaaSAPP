/**
 * PortalAccessDialog
 *
 * Visual module-access editor used inside the "Give portal access" and
 * "Edit assigned modules" dialogs.
 *
 * Shows:
 *   1. Profile quick-assign row  (Viewer / Editor / Manager)
 *   2. Feature × action card grid (same style as Modules & Capabilities)
 *
 * Accepts:
 *   caps          current selected capability IDs
 *   tenantCaps    set of caps the tenant has enabled (upper bound for staff)
 *   profiles      permission profiles from /meta/permission-profiles
 *   onChange      called whenever caps change
 */
import {
  Box, Button, Card, CardContent, Checkbox, Chip, Divider,
  FormControlLabel, Grid, Stack, Tooltip, Typography,
} from '@mui/material'
import type { PermissionProfile } from '@api/users'

// ─── Feature / module definitions ───────────────────────────────────────────

interface FeatureAction { label: string; cap: string; hint: string }
interface Feature { label: string; description: string; actions: FeatureAction[] }
interface ModuleDef { id: string; label: string; emoji: string; color: string; features: Feature[] }

export const MODULE_DEFS: ModuleDef[] = [
  {
    id: 'core', label: 'Core', emoji: '⚙️', color: '#2563eb',
    features: [
      {
        label: 'Dashboard', description: 'Analytics overview',
        actions: [{ label: 'View', cap: 'core.dashboard.view', hint: 'See the analytics dashboard' }],
      },
      {
        label: 'Customers', description: 'Customer profiles',
        actions: [
          { label: 'View', cap: 'core.customers.view', hint: 'Browse customer list' },
          { label: 'Edit', cap: 'core.customers.edit', hint: 'Create & update customers' },
          { label: 'PII', cap: 'core.customers.edit_sensitive', hint: 'Access phone & payment info' },
        ],
      },
      {
        label: 'Staff', description: 'Staff records',
        actions: [{ label: 'Manage', cap: 'core.staff', hint: 'Add, edit, view staff records' }],
      },
      {
        label: 'Users', description: 'Portal logins',
        actions: [
          { label: 'View', cap: 'core.users.view', hint: 'See portal user list' },
          { label: 'Edit', cap: 'core.users.edit', hint: 'Create / edit portal logins' },
        ],
      },
      {
        label: 'Reports', description: 'Reports & analytics',
        actions: [{ label: 'View', cap: 'core.reports.view', hint: 'Download & view reports' }],
      },
      {
        label: 'Settings', description: 'Tenant configuration',
        actions: [
          { label: 'View', cap: 'core.settings.view', hint: 'Read settings' },
          { label: 'Edit', cap: 'core.settings.edit', hint: 'Change non-sensitive settings' },
        ],
      },
      {
        label: 'Promotions', description: 'Campaigns',
        actions: [{ label: 'Access', cap: 'core.promotions', hint: 'Create & send promotions' }],
      },
      {
        label: 'Follow-ups', description: 'Auto messages',
        actions: [{ label: 'Access', cap: 'core.followups', hint: 'Configure follow-up rules' }],
      },
      {
        label: 'WhatsApp Bot', description: 'Bot builder',
        actions: [{ label: 'Manage', cap: 'core.whatsapp_menu', hint: 'Build WhatsApp menus & workflows' }],
      },
    ],
  },
  {
    id: 'salon', label: 'Salon / Clinic', emoji: '💇', color: '#0d9488',
    features: [
      {
        label: 'Services', description: 'Service catalog',
        actions: [
          { label: 'View', cap: 'salon.services.view', hint: 'Browse services list' },
          { label: 'Edit', cap: 'salon.services.edit', hint: 'Add / edit services' },
        ],
      },
      {
        label: 'Professionals', description: 'Stylists / doctors',
        actions: [
          { label: 'View',      cap: 'salon.professionals.view',           hint: 'View professional list' },
          { label: 'Edit',      cap: 'salon.professionals.edit',           hint: 'Edit slots & availability' },
          { label: 'Sensitive', cap: 'salon.professionals.edit_sensitive', hint: 'Edit fees, contact, bio' },
        ],
      },
      {
        label: 'Appointments', description: 'Booking management',
        actions: [
          { label: 'View',   cap: 'salon.appointments.view',   hint: 'See appointment list' },
          { label: 'Edit',   cap: 'salon.appointments.edit',   hint: 'Create, cancel, reschedule' },
          { label: 'Delete', cap: 'salon.appointments.delete', hint: 'Hard-delete appointments' },
        ],
      },
      {
        label: 'No-Show List', description: 'Blocked customers',
        actions: [
          { label: 'View', cap: 'salon.no_show_blocked.view', hint: 'See blocked customers' },
          { label: 'Edit', cap: 'salon.no_show_blocked.edit', hint: 'Reset no-show count' },
        ],
      },
    ],
  },
  {
    id: 'store', label: 'Store', emoji: '🛒', color: '#d97706',
    features: [
      {
        label: 'Orders', description: 'Customer orders',
        actions: [
          { label: 'View',      cap: 'store.orders.view',           hint: 'Browse orders' },
          { label: 'Edit',      cap: 'store.orders.edit',           hint: 'Update order status' },
          { label: 'Sensitive', cap: 'store.orders.edit_sensitive', hint: 'Refunds, payment details' },
        ],
      },
      {
        label: 'Catalog', description: 'Products',
        actions: [{ label: 'Manage', cap: 'store.catalog', hint: 'Add / edit products & categories' }],
      },
      {
        label: 'Inventory', description: 'Stock management',
        actions: [{ label: 'Manage', cap: 'store.inventory', hint: 'Track stock levels' }],
      },
    ],
  },
]

// Profile colours
const PROFILE_STYLE: Record<string, { color: 'info' | 'primary' | 'success' | 'warning' | 'default'; desc: string }> = {
  viewer:  { color: 'info',    desc: 'Read-only — can view but not change anything' },
  editor:  { color: 'primary', desc: 'Can view and create/edit records, no delete' },
  manager: { color: 'success', desc: 'Full operations — view, edit, manage (no sensitive data)' },
}

function capsForProfile(profileId: string, profiles: PermissionProfile[], tenantCaps: Set<string>): string[] {
  const p = profiles.find((x) => x.id === profileId)
  if (!p) return []
  return (p.caps || []).map((c) => c.toLowerCase()).filter((c) => tenantCaps.has(c))
}

// ─── Component ───────────────────────────────────────────────────────────────

interface Props {
  caps: string[]
  tenantCaps: Set<string>
  profiles: PermissionProfile[]
  onChange: (caps: string[]) => void
  error?: string | null
}

export default function PortalAccessDialog({ caps, tenantCaps, profiles, onChange, error }: Props) {
  const capsSet = new Set(caps.map((c) => c.toLowerCase()))

  // Detect current profile
  let currentProfile = 'custom'
  for (const pid of ['manager', 'editor', 'viewer']) {
    const pCaps = new Set(capsForProfile(pid, profiles, tenantCaps))
    if (pCaps.size === capsSet.size && [...pCaps].every((c) => capsSet.has(c))) {
      currentProfile = pid
      break
    }
  }
  if (capsSet.size === 0) currentProfile = 'none'

  function applyProfile(profileId: string) {
    onChange(capsForProfile(profileId, profiles, tenantCaps))
  }

  function toggleCap(cap: string, on: boolean) {
    const s = new Set(capsSet)
    if (on) s.add(cap); else s.delete(cap)
    onChange(Array.from(s))
  }

  return (
    <Box>
      {/* ── Section 1: Profile quick-assign ─────────────────────── */}
      <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 0.5 }}>
        Quick assign — choose a profile
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ mb: 1.5, display: 'block' }}>
        Profiles are predefined sets of page access. Pick one, or customize below.
      </Typography>

      <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 2 }}>
        {(['viewer', 'editor', 'manager'] as const).map((pid) => {
          const meta = PROFILE_STYLE[pid]
          const active = currentProfile === pid
          return (
            <Tooltip key={pid} title={meta.desc} arrow placement="top">
              <Button
                size="small"
                variant={active ? 'contained' : 'outlined'}
                color={meta.color}
                onClick={() => applyProfile(pid)}
                sx={{ textTransform: 'capitalize' }}
              >
                {pid.charAt(0).toUpperCase() + pid.slice(1)}
                {active && ' ✓'}
              </Button>
            </Tooltip>
          )
        })}
        <Button
          size="small"
          variant="outlined"
          color="warning"
          onClick={() => onChange([])}
          sx={{ textTransform: 'none' }}
        >
          Clear all
        </Button>
        {currentProfile === 'custom' && capsSet.size > 0 && (
          <Chip label="Custom" color="warning" size="small" sx={{ alignSelf: 'center' }} />
        )}
      </Stack>

      <Divider sx={{ mb: 2 }} />

      {/* ── Section 2: Feature × action matrix ──────────────────── */}
      <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 0.5 }}>
        Or pick specific page access
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ mb: 1.5, display: 'block' }}>
        Staff will <strong>only see pages</strong> for the checkboxes ticked below.
        Greyed-out options are not enabled for this tenant.
      </Typography>

      <Grid container spacing={1.5}>
        {MODULE_DEFS.map((mod) => {
          const modVisible = mod.features.some((f) => f.actions.some((a) => tenantCaps.has(a.cap)))
          if (!modVisible) return null
          return (
            <Grid item xs={12} md={6} key={mod.id}>
              <Card
                variant="outlined"
                sx={{ borderLeft: `4px solid ${mod.color}`, bgcolor: `${mod.color}08`, height: '100%' }}
              >
                <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography variant="subtitle2" fontWeight={700} sx={{ color: mod.color, mb: 1 }}>
                    {mod.emoji} {mod.label}
                  </Typography>
                  {mod.features.map((feature) => {
                    const visibleActions = feature.actions.filter((a) => tenantCaps.has(a.cap))
                    if (visibleActions.length === 0) return null
                    return (
                      <Box key={feature.label} sx={{ mb: 0.5 }}>
                        <Stack direction="row" alignItems="flex-start" spacing={1}>
                          <Box sx={{ minWidth: 105, pt: 0.5 }}>
                            <Typography variant="caption" color="text.secondary" fontWeight={500}>
                              {feature.label}
                            </Typography>
                          </Box>
                          <Stack direction="row" flexWrap="wrap" gap={0}>
                            {visibleActions.map((action) => (
                              <Tooltip key={action.cap} title={action.hint} arrow placement="top">
                                <FormControlLabel
                                  control={
                                    <Checkbox
                                      size="small"
                                      checked={capsSet.has(action.cap)}
                                      onChange={(e) => toggleCap(action.cap, e.target.checked)}
                                      sx={{ py: 0.25 }}
                                    />
                                  }
                                  label={
                                    <Typography variant="caption">{action.label}</Typography>
                                  }
                                  sx={{ mr: 0.5, ml: 0 }}
                                />
                              </Tooltip>
                            ))}
                          </Stack>
                        </Stack>
                      </Box>
                    )
                  })}
                </CardContent>
              </Card>
            </Grid>
          )
        })}
      </Grid>

      {error && (
        <Typography color="error" variant="body2" sx={{ mt: 2 }}>
          {error}
        </Typography>
      )}
    </Box>
  )
}
