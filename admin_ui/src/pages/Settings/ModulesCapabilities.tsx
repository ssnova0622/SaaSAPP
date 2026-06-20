/**
 * ModulesCapabilities — clean, visual Modules & Capabilities editor.
 *
 * Replaces the confusing 5-sub-tab approach. Shows:
 *   1. Module toggle cards  — flip a module on/off for the tenant
 *   2. Capability matrix    — per-module, feature × action grid
 *
 * Only visible to Super Admin (settings-level feature gating).
 */
import {
  Alert, Box, Button, Card, CardContent, Checkbox, Chip,
  Divider, FormControlLabel, Grid, Stack, Switch, Tooltip, Typography,
} from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import LockIcon from '@mui/icons-material/Lock'
import { TenantSettings } from '@api/tenants'
import { RegistryItem } from '@api/modules'

// ─── Types ──────────────────────────────────────────────────────────────────

interface Props {
  settings: TenantSettings | null
  registry: RegistryItem[]
  saving: boolean
  saveMsg: { ok?: string; error?: string } | null
  onSave: (patch: Partial<TenantSettings>) => void
  onChange: (patch: Partial<TenantSettings>) => void
}

// ─── Feature definition (readable grouping of raw capability IDs) ────────────
//
// Each feature maps to capability IDs for the actions the UI exposes.
// Only capabilities that exist in the registry are shown.

interface FeatureAction {
  label: string
  cap: string
  description: string
}

interface Feature {
  label: string           // e.g. "Appointments"
  description: string
  actions: FeatureAction[]
}

interface ModuleDef {
  id: string
  label: string
  emoji: string
  description: string
  features: Feature[]
}

const MODULE_DEFS: ModuleDef[] = [
  {
    id: 'core',
    label: 'Core',
    emoji: '⚙️',
    description: 'Dashboard, customers, staff, reports, promotions',
    features: [
      {
        label: 'Dashboard',
        description: 'Analytics overview',
        actions: [
          { label: 'View', cap: 'core.dashboard.view', description: 'See the dashboard' },
        ],
      },
      {
        label: 'Customers',
        description: 'Customer profiles and contact info',
        actions: [
          { label: 'View',      cap: 'core.customers.view',           description: 'Browse customer list' },
          { label: 'Edit',      cap: 'core.customers.edit',           description: 'Create & update customers' },
          { label: 'PII / Sensitive', cap: 'core.customers.edit_sensitive', description: 'Access phone, payment details' },
        ],
      },
      {
        label: 'Staff',
        description: 'Staff records management',
        actions: [
          { label: 'Manage', cap: 'core.staff', description: 'View, add, edit staff records' },
        ],
      },
      {
        label: 'Portal Users',
        description: 'Create / manage staff portal logins and permissions',
        actions: [
          { label: 'View',            cap: 'core.users.view',           description: 'List portal users' },
          { label: 'Edit',            cap: 'core.users.edit',           description: 'Create/edit staff logins' },
          { label: 'Sensitive / Roles', cap: 'core.users.edit_sensitive', description: 'Edit roles, caps, passwords' },
        ],
      },
      {
        label: 'Reports',
        description: 'Daily & period reports, PDF exports',
        actions: [
          { label: 'View', cap: 'core.reports.view', description: 'Read and download reports' },
        ],
      },
      {
        label: 'Settings',
        description: 'Tenant configuration',
        actions: [
          { label: 'View',      cap: 'core.settings.view',           description: 'Read settings' },
          { label: 'Edit',      cap: 'core.settings.edit',           description: 'Change non-sensitive settings' },
          { label: 'Sensitive', cap: 'core.settings.edit_sensitive', description: 'Edit API keys, billing info' },
        ],
      },
      {
        label: 'Promotions',
        description: 'Create & send bulk WhatsApp / Email campaigns',
        actions: [
          { label: 'Access', cap: 'core.promotions', description: 'Create, view, send promotions' },
        ],
      },
      {
        label: 'Follow-ups',
        description: 'Automated follow-up messages',
        actions: [
          { label: 'Access', cap: 'core.followups', description: 'Manage follow-up rules' },
        ],
      },
      {
        label: 'Retention',
        description: 'Customer retention analytics',
        actions: [
          { label: 'Access', cap: 'core.retention', description: 'View retention metrics' },
        ],
      },
      {
        label: 'WhatsApp Bot',
        description: 'Bot menus, triggers, workflows',
        actions: [
          { label: 'Manage', cap: 'core.whatsapp_menu', description: 'Build and configure WhatsApp bot' },
        ],
      },
    ],
  },
  {
    id: 'salon',
    label: 'Salon / Clinic',
    emoji: '💇',
    description: 'Appointments, professionals, services',
    features: [
      {
        label: 'Services',
        description: 'Service catalog (Haircut, Facial, etc.)',
        actions: [
          { label: 'View', cap: 'salon.services.view', description: 'Browse service list' },
          { label: 'Edit', cap: 'salon.services.edit', description: 'Add/edit services' },
        ],
      },
      {
        label: 'Professionals',
        description: 'Stylists, doctors, trainers',
        actions: [
          { label: 'View',      cap: 'salon.professionals.view',           description: 'View professional list' },
          { label: 'Edit',      cap: 'salon.professionals.edit',           description: 'Edit slots & availability' },
          { label: 'Sensitive', cap: 'salon.professionals.edit_sensitive', description: 'Edit fees, contact, bio' },
          { label: 'Create',    cap: 'salon.professionals.create',         description: 'Add new professionals' },
          { label: 'Delete',    cap: 'salon.professionals.delete',         description: 'Remove professionals' },
        ],
      },
      {
        label: 'Appointments',
        description: 'Booking management',
        actions: [
          { label: 'View',   cap: 'salon.appointments.view',   description: 'See appointment list' },
          { label: 'Edit',   cap: 'salon.appointments.edit',   description: 'Complete, cancel, reschedule' },
          { label: 'Delete', cap: 'salon.appointments.delete', description: 'Hard delete appointments' },
        ],
      },
      {
        label: 'No-Show Blocked',
        description: 'Blocked customers due to no-shows',
        actions: [
          { label: 'View', cap: 'salon.no_show_blocked.view', description: 'See blocked list' },
          { label: 'Edit', cap: 'salon.no_show_blocked.edit', description: 'Reset no-show count' },
        ],
      },
    ],
  },
  {
    id: 'store',
    label: 'Store',
    emoji: '🛒',
    description: 'Products, orders, catalog',
    features: [
      {
        label: 'Orders',
        description: 'Customer orders and carts',
        actions: [
          { label: 'View',      cap: 'store.orders.view',           description: 'Browse orders' },
          { label: 'Edit',      cap: 'store.orders.edit',           description: 'Update order status' },
          { label: 'Sensitive', cap: 'store.orders.edit_sensitive', description: 'Refunds, payment details' },
          { label: 'Cancel',    cap: 'store.orders.delete',         description: 'Void/cancel orders' },
        ],
      },
      {
        label: 'Product Catalog',
        description: 'Products, categories, offers',
        actions: [
          { label: 'Manage', cap: 'store.catalog', description: 'Add/edit products & categories' },
        ],
      },
      {
        label: 'Inventory',
        description: 'Stock management',
        actions: [
          { label: 'Manage', cap: 'store.inventory', description: 'Track stock levels' },
        ],
      },
    ],
  },
  {
    id: 'ai',
    label: 'AI Features',
    emoji: '🤖',
    description: 'AI recommendations, predictions, insights',
    features: [
      {
        label: 'AI Capabilities',
        description: 'AI caps are managed by the plan. Enable the AI module to unlock them.',
        actions: [],  // AI caps are managed separately (not user-assignable in this UI)
      },
    ],
  },
]

// ─── Legacy-cap helpers ───────────────────────────────────────────────────────
//
// OLD-style / legacy caps (e.g. "salon.professionals", "salon.appointments") were
// seeded as defaults and are NOT shown as checkboxes in the matrix.
//
// Problem A — DISPLAY: The DB has "salon.professionals" but NOT "salon.professionals.view".
//   → Checkboxes appear UNCHECKED even though the page is still showing.
//   → User thinks they don't need to click Save.
//
// Problem B — SAVE: When we do Save, "salon.professionals" is included in enabledCaps
//   (because it came from settings.capabilities) and silently saved back, keeping
//   the page visible forever.
//
// Fix for A: expand legacy caps to their modern equivalents when building the display set.
// Fix for B: on save, strip ALL caps that belong to managed modules but are NOT in
//   the feature matrix. Only the checkboxes-visible new-style caps are saved.

const LEGACY_TO_MODERN: Record<string, string[]> = {
  'salon.professionals':        ['salon.professionals.view'],
  'salon.professionals.manage': ['salon.professionals.edit_sensitive'],
  'salon.appointments':         ['salon.appointments.view', 'salon.appointments.edit'],
  'salon.services':             ['salon.services.view'],
  'salon.no_show_blocked':      ['salon.no_show_blocked.view'],
  'store.orders':               ['store.orders.view', 'store.orders.edit'],
  'core.dashboard':             ['core.dashboard.view'],
  'core.settings':              ['core.settings.view'],
  'core.users':                 ['core.users.view'],
  'core.customers':             ['core.customers.view'],
  'core.reports':               ['core.reports.view'],
}

/** Expand any legacy/alias caps into their modern equivalents for display. */
function expandLegacyCaps(rawCaps: string[]): Set<string> {
  const result = new Set<string>()
  for (const c of rawCaps) {
    const key = c.toLowerCase()
    const modern = LEGACY_TO_MODERN[key]
    if (modern) {
      modern.forEach(m => result.add(m))
    } else {
      result.add(key)
    }
  }
  return result
}

const _MANAGED_MODULE_IDS = new Set(MODULE_DEFS.map(m => m.id))
// Caps that appear as checkboxes in the feature matrix (new-style only; no legacy aliases)
const _MANAGED_CAP_IDS = new Set(
  MODULE_DEFS.flatMap(m => m.features.flatMap(f => f.actions.map(a => a.cap)))
)

// ─── Module card ─────────────────────────────────────────────────────────────

function ModuleCard({
  def, enabled, onToggle,
}: { def: ModuleDef; enabled: boolean; onToggle: (on: boolean) => void }) {
  return (
    <Card
      variant="outlined"
      sx={{
        cursor: 'pointer',
        border: enabled ? '2px solid #2563eb' : '1px solid #e2e8f0',
        background: enabled ? '#eff6ff' : '#f8fafc',
        transition: 'all 0.15s',
        '&:hover': { boxShadow: 2 },
      }}
      onClick={() => onToggle(!enabled)}
    >
      <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography fontSize={22}>{def.emoji}</Typography>
            <Box>
              <Typography variant="subtitle2" fontWeight={700} color={enabled ? 'primary.main' : 'text.primary'}>
                {def.label}
              </Typography>
              <Typography variant="caption" color="text.secondary">{def.description}</Typography>
            </Box>
          </Stack>
          <Switch
            checked={enabled}
            size="small"
            onChange={(e) => { e.stopPropagation(); onToggle(e.target.checked) }}
            color="primary"
          />
        </Stack>
        {enabled && (
          <Chip
            label="Enabled"
            size="small"
            color="primary"
            icon={<CheckCircleIcon />}
            sx={{ mt: 1.5, fontSize: 11 }}
          />
        )}
      </CardContent>
    </Card>
  )
}

// ─── Capability row (one feature, multiple action checkboxes) ────────────────

function CapabilityRow({
  feature, enabledCaps, registryIds, onToggle,
}: {
  feature: Feature
  enabledCaps: Set<string>
  registryIds: Set<string>
  onToggle: (cap: string, on: boolean) => void
}) {
  if (feature.actions.length === 0) return null

  return (
    <Stack direction={{ xs: 'column', sm: 'row' }} alignItems={{ sm: 'center' }} spacing={1} py={0.5}>
      <Box minWidth={160}>
        <Typography variant="body2" fontWeight={600}>{feature.label}</Typography>
        <Typography variant="caption" color="text.secondary">{feature.description}</Typography>
      </Box>
      <Stack direction="row" flexWrap="wrap" gap={0.5}>
        {feature.actions.map((action) => {
          const exists = registryIds.has(action.cap)
          const checked = enabledCaps.has(action.cap)
          return (
            <Tooltip key={action.cap} title={action.description} arrow placement="top">
              <FormControlLabel
                control={
                  <Checkbox
                    size="small"
                    checked={checked}
                    disabled={!exists}
                    onChange={(e) => onToggle(action.cap, e.target.checked)}
                  />
                }
                label={
                  <Typography variant="caption" color={exists ? 'text.primary' : 'text.disabled'}>
                    {action.label}
                  </Typography>
                }
                sx={{ mr: 0, ml: 0 }}
              />
            </Tooltip>
          )
        })}
      </Stack>
    </Stack>
  )
}

// ─── Main component ──────────────────────────────────────────────────────────

export default function ModulesCapabilities({ settings, registry, saving, saveMsg, onSave, onChange }: Props) {
  if (!settings) return null

  const enabledModules = new Set((settings.modules || []).map((m) => m.toLowerCase()))
  // Expand legacy caps (e.g. "salon.professionals" → "salon.professionals.view") so that
  // the checkboxes reflect the EFFECTIVE access already granted, not just the raw stored caps.
  const enabledCaps = expandLegacyCaps(settings.capabilities || [])
  const registryIds = new Set(registry.map((r) => r.id.toLowerCase()))

  function toggleModule(id: string, on: boolean) {
    const mods = new Set(enabledModules)
    if (on) mods.add(id); else mods.delete(id)
    onChange({ modules: Array.from(mods).sort() })
  }

  function toggleCap(cap: string, on: boolean) {
    const caps = new Set(enabledCaps)
    if (on) caps.add(cap); else caps.delete(cap)
    onChange({ capabilities: Array.from(caps).sort() })
  }

  function applyDefaults() {
    const defaultCaps = registry
      .filter((r) => r.type === 'capability' && r.default && enabledModules.has((r as any).module?.toLowerCase?.() || ''))
      .map((r) => r.id.toLowerCase())
    const merged = new Set([...enabledCaps, ...defaultCaps])
    onChange({ capabilities: Array.from(merged).sort() })
  }

  function clearAll() {
    onChange({ modules: [], capabilities: [] })
  }

  function handleSave() {
    // Strip legacy / unknown caps that belong to modules this UI manages but are
    // NOT surfaced as checkboxes in the matrix (e.g. "salon.professionals",
    // "salon.appointments" — the old-style caps seeded as defaults).
    // Without this, unchecking "Professionals View" leaves the legacy cap in
    // place and the sidebar keeps showing the page.
    const cleanCaps = [
      // Only caps the user explicitly checked that are in the feature matrix
      ...Array.from(enabledCaps).filter(c => _MANAGED_CAP_IDS.has(c)),
      // Preserve caps from modules NOT covered by this UI (future-proof)
      ...Array.from(enabledCaps).filter(c => !_MANAGED_MODULE_IDS.has(c.split('.')[0])),
    ]
    onSave({
      modules: Array.from(enabledModules).sort(),
      capabilities: Array.from(new Set(cleanCaps)).sort(),
    })
  }

  return (
    <Box>
      {/* ── Section 1: Module cards ─────────────────────────────────── */}
      <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 0.5 }}>
        Modules
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Toggle which product areas are available for this tenant. Disabling a module hides all its pages from the portal.
      </Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        {MODULE_DEFS.map((def) => (
          <Grid item xs={12} sm={6} md={4} key={def.id}>
            <ModuleCard
              def={def}
              enabled={enabledModules.has(def.id)}
              onToggle={(on) => toggleModule(def.id, on)}
            />
          </Grid>
        ))}
      </Grid>

      {/* ── Section 2: Capability matrix ────────────────────────────── */}
      <Divider sx={{ my: 2 }} />
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
        <LockIcon fontSize="small" color="action" />
        <Typography variant="subtitle1" fontWeight={700}>Capabilities</Typography>
      </Stack>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Fine-tune which actions are available within each module. Staff can only use the capabilities you enable here —
        these are the <em>maximum</em> permissions any user on this tenant can have.
      </Typography>

      {MODULE_DEFS.filter((def) => enabledModules.has(def.id) && def.id !== 'ai').map((def) => (
        <Box key={def.id} sx={{ mb: 3 }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <Typography fontSize={16}>{def.emoji}</Typography>
            <Typography variant="subtitle2" fontWeight={700} color="primary.main">{def.label}</Typography>
          </Stack>
          <Card variant="outlined" sx={{ p: 2 }}>
            {def.features.filter((f) => f.actions.length > 0).map((feature, idx, arr) => (
              <Box key={feature.label}>
                <CapabilityRow
                  feature={feature}
                  enabledCaps={enabledCaps}
                  registryIds={registryIds}
                  onToggle={toggleCap}
                />
                {idx < arr.length - 1 && <Divider sx={{ my: 0.5 }} />}
              </Box>
            ))}
          </Card>
        </Box>
      ))}

      {/* AI module notice */}
      {enabledModules.has('ai') && (
        <Box sx={{ mb: 3 }}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <Typography fontSize={16}>🤖</Typography>
            <Typography variant="subtitle2" fontWeight={700} color="primary.main">AI Features</Typography>
          </Stack>
          <Alert severity="info" icon={false} sx={{ border: '1px solid #bfdbfe' }}>
            AI capabilities (intent detection, recommendations, insights) are managed by the plan and enabled automatically
            when the AI module is turned on. Contact Super Admin to adjust AI feature access.
          </Alert>
        </Box>
      )}

      {Array.from(enabledModules).length === 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          No modules enabled. Toggle at least one module above to configure capabilities.
        </Alert>
      )}

      {/* ── Actions ──────────────────────────────────────────────────── */}
      <Divider sx={{ my: 2 }} />
      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
        <Button size="small" variant="outlined" onClick={applyDefaults}>
          Select Defaults
        </Button>
        <Button size="small" variant="outlined" color="warning" onClick={clearAll}>
          Clear All
        </Button>
        <Box flex={1} />
        <Button
          variant="contained"
          disabled={saving}
          onClick={handleSave}
          startIcon={<CheckCircleIcon />}
        >
          Save Modules &amp; Capabilities
        </Button>
      </Stack>

      {saveMsg?.ok && (
        <Typography variant="body2" color="success.main" sx={{ mt: 1 }}>{saveMsg.ok}</Typography>
      )}
      {saveMsg?.error && (
        <Typography variant="body2" color="error" sx={{ mt: 1 }}>{saveMsg.error}</Typography>
      )}
    </Box>
  )
}
