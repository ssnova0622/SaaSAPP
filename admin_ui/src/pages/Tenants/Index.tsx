import { useEffect, useMemo, useState } from 'react'
import { Box, Button, Card, CardContent, Grid, Typography, Table, TableBody, TableCell, TableHead, TableRow, Stack, Alert, Dialog, DialogTitle, DialogContent, DialogActions, TextField, Chip, MenuItem } from '@mui/material'
import { listTenants, TenantBasic, deleteTenant, createTenant, setTenantActive, listPlans, clearTenantSettingsCache, type PlanInfo } from '@api/tenants'
import { useNavigate, Link as RouterLink, useSearchParams } from 'react-router-dom'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { tokenStore } from '@api/axios'
import { useAlert } from '@contexts/AlertContext'

export default function TenantsIndex() {
  const { showConfirm } = useAlert()
  const [items, setItems] = useState<TenantBasic[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [newTenantId, setNewTenantId] = useState('')
  const [newCategory, setNewCategory] = useState('salon')
  const [adminEmail, setAdminEmail] = useState('')
  const [adminPassword, setAdminPassword] = useState('')
  const [adminDisplayName, setAdminDisplayName] = useState('')
  const [newPlan, setNewPlan] = useState('pro')
  const [plans, setPlans] = useState<PlanInfo[]>([])
  const { effectiveTenant, setEffectiveTenant } = useEffectiveTenant()
  const tenant = effectiveTenant
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [isSuperAdmin, setIsSuperAdmin] = useState(false)

  async function refresh() {
    setLoading(true)
    setError(null)
    try {
      const rows = await listTenants()
      setItems(rows)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load tenants')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { refresh() }, [])

  // Auto-open create dialog if ?new=1 is present
  useEffect(() => {
    const open = searchParams.get('new')
    if (open === '1' && isSuperAdmin) setCreateOpen(true)
  }, [searchParams])

  // Load plans when create dialog opens
  useEffect(() => {
    if (createOpen && isSuperAdmin) {
      listPlans().then(setPlans).catch(() => setPlans([]))
    }
  }, [createOpen, isSuperAdmin])

  // Determine role from JWT
  useEffect(() => {
    try {
      const tok = tokenStore.get()
      if (!tok) { setIsSuperAdmin(false); return }
      const p = JSON.parse(atob(tok.split('.')[1]))
      setIsSuperAdmin(String(p?.role || 'admin').toLowerCase() === 'super_admin')
    } catch { setIsSuperAdmin(false) }
  }, [])

  function openTenant(t: string) {
    setEffectiveTenant(t)
    navigate('/settings')
  }

  async function onDelete(t: string) {
    const ok = await showConfirm({ title: 'Deactivate tenant', message: `Deactivate tenant "${t}"? They will be marked inactive and can be reactivated later.` })
    if (!ok) return
    setError(null); setMessage(null)
    try {
      // Use status toggle to deactivate, prefer soft path
      try {
        await setTenantActive(t, false)
      } catch {
        // Fallback to backend DELETE which is implemented as soft-delete
        await deleteTenant(t)
      }
      await refresh()
      // If deleted tenant was selected, update selection
      if (tenant === t) {
        const next = (items.find(x => x.tenant !== t)?.tenant) || null
        if (next) setEffectiveTenant(next)
        else setEffectiveTenant('')
      }
      setMessage('Tenant deactivated')
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to deactivate tenant')
    }
  }

  async function onCreateSubmit(e: React.FormEvent) {
    e.preventDefault()
    setCreateError(null)
    const t = newTenantId.trim()
    if (!t) { setCreateError('Tenant id is required'); return }
    const email = adminEmail.trim().toLowerCase()
    const pwd = adminPassword
    if (!email) { setCreateError('Admin email is required'); return }
    if (!pwd || pwd.length < 8) { setCreateError('Admin password must be at least 8 characters'); return }
    setCreating(true)
    try {
      await createTenant({
        tenant: t,
        category: newCategory.trim() || 'salon',
        plan: newPlan || 'pro',
        admin_email: email,
        admin_password: pwd,
        admin_display_name: adminDisplayName.trim() || 'Tenant Admin',
      } as any)
      // Set the new tenant as effective so the left panel and app switch to it immediately
      try {
        localStorage.setItem('selected_tenant', t)
        clearTenantSettingsCache()
        window.dispatchEvent(new CustomEvent<string>('tenant-change', { detail: t }))
      } catch { /* ignore */ }
      setEffectiveTenant(t)
      await refresh()
      setCreateOpen(false)
      setNewTenantId('')
      setNewCategory('salon')
      setNewPlan('pro')
      setAdminEmail('')
      setAdminPassword('')
      setAdminDisplayName('')
      setMessage('Tenant created')
      // Let the sidebar and listeners update, then open Settings for remaining configuration
      setTimeout(() => navigate('/settings', { replace: true }), 0)
    } catch (e: any) {
      // Normalize FastAPI validation error (422) that may be an object/array
      const d = e?.response?.data?.detail
      let msg = 'Failed to create tenant'
      if (typeof d === 'string') msg = d
      else if (Array.isArray(d) && d.length) msg = d[0]?.msg || JSON.stringify(d[0])
      else if (d && typeof d === 'object') msg = d.msg || JSON.stringify(d)
      else if (e?.message) msg = e.message
      setCreateError(String(msg))
    } finally {
      setCreating(false)
    }
  }

  async function onActivate(t: string){
    setError(null); setMessage(null)
    try{
      await setTenantActive(t, true)
      await refresh()
      setMessage('Tenant activated')
    }catch(e:any){
      setError(e?.response?.data?.detail || 'Failed to activate tenant')
    }
  }

  return (
    <Box sx={{ p: 1 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
        <Typography variant="h5">Tenants</Typography>
        {isSuperAdmin && (
          <Button variant="contained" onClick={() => { setCreateOpen(true); setSearchParams(prev => { const p = new URLSearchParams(prev); p.set('new','1'); return p as any }) }}>Create Tenant</Button>
        )}
      </Stack>

      <Grid container spacing={2}>
        <Grid item xs={12} md={10}>
          <Card>
            <CardContent>
              {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
              {message && <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>}
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Tenant</TableCell>
                    <TableCell>Category</TableCell>
                    <TableCell>Timezone</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(!loading && items.length === 0) && (
                    <TableRow>
                      <TableCell colSpan={4}>
                        <Typography variant="body2" color="text.secondary">No tenants yet. Create one to get started.</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                  {items.map((row) => (
                    <TableRow key={row.tenant} selected={row.tenant === tenant}>
                      <TableCell>{row.tenant}</TableCell>
                      <TableCell>{row.category || '—'}</TableCell>
                      <TableCell>{row.tz || '—'}</TableCell>
                      <TableCell>
                        {row.active === false ? (
                          <Chip size="small" label="Deactivated" color="warning" />
                        ) : (
                          <Chip size="small" label="Active" color="success" />
                        )}
                      </TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={1} justifyContent="flex-end">
                          <Button size="small" variant="outlined" onClick={() => openTenant(row.tenant)}>Open</Button>
                          {isSuperAdmin && (
                            row.active === false ? (
                              <Button size="small" color="primary" onClick={() => onActivate(row.tenant)}>Activate</Button>
                            ) : (
                              <Button size="small" color="error" onClick={() => onDelete(row.tenant)}>Deactivate</Button>
                            )
                          )}
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Dialog open={createOpen} onClose={() => { setCreateOpen(false); setSearchParams(prev => { const p = new URLSearchParams(prev); p.delete('new'); return p as any }) }} fullWidth maxWidth="sm">
        <DialogTitle>Create New Tenant</DialogTitle>
        <Box component="form" onSubmit={onCreateSubmit}>
          <DialogContent dividers>
            {createError && <Alert severity="error" sx={{ mb: 2 }}>{String(createError)}</Alert>}
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField label="Tenant ID" value={newTenantId} onChange={(e) => setNewTenantId(e.target.value)} placeholder="my-salon" fullWidth required />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField label="Category" value={newCategory} onChange={(e) => setNewCategory(e.target.value)} placeholder="salon | clinic | showroom" fullWidth />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField select label="Plan" value={newPlan} onChange={(e) => setNewPlan(e.target.value)} fullWidth helperText="Choose 14-day Trial (Pro) to auto-deactivate after 14 days.">
                  {(plans.length ? plans : [{ id: 'basic', label: 'Basic' }, { id: 'pro', label: 'Pro' }, { id: 'enterprise', label: 'Enterprise' }, { id: 'trial', label: '14-day Trial (Pro)' }]).map((p) => (
                    <MenuItem key={p.id} value={p.id}>{p.label}</MenuItem>
                  ))}
                </TextField>
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField label="Admin Email" type="email" value={adminEmail} onChange={(e)=>setAdminEmail(e.target.value)} placeholder="owner@example.com" fullWidth required />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField label="Admin Password" type="password" value={adminPassword} onChange={(e)=>setAdminPassword(e.target.value)} placeholder="min 8 characters" fullWidth required />
              </Grid>
              <Grid item xs={12}>
                <TextField label="Admin Display Name (optional)" value={adminDisplayName} onChange={(e)=>setAdminDisplayName(e.target.value)} fullWidth />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => { setCreateOpen(false); setSearchParams(prev => { const p = new URLSearchParams(prev); p.delete('new'); return p as any }) }} disabled={creating}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={creating || !isSuperAdmin}>Create</Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Box>
  )
}
