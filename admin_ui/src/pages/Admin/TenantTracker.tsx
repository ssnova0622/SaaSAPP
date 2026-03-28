import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Chip,
  Button,
  Stack,
  Alert,
} from '@mui/material'
import { getTenantsOverview, type TenantOverviewRow } from '@api/admin'
import { setTenantActive } from '@api/tenants'
import { useAlert } from '@contexts/AlertContext'
import { useAuth } from '@contexts/AuthContext'

function isTrialExpiringTomorrow(trial_ends_at: string | null | undefined): boolean {
  if (!trial_ends_at) return false
  const d = new Date(trial_ends_at)
  if (Number.isNaN(d.getTime())) return false
  const tomorrow = new Date()
  tomorrow.setDate(tomorrow.getDate() + 1)
  return d.getUTCDate() === tomorrow.getUTCDate() &&
    d.getUTCMonth() === tomorrow.getUTCMonth() &&
    d.getUTCFullYear() === tomorrow.getUTCFullYear()
}

function formatDate(val: string | null | undefined): string {
  if (!val) return '—'
  const d = new Date(val)
  return Number.isNaN(d.getTime()) ? String(val) : d.toLocaleDateString(undefined, { dateStyle: 'short' })
}

export default function TenantTrackerPage() {
  const { user } = useAuth()
  const { showAlert, showConfirm } = useAlert()
  const [rows, setRows] = useState<TenantOverviewRow[]>([])
  if (user?.role !== 'super_admin') {
    return <Navigate to="/" replace />
  }
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [toggling, setToggling] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getTenantsOverview()
      setRows(data)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load tenant overview')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleSetActive = async (tenant: string, active: boolean) => {
    const action = active ? 'activate' : 'deactivate'
    const ok = await showConfirm({
      title: active ? 'Activate tenant' : 'Deactivate tenant',
      message: `Are you sure you want to ${action} "${tenant}"?`,
    })
    if (!ok) return
    setToggling(tenant)
    try {
      await setTenantActive(tenant, active)
      await load()
      showAlert(`Tenant ${action}d`, 'success')
    } catch (e: any) {
      showAlert(e?.response?.data?.detail || `Failed to ${action} tenant`, 'error')
    } finally {
      setToggling(null)
    }
  }

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography color="text.secondary">Loading…</Typography>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Tenant Tracker (Super Admin)
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        All tenants with plan, payment, WhatsApp received count, trial end, and status. You can deactivate or activate a tenant from here.
      </Typography>
      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      <Card>
        <CardContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Tenant</TableCell>
                <TableCell>Plan</TableCell>
                <TableCell>Payment</TableCell>
                <TableCell align="right">WhatsApp received</TableCell>
                <TableCell>Trial ends</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Revenue (30d)</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} align="center" sx={{ py: 3 }} color="text.secondary">
                    No tenants found
                  </TableCell>
                </TableRow>
              ) : (
                rows.map((r) => (
                  <TableRow key={r.tenant}>
                    <TableCell>
                      <Stack direction="row" alignItems="center" spacing={1}>
                        <Typography variant="body2" fontWeight={500}>
                          {r.tenant}
                        </Typography>
                        {isTrialExpiringTomorrow(r.trial_ends_at) && (
                          <Chip label="Trial expires tomorrow" color="warning" size="small" />
                        )}
                      </Stack>
                      {r.owner_email && (
                        <Typography variant="caption" display="block" color="text.secondary">
                          {r.owner_email}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>{r.plan ?? '—'}</TableCell>
                    <TableCell>
                      {r.payment_config?.provider ?? '—'} {r.payment_config?.currency ? `(${r.payment_config.currency})` : ''}
                    </TableCell>
                    <TableCell align="right">{r.whatsapp_inbound_count}</TableCell>
                    <TableCell>{formatDate(r.trial_ends_at)}</TableCell>
                    <TableCell>
                      <Chip
                        label={r.active ? 'Active' : 'Inactive'}
                        color={r.active ? 'success' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="right">
                      {typeof r.revenue_30d === 'number' ? r.revenue_30d.toFixed(2) : '—'}
                    </TableCell>
                    <TableCell align="right">
                      <Button
                        size="small"
                        variant="outlined"
                        color={r.active ? 'warning' : 'primary'}
                        disabled={toggling === r.tenant}
                        onClick={() => handleSetActive(r.tenant, !r.active)}
                      >
                        {toggling === r.tenant ? '…' : r.active ? 'Make inactive' : 'Activate'}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Box>
  )
}
