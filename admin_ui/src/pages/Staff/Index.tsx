import { useEffect, useMemo, useState } from 'react'
import { useNavigate, Link as RouterLink } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle,
  Divider, FormControlLabel, Checkbox, IconButton, MenuItem, Pagination, Stack, Table, TableBody,
  TableCell, TableHead, TableRow, TextField, ToggleButton, ToggleButtonGroup, Tooltip, Typography
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import DownloadIcon from '@mui/icons-material/Download'
import LockIcon from '@mui/icons-material/Lock'
import PersonAddIcon from '@mui/icons-material/PersonAdd'
import SettingsIcon from '@mui/icons-material/Settings'
import BlockIcon from '@mui/icons-material/Block'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import { deleteStaff, listStaff, importStaffCsv, updateStaff, StaffImportResult, Staff } from '@api/staff'
import { listUsers, createUser, updateUser, setPassword, getUser, getPermissionProfiles, type User, type PermissionProfile } from '@api/users'
import PortalAccessDialog from './PortalAccessDialog'
import { getTenantSettings } from '@api/tenants'
import { listRegistry, type RegistryItem } from '@api/modules'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useAlert } from '@contexts/AlertContext'
import { formatEntityPhoneForDisplay } from '../../utils/phone'

/** Normalize API error detail (string, array of { msg }, or object) to a single string for display. */
function apiErrorToString(detail: unknown): string {
  if (detail == null) return ''
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0]
    return typeof first === 'object' && first !== null && 'msg' in first ? String((first as { msg?: string }).msg) : String(detail)
  }
  if (typeof detail === 'object' && 'msg' in detail) return String((detail as { msg: string }).msg)
  return String(detail)
}

const MODULE_ORDER = ['core', 'salon', 'clinic', 'store', 'ai', 'other']
const MODULE_DISPLAY: Record<string, { label: string; borderColor: string; bgHint: string }> = {
  core: { label: 'Core', borderColor: '#2563eb', bgHint: 'rgba(37, 99, 235, 0.08)' },
  salon: { label: 'Salon', borderColor: '#0d9488', bgHint: 'rgba(13, 148, 136, 0.08)' },
  clinic: { label: 'Clinic', borderColor: '#0891b2', bgHint: 'rgba(8, 145, 178, 0.08)' },
  store: { label: 'Store', borderColor: '#d97706', bgHint: 'rgba(217, 119, 6, 0.08)' },
  ai: { label: 'AI', borderColor: '#7c3aed', bgHint: 'rgba(124, 58, 237, 0.08)' },
  other: { label: 'Other', borderColor: '#64748b', bgHint: 'rgba(100, 116, 139, 0.08)' },
}

export default function StaffIndex() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { effectiveTenant: tenant, role } = useEffectiveTenant()
  const { showConfirm, showAlert } = useAlert()

  const canCreateStaff = role === 'tenant_admin' || role === 'super_admin'

  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [active, setActive] = useState<'all' | 'true' | 'false'>('all')
  const [page, setPage] = useState(1)
  const [size, setSize] = useState(10)

  // Portal access dialogs (email from staff; password set by tenant via Change password)
  const [createLoginStaff, setCreateLoginStaff] = useState<Staff | null>(null)
  const [createLoginCaps, setCreateLoginCaps] = useState<string[]>([])
  const [createLoginSaving, setCreateLoginSaving] = useState(false)
  const [createLoginError, setCreateLoginError] = useState<string | null>(null)

  const [passwordUser, setPasswordUser] = useState<User | null>(null)
  const [newPassword, setNewPassword] = useState('')
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('')
  const [passwordSaving, setPasswordSaving] = useState(false)
  const [passwordError, setPasswordError] = useState<string | null>(null)

  const [editModulesUser, setEditModulesUser] = useState<User | null>(null)
  const [editModulesCaps, setEditModulesCaps] = useState<string[]>([])
  const [editModulesSaving, setEditModulesSaving] = useState(false)
  const [editModulesError, setEditModulesError] = useState<string | null>(null)

  const [revokeUser, setRevokeUser] = useState<User | null>(null)
  const [revokeSaving, setRevokeSaving] = useState(false)

  // CSV import state
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<StaffImportResult | null>(null)
  const [importDialogOpen, setImportDialogOpen] = useState(false)

  const [searchInput, setSearchInput] = useState('')
  useEffect(() => {
    const h = setTimeout(() => setSearch(searchInput), 300)
    return () => clearTimeout(h)
  }, [searchInput])

  const queryParams = useMemo(
    () => ({
      search: search || undefined,
      role: roleFilter || undefined,
      active: active === 'all' ? undefined : active === 'true',
      page,
      size,
    }),
    [search, roleFilter, active, page, size]
  )

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['staff', tenant, queryParams],
    queryFn: async () => {
      if (!tenant) return { items: [], total: 0, page: 1, size: 10 }
      return await listStaff(tenant, queryParams as any)
    },
    enabled: !!tenant,
    staleTime: 5_000,
  })

  const { data: portalUsersData } = useQuery({
    queryKey: ['users', tenant, 'staff'],
    queryFn: async () => {
      if (!tenant) return { items: [] as User[] }
      return await listUsers({ tenant, role: 'staff', page: 1, size: 200 })
    },
    enabled: !!tenant && canCreateStaff,
    staleTime: 10_000,
  })

  const portalUsersByEmail = useMemo(() => {
    const map: Record<string, User> = {}
    for (const u of portalUsersData?.items ?? []) {
      const email = (u.email || '').trim().toLowerCase()
      if (email) map[email] = u
    }
    return map
  }, [portalUsersData])

  const { data: tenantSettings } = useQuery({
    queryKey: ['tenantSettings', tenant],
    queryFn: () => getTenantSettings(tenant!),
    enabled: !!tenant && (!!createLoginStaff || !!editModulesUser),
  })

  const { data: registryData } = useQuery({
    queryKey: ['registry'],
    queryFn: async () => (await listRegistry()).items,
    enabled: !!createLoginStaff || !!editModulesUser,
  })

  const { data: profilesData } = useQuery({
    queryKey: ['permissionProfiles', tenant],
    queryFn: async () => {
      if (!tenant) return { profiles: [] as PermissionProfile[], assignable_caps: [] }
      return await getPermissionProfiles(tenant)
    },
    enabled: !!tenant && (!!createLoginStaff || !!editModulesUser),
  })
  const profiles = profilesData?.profiles ?? []

  const tenantCapsSet = useMemo(() => {
    const caps = (tenantSettings?.capabilities ?? []).map((c: string) => c.toLowerCase())
    const set = new Set(caps)
    const legacy: Record<string, string[]> = {
      'salon.appointments': ['salon.appointments.view', 'salon.appointments.edit', 'salon.appointments.delete'],
      'salon.services': ['salon.services.view', 'salon.services.edit'],
      'core.dashboard': ['core.dashboard.view'],
      'core.settings': ['core.settings.view', 'core.settings.edit', 'core.settings.edit_sensitive'],
      'core.customers': ['core.customers.view', 'core.customers.edit', 'core.customers.edit_sensitive'],
      'core.reports': ['core.reports.view'],
      'store.orders': ['store.orders.view', 'store.orders.edit', 'store.orders.edit_sensitive', 'store.orders.delete'],
    }
    for (const [leg, list] of Object.entries(legacy)) {
      if (set.has(leg)) list.forEach(c => set.add(c))
    }
    return set
  }, [tenantSettings])

  const allowedCapsForTenant = useMemo(() => Array.from(tenantCapsSet), [tenantCapsSet])

  const capOptions = useMemo(() => {
    const reg = (registryData ?? []) as RegistryItem[]
    return reg
      .filter(r => r.type === 'capability' && allowedCapsForTenant.includes((r.id || '').toLowerCase()))
      .map(r => ({ id: r.id!.toLowerCase(), label: r.label || r.id, module: ((r as any).module || (r.id || '').split('.')[0] || 'other').toLowerCase() }))
      .sort((a, b) => a.label.localeCompare(b.label))
  }, [registryData, allowedCapsForTenant])

  const capsByModule = useMemo(() => {
    const byModule: Record<string, { id: string; label: string }[]> = {}
    for (const c of capOptions) {
      const mod = MODULE_ORDER.includes(c.module) ? c.module : 'other'
      if (!byModule[mod]) byModule[mod] = []
      byModule[mod].push({ id: c.id, label: c.label })
    }
    return MODULE_ORDER.filter(m => byModule[m]?.length).map(m => ({
      moduleId: m,
      label: MODULE_DISPLAY[m]?.label ?? m,
      borderColor: MODULE_DISPLAY[m]?.borderColor ?? MODULE_DISPLAY.other.borderColor,
      bgHint: MODULE_DISPLAY[m]?.bgHint ?? MODULE_DISPLAY.other.bgHint,
      caps: byModule[m] || [],
    }))
  }, [capOptions])

  const del = useMutation({
    mutationFn: async (id: string) => {
      if (!tenant) return
      await deleteStaff(tenant, id)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['staff'] }),
  })

  const rolesFromData = useMemo(() => {
    const set = new Set<string>()
    ;(data?.items ?? []).forEach(s => {
      if (s.role) set.add(s.role)
    })
    return Array.from(set).sort()
  }, [data])

  /** Detect profile name from a caps array (used to auto-set staff record role). */
  function detectPortalProfile(userCaps: string[]): string {
    const tenantSet = tenantCapsSet
    const effectiveCaps = new Set(userCaps.map(c => c.toLowerCase()).filter(c => tenantSet.has(c)))
    const PROFILE_ORDER = ['manager', 'editor', 'viewer']
    for (const pid of PROFILE_ORDER) {
      const p = profiles.find(x => x.id === pid)
      if (!p) continue
      const pCaps = new Set((p.caps || []).map(c => c.toLowerCase()).filter(c => tenantSet.has(c)))
      if (pCaps.size > 0 && pCaps.size === effectiveCaps.size && [...pCaps].every(c => effectiveCaps.has(c))) return pid
    }
    return effectiveCaps.size === 0 ? '' : 'custom'
  }

  /** After saving portal caps, update the staff record's role to match the profile. */
  async function syncStaffRoleFromCaps(staffRecord: Staff, newCaps: string[]) {
    if (!tenant || !staffRecord.id) return
    const profileName = detectPortalProfile(newCaps)
    const newRole = profileName === 'custom' ? 'custom' : profileName  // '' keeps role unchanged
    if (newRole && newRole !== (staffRecord.role || '').toLowerCase()) {
      try {
        await updateStaff(tenant, staffRecord.id, { role: newRole })
        await qc.refetchQueries({ queryKey: ['staff', tenant] })
      } catch { /* non-critical */ }
    }
  }

  function openCreateLogin(s: Staff) {
    setCreateLoginStaff(s)
    setCreateLoginError(null)
    qc.invalidateQueries({ queryKey: ['users', tenant, 'staff'] })
    const email = (s.email || '').trim().toLowerCase()
    const existing = email ? portalUsersByEmail[email] : null
    setCreateLoginCaps((existing?.caps ?? []).map(c => String(c).toLowerCase()))
  }

  function randomTemporaryPassword(length = 16): string {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'
    let s = ''
    if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
      const arr = new Uint8Array(length)
      crypto.getRandomValues(arr)
      for (let i = 0; i < length; i++) s += chars[arr[i] % chars.length]
    } else {
      for (let i = 0; i < length; i++) s += chars[Math.floor(Math.random() * chars.length)]
    }
    return s
  }

  async function submitCreateLogin() {
    if (!tenant || !createLoginStaff) return
    setCreateLoginError(null)
    const email = (createLoginStaff.email || '').trim().toLowerCase()
    if (!email) {
      setCreateLoginError('This staff member has no email. Add an email to their record first.')
      return
    }
    const existingPortalUser = portalUsersByEmail[email]
    setCreateLoginSaving(true)
    try {
      if (existingPortalUser?.id) {
        await updateUser(existingPortalUser.id, { caps: createLoginCaps })
        await syncStaffRoleFromCaps(createLoginStaff, createLoginCaps)
        showAlert('Portal access updated.', 'success')
        setCreateLoginStaff(null)
        await qc.refetchQueries({ queryKey: ['users', tenant, 'staff'] })
      } else {
        try {
          await createUser({
            email,
            password: randomTemporaryPassword(16),
            role: 'staff',
            tenant,
            display_name: createLoginStaff.name || email,
            caps: createLoginCaps,
          })
          await syncStaffRoleFromCaps(createLoginStaff, createLoginCaps)
          showAlert('Portal access granted. Set their password via Change password or Edit Staff.', 'success')
          setCreateLoginStaff(null)
          await qc.refetchQueries({ queryKey: ['users', tenant, 'staff'] })
        } catch (createErr: any) {
          const msg = apiErrorToString(createErr?.response?.data?.detail) || ''
          if (msg.toLowerCase().includes('already exists') || msg.toLowerCase().includes('unique')) {
            const fresh = await listUsers({ tenant, role: 'staff', page: 1, size: 200 })
            const byEmail = (fresh?.items ?? []).find(u => (u.email || '').trim().toLowerCase() === email)
            if (byEmail?.id) {
              await updateUser(byEmail.id, { caps: createLoginCaps })
              await syncStaffRoleFromCaps(createLoginStaff, createLoginCaps)
              showAlert('Portal access updated.', 'success')
              setCreateLoginStaff(null)
              await qc.refetchQueries({ queryKey: ['users', tenant, 'staff'] })
            } else {
              setCreateLoginError(msg || 'Failed to create portal access')
            }
          } else {
            setCreateLoginError(msg || 'Failed to create portal access')
          }
        }
      }
    } catch (e: any) {
      setCreateLoginError(apiErrorToString(e?.response?.data?.detail) || 'Failed to create portal access')
    } finally {
      setCreateLoginSaving(false)
    }
  }

  function openChangePassword(u: User) {
    setPasswordUser(u)
    setNewPassword('')
    setNewPasswordConfirm('')
    setPasswordError(null)
  }

  async function submitChangePassword() {
    if (!passwordUser?.id) return
    setPasswordError(null)
    if (newPassword.length < 8) {
      setPasswordError('Password must be at least 8 characters')
      return
    }
    if (newPassword !== newPasswordConfirm) {
      setPasswordError('Passwords do not match')
      return
    }
    setPasswordSaving(true)
    try {
      await setPassword(passwordUser.id, newPassword)
      showAlert('Password updated', 'success')
      setPasswordUser(null)
    } catch (e: any) {
      setPasswordError(apiErrorToString(e?.response?.data?.detail) || 'Failed to update password')
    } finally {
      setPasswordSaving(false)
    }
  }

  async function openEditModules(u: User) {
    setEditModulesError(null)
    setEditModulesUser(u)
    try {
      const full = await getUser(u.id!)
      setEditModulesUser(full)
      setEditModulesCaps((full.caps ?? []).map(c => String(c).toLowerCase()))
    } catch {
      setEditModulesCaps((u.caps ?? []).map(c => String(c).toLowerCase()))
    }
  }

  async function submitEditModules() {
    if (!editModulesUser?.id) return
    setEditModulesError(null)
    setEditModulesSaving(true)
    try {
      await updateUser(editModulesUser.id, { caps: editModulesCaps })
      // Find matching staff record by email and sync role
      const staffEmail = (editModulesUser.email || '').trim().toLowerCase()
      const matchingStaff = (data?.items ?? []).find(s => (s.email || '').trim().toLowerCase() === staffEmail)
      if (matchingStaff) await syncStaffRoleFromCaps(matchingStaff, editModulesCaps)
      showAlert('Portal access updated.', 'success')
      setEditModulesUser(null)
      await qc.refetchQueries({ queryKey: ['users', tenant, 'staff'] })
    } catch (e: any) {
      setEditModulesError(apiErrorToString(e?.response?.data?.detail) || 'Failed to update modules')
    } finally {
      setEditModulesSaving(false)
    }
  }

  async function confirmRevokePortalAccess() {
    if (!revokeUser?.id) return
    setRevokeSaving(true)
    try {
      await updateUser(revokeUser.id, { status: 'disabled' })
      showAlert('Portal access revoked. Staff can no longer sign in.', 'success')
      setRevokeUser(null)
      await qc.refetchQueries({ queryKey: ['users', tenant, 'staff'] })
    } catch (e: any) {
      showAlert(apiErrorToString(e?.response?.data?.detail) || 'Failed to revoke portal access', 'error')
    } finally {
      setRevokeSaving(false)
    }
  }

  async function handleImportCsv(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || !tenant) return
    setImporting(true)
    setImportResult(null)
    try {
      const result = await importStaffCsv(tenant, file)
      setImportResult(result)
      setImportDialogOpen(true)
      qc.invalidateQueries({ queryKey: ['staff'] })
    } catch (err: any) {
      setImportResult({ inserted: 0, updated: 0, failed: 0, errors: [{ row: 0, name: '', error: err?.response?.data?.detail || 'Upload failed' }] })
      setImportDialogOpen(true)
    } finally {
      setImporting(false)
    }
  }

  function downloadTemplate() {
    const headers = 'name,role,phone,email,skills,active'
    const example1 = 'Ayesha Khan,stylist,+919876543210,ayesha@salon.com,"haircut,coloring",true'
    const example2 = 'Raj Kumar,therapist,9988776655,raj@salon.com,massage,true'
    const example3 = 'Meena Nair,receptionist,,meena@salon.com,,true'
    const blob = new Blob([[headers, example1, example2, example3].join('\n') + '\n'], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'staff_import_template.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  async function restorePortalAccess(u: User) {
    if (!u?.id) return
    try {
      await updateUser(u.id, { status: 'active' })
      showAlert('Portal access restored.', 'success')
      await qc.refetchQueries({ queryKey: ['users', tenant, 'staff'] })
    } catch (e: any) {
      showAlert(apiErrorToString(e?.response?.data?.detail) || 'Failed to restore portal access', 'error')
    }
  }

  return (
    <Box>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
        <Typography variant="h5">Staff</Typography>
        {canCreateStaff && (
          <Stack direction="row" spacing={1}>
            <Tooltip title="Download CSV template">
              <Button variant="outlined" size="small" startIcon={<DownloadIcon />} onClick={downloadTemplate}>
                Template
              </Button>
            </Tooltip>
            <Tooltip title="Import staff from CSV file">
              <Button
                component="label"
                variant="outlined"
                size="small"
                startIcon={importing ? <CircularProgress size={14} /> : <UploadFileIcon />}
                disabled={!tenant || importing}
              >
                {importing ? 'Importing…' : 'Import CSV'}
                <input type="file" accept=".csv,text/csv" hidden onChange={handleImportCsv} />
              </Button>
            </Tooltip>
            <Button variant="contained" startIcon={<AddIcon />} component={RouterLink} to="/staff/new">
              New Staff
            </Button>
          </Stack>
        )}
      </Stack>
      {canCreateStaff && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          To give a staff member portal access: click <strong>Give portal access</strong> in the table row. Set their sign-in password via <strong>Change password</strong>.
        </Typography>
      )}
      <Card>
        <CardContent>
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={2}
            alignItems={{ xs: 'stretch', sm: 'center' }}
            sx={{ mb: 2 }}
          >
            <TextField
              label="Search"
              placeholder="name, phone, email, role"
              value={searchInput}
              onChange={e => setSearchInput(e.target.value)}
              fullWidth
            />
            <TextField
              select
              label="Role"
              value={roleFilter}
              onChange={e => setRoleFilter(e.target.value)}
              sx={{ minWidth: 180 }}
            >
              <MenuItem value="">All roles</MenuItem>
              {rolesFromData.map(r => (
                <MenuItem key={r} value={r}>
                  {r}
                </MenuItem>
              ))}
            </TextField>
            <ToggleButtonGroup exclusive value={active} onChange={(_, v) => v && setActive(v)}>
              <ToggleButton value="all">All</ToggleButton>
              <ToggleButton value="true">Active</ToggleButton>
              <ToggleButton value="false">Inactive</ToggleButton>
            </ToggleButtonGroup>
            <TextField
              type="number"
              label="Page size"
              value={size}
              onChange={e => {
                const v = Math.max(1, Math.min(200, Number(e.target.value) || 10))
                setSize(v)
                setPage(1)
              }}
              sx={{ width: 120 }}
            />
          </Stack>
          <Divider sx={{ mb: 2 }} />
          {isLoading && <Typography>Loading...</Typography>}
          {isError && (
            <Typography color="error">
              {apiErrorToString((error as any)?.response?.data?.detail) || (error as any)?.message || 'Failed to load'}
            </Typography>
          )}
          {!isLoading && !isError && (
            <>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Portal Role</TableCell>
                    <TableCell>Position</TableCell>
                    <TableCell>Phone</TableCell>
                    <TableCell>Email</TableCell>
                    <TableCell>Skills</TableCell>
                    <TableCell>Active</TableCell>
                    <TableCell>Portal access</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(data?.items ?? []).map((s: Staff) => {
                    const portalUser = s.email ? portalUsersByEmail[(s.email || '').trim().toLowerCase()] : null
                    return (
                      <TableRow key={s.id} hover>
                        <TableCell>{s.name}</TableCell>
                        <TableCell>
                          {s.role ? (
                            <Chip
                              label={s.role.charAt(0).toUpperCase() + s.role.slice(1)}
                              size="small"
                              color={
                                s.role === 'manager' ? 'success' :
                                s.role === 'editor'  ? 'primary' :
                                s.role === 'viewer'  ? 'info' :
                                s.role === 'custom'  ? 'warning' : 'default'
                              }
                              variant={['manager','editor','viewer','custom'].includes(s.role) ? 'filled' : 'outlined'}
                            />
                          ) : <Typography variant="caption" color="text.disabled">—</Typography>}
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption" color="text.secondary">{(s as any).position || '—'}</Typography>
                        </TableCell>
                        <TableCell>{formatEntityPhoneForDisplay(s) || '-'}</TableCell>
                        <TableCell>{s.email || '-'}</TableCell>
                        <TableCell>
                          {(s.skills ?? []).length
                            ? (s.skills ?? []).map(sk => (
                                <Chip key={sk} size="small" label={sk} sx={{ mr: 0.5 }} />
                              ))
                            : '-'}
                        </TableCell>
                        <TableCell>{s.active ? 'Yes' : 'No'}</TableCell>
                        <TableCell>
                          {portalUser ? (
                            (portalUser.status || 'active') === 'disabled' ? (
                              <Stack direction="row" spacing={0.5} alignItems="center">
                                <Chip size="small" color="default" label="Revoked" variant="outlined" />
                                {canCreateStaff && (
                                  <Button
                                    size="small"
                                    variant="outlined"
                                    startIcon={<PersonAddIcon />}
                                    onClick={() => restorePortalAccess(portalUser)}
                                  >
                                    Restore access
                                  </Button>
                                )}
                              </Stack>
                            ) : (
                              <Stack direction="row" spacing={0.5} alignItems="center">
                                <Chip size="small" color="success" label="Yes" />
                                {canCreateStaff && (
                                  <>
                                    <Tooltip title="Change password">
                                      <IconButton size="small" onClick={() => openChangePassword(portalUser)}>
                                        <LockIcon fontSize="small" />
                                      </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Edit modules">
                                      <IconButton size="small" onClick={() => openEditModules(portalUser)}>
                                        <SettingsIcon fontSize="small" />
                                      </IconButton>
                                    </Tooltip>
                                    <Tooltip title="Revoke portal access">
                                      <IconButton size="small" color="error" onClick={() => setRevokeUser(portalUser)}>
                                        <BlockIcon fontSize="small" />
                                      </IconButton>
                                    </Tooltip>
                                  </>
                                )}
                              </Stack>
                            )
                          ) : (
                            <Stack direction="row" spacing={0.5} alignItems="center">
                              <Chip size="small" label="No" variant="outlined" />
                              {canCreateStaff && (
                                <Button
                                  size="small"
                                  variant="outlined"
                                  color="primary"
                                  startIcon={<PersonAddIcon />}
                                  onClick={() => openCreateLogin(s)}
                                >
                                  Give portal access
                                </Button>
                              )}
                            </Stack>
                          )}
                        </TableCell>
                        <TableCell align="right">
                          <Tooltip title="Edit">
                            <span>
                              <IconButton onClick={() => navigate(`/staff/${s.id}`)} size="small">
                                <EditIcon fontSize="small" />
                              </IconButton>
                            </span>
                          </Tooltip>
                          {canCreateStaff && (
                            <Tooltip title="Delete">
                              <span>
                                <IconButton
                                  color="error"
                                  size="small"
                                  onClick={async () => {
                                    if (del.isPending) return
                                    const ok = await showConfirm({
                                      title: 'Delete staff',
                                      message: `Delete ${s.name}?`,
                                    })
                                    if (ok) {
                                      try {
                                        await del.mutateAsync(s.id)
                                      } catch {
                                        /* handled by query error */
                                      }
                                    }
                                  }}
                                >
                                  <DeleteIcon fontSize="small" />
                                </IconButton>
                              </span>
                            </Tooltip>
                          )}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                  {data && data.items.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={9}>
                        <Typography>No staff found</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
              <Stack direction="row" justifyContent="flex-end" sx={{ mt: 2 }}>
                <Pagination
                  page={page}
                  onChange={(_, p) => setPage(p)}
                  count={Math.max(1, Math.ceil((data?.total ?? 0) / size))}
                />
              </Stack>
            </>
          )}
        </CardContent>
      </Card>

      {/* Create portal login dialog */}
      <Dialog open={!!createLoginStaff} onClose={() => setCreateLoginStaff(null)} maxWidth="md" fullWidth>
        <DialogTitle>
          Give portal access — {createLoginStaff?.name}
        </DialogTitle>
        <DialogContent dividers>
          {createLoginStaff && (
            <Stack spacing={2} sx={{ mt: 1 }}>
              {/* Staff info */}
              <Stack direction="row" spacing={1} alignItems="center">
                <Typography variant="body2" color="text.secondary">Login email:</Typography>
                <Typography variant="body2" fontWeight={600}>{createLoginStaff.email || '—'}</Typography>
                {createLoginStaff.role && <Chip label={createLoginStaff.role} size="small" variant="outlined" />}
              </Stack>
              {!createLoginStaff.email?.trim() && (
                <Typography variant="body2" color="error">
                  No email on this staff record — add an email first.
                </Typography>
              )}
              {/* Visual access editor */}
              <PortalAccessDialog
                caps={createLoginCaps}
                tenantCaps={tenantCapsSet}
                profiles={profiles}
                onChange={setCreateLoginCaps}
                error={createLoginError}
              />
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateLoginStaff(null)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={submitCreateLogin}
            disabled={createLoginSaving || !createLoginStaff?.email?.trim()}
          >
            {createLoginSaving
              ? 'Saving...'
              : createLoginStaff?.email && portalUsersByEmail[(createLoginStaff.email || '').trim().toLowerCase()]
                ? 'Update access'
                : 'Grant access'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Change password dialog */}
      <Dialog open={!!passwordUser} onClose={() => setPasswordUser(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Change staff password</DialogTitle>
        <DialogContent dividers>
          {passwordUser && (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <Typography variant="body2" color="text.secondary">Only tenant admin can change staff passwords.</Typography>
              <Typography variant="body2">User: {passwordUser.email}</Typography>
              <TextField
                label="New password"
                type="password"
                value={newPassword}
                onChange={e => setNewPassword(e.target.value)}
                fullWidth
                helperText="Min 8 characters"
              />
              <TextField
                label="Confirm password"
                type="password"
                value={newPasswordConfirm}
                onChange={e => setNewPasswordConfirm(e.target.value)}
                fullWidth
              />
              {passwordError && (
                <Typography color="error" variant="body2">
                  {passwordError}
                </Typography>
              )}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPasswordUser(null)}>Cancel</Button>
          <Button variant="contained" onClick={submitChangePassword} disabled={passwordSaving}>
            {passwordSaving ? 'Updating...' : 'Update password'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit modules dialog */}
      <Dialog open={!!editModulesUser} onClose={() => setEditModulesUser(null)} maxWidth="md" fullWidth>
        <DialogTitle>
          Edit portal access — {editModulesUser?.display_name || editModulesUser?.email}
        </DialogTitle>
        <DialogContent dividers>
          {editModulesUser && (
            <Stack spacing={2} sx={{ mt: 1 }}>
              <Stack direction="row" spacing={1} alignItems="center">
                <Typography variant="body2" color="text.secondary">Login email:</Typography>
                <Typography variant="body2" fontWeight={600}>{editModulesUser.email}</Typography>
              </Stack>
              <PortalAccessDialog
                caps={editModulesCaps}
                tenantCaps={tenantCapsSet}
                profiles={profiles}
                onChange={setEditModulesCaps}
                error={editModulesError}
              />
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditModulesUser(null)}>Cancel</Button>
          <Button variant="contained" onClick={submitEditModules} disabled={editModulesSaving}>
            {editModulesSaving ? 'Saving...' : 'Save access'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Revoke portal access confirmation */}
      <Dialog open={!!revokeUser} onClose={() => !revokeSaving && setRevokeUser(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Revoke portal access</DialogTitle>
        <DialogContent dividers>
          {revokeUser && (
            <Typography variant="body2">
              Revoke portal access for <strong>{revokeUser.email}</strong>? They will no longer be able to sign in. You can restore access later.
            </Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRevokeUser(null)} disabled={revokeSaving}>Cancel</Button>
          <Button variant="contained" color="error" onClick={confirmRevokePortalAccess} disabled={revokeSaving}>
            {revokeSaving ? 'Revoking...' : 'Revoke access'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* CSV Import Result Dialog */}
      <Dialog open={importDialogOpen} onClose={() => setImportDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Import Results</DialogTitle>
        <DialogContent>
          {importResult && (
            <Stack spacing={2}>
              <Stack direction="row" spacing={2} flexWrap="wrap">
                <Chip label={`✅ Created: ${importResult.inserted}`} color="success" variant="outlined" />
                <Chip label={`🔄 Updated: ${importResult.updated}`} color="info" variant="outlined" />
                {importResult.failed > 0 && (
                  <Chip label={`❌ Failed: ${importResult.failed}`} color="error" variant="outlined" />
                )}
              </Stack>
              {importResult.errors.length > 0 && (
                <>
                  <Typography variant="subtitle2" color="error">Errors (first 20):</Typography>
                  <Box sx={{ maxHeight: 300, overflowY: 'auto', border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Row</TableCell>
                          <TableCell>Name</TableCell>
                          <TableCell>Error</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {importResult.errors.map((e, i) => (
                          <TableRow key={i}>
                            <TableCell>{e.row || '—'}</TableCell>
                            <TableCell>{e.name || '—'}</TableCell>
                            <TableCell sx={{ color: 'error.main' }}>{e.error}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Box>
                </>
              )}
              {importResult.failed === 0 && importResult.errors.length === 0 && (
                <Alert severity="success">
                  Import completed! {importResult.inserted} new staff member{importResult.inserted !== 1 ? 's' : ''} created,{' '}
                  {importResult.updated} updated.
                </Alert>
              )}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setImportDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
