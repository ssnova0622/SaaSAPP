/**
 * Access Manager — lets Tenant Admins configure staff portal permissions.
 *
 * Features:
 *  • Lists all staff who have a portal login (role=staff)
 *  • Shows their current permission profile (Viewer / Editor / Manager / Custom)
 *  • Quick-assign a profile (applies predefined cap set intersected with tenant caps)
 *  • Expand to a full per-capability matrix for Custom configuration
 *  • Save changes via PATCH /users/{id}
 */
import {
  Alert, Box, Button, Checkbox, Chip, CircularProgress, Collapse,
  Divider, FormControlLabel, FormGroup, IconButton, Paper, Stack,
  Table, TableBody, TableCell, TableHead, TableRow, ToggleButton,
  ToggleButtonGroup, Tooltip, Typography,
} from '@mui/material'
import CheckCircleIcon from '@mui/icons-material/CheckCircle'
import EditIcon from '@mui/icons-material/Edit'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import LockIcon from '@mui/icons-material/Lock'
import { useEffect, useMemo, useState } from 'react'
import {
  listUsers,
  getPermissionProfiles,
  updateUserCaps,
  type User,
  type PermissionProfile,
  type AssignableCap,
} from '@api/users'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useAuth } from '../../contexts/AuthContext'

// --------------------------------------------------------------------------
// Profile chip colours
// --------------------------------------------------------------------------
const PROFILE_COLOURS: Record<string, 'default' | 'info' | 'primary' | 'warning' | 'success'> = {
  viewer:  'info',
  editor:  'primary',
  manager: 'success',
  custom:  'warning',
}

// --------------------------------------------------------------------------
// Helper: detect profile from user caps
// --------------------------------------------------------------------------
function detectProfile(userCaps: string[], profiles: PermissionProfile[], tenantCaps: string[]): string {
  const tenantSet = new Set(tenantCaps)
  const effectiveCaps = new Set(userCaps.map((c) => c.toLowerCase()).filter((c) => tenantSet.has(c)))
  for (const p of profiles) {
    if (p.id === 'custom') continue
    const profileEffective = new Set(
      (p.caps || []).map((c) => c.toLowerCase()).filter((c) => tenantSet.has(c))
    )
    if (
      profileEffective.size === effectiveCaps.size &&
      [...profileEffective].every((c) => effectiveCaps.has(c))
    ) {
      return p.id
    }
  }
  return 'custom'
}

// --------------------------------------------------------------------------
// Group assignable caps by module for the custom matrix
// --------------------------------------------------------------------------
function groupCaps(caps: AssignableCap[]): Record<string, AssignableCap[]> {
  return caps.reduce<Record<string, AssignableCap[]>>((acc, c) => {
    const g = c.group || c.module || 'Other'
    ;(acc[g] = acc[g] || []).push(c)
    return acc
  }, {})
}

// --------------------------------------------------------------------------
// Per-user row component
// --------------------------------------------------------------------------
interface StaffRowProps {
  staffUser: User
  profiles: PermissionProfile[]
  assignableCaps: AssignableCap[]
  tenantCaps: string[]
  onSaved: (updated: User) => void
}

function StaffRow({ staffUser, profiles, assignableCaps, tenantCaps, onSaved }: StaffRowProps) {
  const initCaps = useMemo(() => (staffUser.caps || []).map((c) => c.toLowerCase()), [staffUser.caps])
  const [selectedCaps, setSelectedCaps] = useState<Set<string>>(new Set(initCaps))
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<{ ok?: string; error?: string } | null>(null)
  const [expanded, setExpanded] = useState(false)

  const currentProfile = detectProfile([...selectedCaps], profiles, tenantCaps)
  const grouped = useMemo(() => groupCaps(assignableCaps), [assignableCaps])

  function applyProfile(profileId: string) {
    const p = profiles.find((x) => x.id === profileId)
    if (!p || profileId === 'custom') return
    setSelectedCaps(new Set((p.caps || []).map((c) => c.toLowerCase())))
  }

  function toggleCap(capId: string) {
    setSelectedCaps((prev) => {
      const next = new Set(prev)
      next.has(capId) ? next.delete(capId) : next.add(capId)
      return next
    })
  }

  async function save() {
    setSaving(true)
    setMsg(null)
    try {
      const updated = await updateUserCaps(staffUser.id!, [...selectedCaps])
      onSaved(updated)
      setMsg({ ok: 'Permissions saved.' })
    } catch {
      setMsg({ error: 'Failed to save. Try again.' })
    } finally {
      setSaving(false)
    }
  }

  const isDirty = useMemo(() => {
    const init = new Set(initCaps)
    if (init.size !== selectedCaps.size) return true
    for (const c of selectedCaps) if (!init.has(c)) return true
    return false
  }, [initCaps, selectedCaps])

  return (
    <>
      <TableRow hover>
        <TableCell>
          <Stack>
            <Typography variant="body2" fontWeight={600}>
              {staffUser.display_name || staffUser.email}
            </Typography>
            <Typography variant="caption" color="text.secondary">{staffUser.email}</Typography>
          </Stack>
        </TableCell>

        <TableCell>
          <ToggleButtonGroup
            value={currentProfile}
            exclusive
            size="small"
            onChange={(_, v) => { if (v) applyProfile(v) }}
          >
            {profiles.filter((p) => p.id !== 'custom').map((p) => (
              <ToggleButton key={p.id} value={p.id} sx={{ textTransform: 'none', px: 1.5 }}>
                <Tooltip title={p.description} arrow>
                  <span>{p.label}</span>
                </Tooltip>
              </ToggleButton>
            ))}
          </ToggleButtonGroup>

          <Chip
            label={currentProfile === 'custom' ? 'Custom' : profiles.find((p) => p.id === currentProfile)?.label || currentProfile}
            color={PROFILE_COLOURS[currentProfile] ?? 'default'}
            size="small"
            sx={{ ml: 1 }}
          />
        </TableCell>

        <TableCell align="right">
          <Stack direction="row" spacing={1} justifyContent="flex-end">
            <Tooltip title={expanded ? 'Collapse custom caps' : 'Edit individual caps'}>
              <IconButton size="small" onClick={() => setExpanded((e) => !e)}>
                <EditIcon fontSize="small" />
                {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
              </IconButton>
            </Tooltip>
            <Button
              size="small"
              variant="contained"
              disabled={!isDirty || saving}
              onClick={save}
              startIcon={saving ? <CircularProgress size={14} /> : <CheckCircleIcon />}
            >
              Save
            </Button>
          </Stack>
          {msg?.ok && <Typography variant="caption" color="success.main">{msg.ok}</Typography>}
          {msg?.error && <Typography variant="caption" color="error">{msg.error}</Typography>}
        </TableCell>
      </TableRow>

      {/* Expanded custom capability matrix */}
      <TableRow>
        <TableCell colSpan={3} sx={{ p: 0 }}>
          <Collapse in={expanded} unmountOnExit>
            <Box sx={{ px: 3, py: 2, background: '#f8fafc' }}>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                Fine-grained permissions — selecting these switches the profile to <strong>Custom</strong>.
              </Typography>
              {Object.entries(grouped).map(([group, caps]) => (
                <Box key={group} sx={{ mb: 2 }}>
                  <Typography variant="overline" color="text.secondary">{group}</Typography>
                  <FormGroup row>
                    {caps.map((cap) => (
                      <Tooltip key={cap.id} title={cap.description} arrow>
                        <FormControlLabel
                          control={
                            <Checkbox
                              size="small"
                              checked={selectedCaps.has(cap.id)}
                              onChange={() => toggleCap(cap.id)}
                            />
                          }
                          label={
                            <Typography variant="caption">{cap.label}</Typography>
                          }
                          sx={{ minWidth: 220 }}
                        />
                      </Tooltip>
                    ))}
                  </FormGroup>
                  <Divider sx={{ mt: 1 }} />
                </Box>
              ))}
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  )
}

// --------------------------------------------------------------------------
// Main page
// --------------------------------------------------------------------------
export default function AccessManager() {
  const { effectiveTenant } = useEffectiveTenant()
  const { isTenantAdmin, isSuperAdmin } = useAuth()
  const tenant = effectiveTenant || ''

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [staffUsers, setStaffUsers] = useState<User[]>([])
  const [profiles, setProfiles] = useState<PermissionProfile[]>([])
  const [assignableCaps, setAssignableCaps] = useState<AssignableCap[]>([])
  const [tenantCaps, setTenantCaps] = useState<string[]>([])

  useEffect(() => {
    if (!tenant) return
    setLoading(true)
    setError(null)

    Promise.all([
      listUsers({ tenant, role: 'staff', size: 100 }),
      getPermissionProfiles(tenant),
    ])
      .then(([users, profilesRes]) => {
        setStaffUsers(users.items)
        setProfiles(profilesRes.profiles)
        setAssignableCaps(profilesRes.assignable_caps)
        // Collect all caps that appear in any profile to reconstruct tenant caps
        const allCaps = profilesRes.assignable_caps.map((c) => c.id)
        setTenantCaps(allCaps)
      })
      .catch((e) => setError(String(e?.response?.data?.detail || e?.message || 'Failed to load')))
      .finally(() => setLoading(false))
  }, [tenant])

  const handleSaved = (updated: User) => {
    setStaffUsers((prev) => prev.map((u) => (u.id === updated.id ? { ...u, caps: updated.caps } : u)))
  }

  if (!isTenantAdmin && !isSuperAdmin) {
    return (
      <Alert severity="error" sx={{ m: 3 }}>
        Access denied — Tenant Admin role required.
      </Alert>
    )
  }

  return (
    <Box sx={{ p: { xs: 2, md: 3 } }}>
      <Stack direction="row" alignItems="center" spacing={1} mb={2}>
        <LockIcon color="primary" />
        <Typography variant="h5" fontWeight={700}>Access Manager</Typography>
      </Stack>
      <Typography variant="body2" color="text.secondary" mb={3}>
        Control what each staff member can see and do in the portal.
        Super Admin always has full access. Tenant Admin has full access to all enabled modules.
        Staff access is limited to the permissions you configure here.
      </Typography>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {loading ? (
        <Box display="flex" justifyContent="center" py={6}>
          <CircularProgress />
        </Box>
      ) : staffUsers.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary">
            No staff portal accounts found. Create portal access from the <strong>Staff</strong> page.
          </Typography>
        </Paper>
      ) : (
        <Paper elevation={0} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow sx={{ background: '#f1f5f9' }}>
                <TableCell><Typography variant="caption" fontWeight={700}>Staff Member</Typography></TableCell>
                <TableCell><Typography variant="caption" fontWeight={700}>Permission Profile</Typography></TableCell>
                <TableCell align="right"><Typography variant="caption" fontWeight={700}>Actions</Typography></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {staffUsers.map((u) => (
                <StaffRow
                  key={u.id}
                  staffUser={u}
                  profiles={profiles}
                  assignableCaps={assignableCaps}
                  tenantCaps={tenantCaps}
                  onSaved={handleSaved}
                />
              ))}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Box>
  )
}
