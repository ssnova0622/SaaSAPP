import { useState, useEffect } from 'react'
import { Box, Button, Card, CardContent, Grid, TextField, Typography, Alert, MenuItem } from '@mui/material'
import { createTenant, listPlans, clearTenantSettingsCache, type PlanInfo } from '@api/tenants'
import { useNavigate, Link as RouterLink } from 'react-router-dom'

export default function TenantNew() {
  const [tenant, setTenant] = useState('')
  const [category, setCategory] = useState('salon')
  const [plan, setPlan] = useState('pro')
  const [plans, setPlans] = useState<PlanInfo[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    listPlans().then(setPlans).catch(() => setPlans([]))
  }, [])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    const t = tenant.trim()
    if (!t) { setError('Tenant id is required'); return }
    setSubmitting(true)
    try {
      await createTenant({ tenant: t, category: category.trim() || 'salon', plan: plan || 'pro' })
      // Set the new tenant as the effective tenant so the app switches to it
      try {
        localStorage.setItem('selected_tenant', t)
        clearTenantSettingsCache()
        window.dispatchEvent(new CustomEvent<string>('tenant-change', { detail: t }))
      } catch { /* ignore */ }
      // Go to Settings so the tenant can save remaining configuration (owner, timezone, etc.)
      navigate('/settings', { replace: true })
    } catch (e: any) {
      const msg = e?.response?.data?.detail || (e?.message || 'Failed to create tenant')
      setError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Box sx={{ p: 1 }}>
      <Typography variant="h5" sx={{ mb: 2 }}>Create New Tenant</Typography>
      <Grid container spacing={2}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box component="form" onSubmit={onSubmit}>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <TextField
                      label="Tenant ID"
                      value={tenant}
                      onChange={(e) => setTenant(e.target.value)}
                      placeholder="my-salon"
                      fullWidth
                      required
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      label="Category"
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      placeholder="salon | clinic | showroom"
                      fullWidth
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      select
                      fullWidth
                      label="Plan"
                      value={plan}
                      onChange={(e) => setPlan(e.target.value)}
                      helperText="Determines default modules and capabilities (e.g. Basic: no Reports/Store/AI; Pro: + Reports, Store; Enterprise: + AI)."
                    >
                      {plans.length
                        ? plans.map((p) => (
                            <MenuItem key={p.id} value={p.id}>
                              {p.label}
                            </MenuItem>
                          ))
                        : [
                            { id: 'basic', label: 'Basic' },
                            { id: 'pro', label: 'Pro' },
                            { id: 'enterprise', label: 'Enterprise' },
                          ].map((p) => (
                            <MenuItem key={p.id} value={p.id}>
                              {p.label}
                            </MenuItem>
                          ))}
                    </TextField>
                  </Grid>

                  {error && (
                    <Grid item xs={12}>
                      <Alert severity="error">{error}</Alert>
                    </Grid>
                  )}

                  <Grid item xs={12}>
                    <Grid container spacing={2}>
                      <Grid item>
                        <Button type="submit" variant="contained" disabled={submitting}>Create</Button>
                      </Grid>
                      <Grid item>
                        <Button component={RouterLink} to="/settings" variant="text" disabled={submitting}>Cancel</Button>
                      </Grid>
                    </Grid>
                  </Grid>
                </Grid>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
