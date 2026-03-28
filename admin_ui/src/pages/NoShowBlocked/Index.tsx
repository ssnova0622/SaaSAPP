import { useEffect, useState, useCallback } from 'react'
import { Box, Button, Card, CardContent, Table, TableBody, TableCell, TableHead, TableRow, Typography, Alert, TextField, InputAdornment } from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import { listNoShowBlocked, resetNoShow, type NoShowBlockedItem } from '@api/appointments'
import { getTenantSettings } from '@api/tenants'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useCapabilities } from '../../hooks/useCapabilities'
import { formatPhoneForDisplay } from '../../utils/phone'
import { useAlert } from '@contexts/AlertContext'
import ExportMenu from '@components/ExportMenu'

export default function NoShowBlocked() {
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const { canEditNoShowBlocked } = useCapabilities()
  const { showAlert } = useAlert()
  const [data, setData] = useState<{ items: NoShowBlockedItem[]; threshold: number } | null>(null)
  const [loading, setLoading] = useState(false)
  const [resetting, setResetting] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [aiNoShowEnabled, setAiNoShowEnabled] = useState<boolean | null>(null)

  useEffect(() => {
    if (!tenant) {
      setAiNoShowEnabled(null)
      return
    }
    getTenantSettings(tenant).then((s) => {
      const mods = (s.modules || []).map((m) => String(m).toLowerCase())
      const caps = (s.capabilities || []).map((c) => String(c).toLowerCase())
      setAiNoShowEnabled(mods.includes('ai') && caps.includes('ai.no_show'))
    }).catch(() => setAiNoShowEnabled(false))
  }, [tenant])

  const load = useCallback(async () => {
    if (!tenant || aiNoShowEnabled !== true) return
    setLoading(true)
    try {
      const res = await listNoShowBlocked(tenant, search.trim() || undefined)
      setData({ items: res.items || [], threshold: res.threshold || 3 })
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Failed to load blocked list'
      showAlert(msg, 'error')
      setData({ items: [], threshold: 3 })
    } finally {
      setLoading(false)
    }
  }, [tenant, search, aiNoShowEnabled])

  useEffect(() => {
    if (aiNoShowEnabled === true) load()
    else if (aiNoShowEnabled === false) setData(null)
  }, [aiNoShowEnabled, load])

  async function handleReset(phone: string) {
    if (!tenant) return
    setResetting(phone)
    try {
      await resetNoShow(tenant, phone)
      showAlert('No-show count reset. This number can book again.', 'success')
      await load()
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Failed to reset'
      showAlert(msg, 'error')
    } finally {
      setResetting(null)
    }
  }

  return (
    <Box sx={{ p: 1 }}>
      <Typography variant="h5" sx={{ mb: 2 }}>No-Show Blocked List</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Phone numbers with no-show count at or above the threshold are blocked from booking (admin and WhatsApp). Reset to allow booking again.
      </Typography>

      {!tenant && (
        <Alert severity="warning">Select a tenant to view the blocked list.</Alert>
      )}

      {tenant && aiNoShowEnabled === false && (
        <Alert severity="info" sx={{ mb: 2 }}>
          No-Show Blocked is an AI feature. Enable the AI module and <code>ai.no_show</code> capability for this tenant in Settings → Plan &amp; Access to use this page.
        </Alert>
      )}

      {tenant && aiNoShowEnabled === true && loading && !data && (
        <Typography variant="body2" color="text.secondary">Loading blocked list...</Typography>
      )}

      {tenant && aiNoShowEnabled === true && data && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center', mb: 2 }}>
              <TextField
                size="small"
                placeholder="Search by phone or name..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && load()}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon fontSize="small" />
                    </InputAdornment>
                  ),
                }}
                sx={{ minWidth: 220 }}
              />
              <Button size="small" variant="outlined" onClick={() => load()}>Search</Button>
              <ExportMenu
                data={data.items}
                columns={[{ key: 'phone', label: 'Phone' }, { key: 'name', label: 'Name' }, { key: 'no_show_count', label: 'No-Show Count' }]}
                filename="no_show_blocked"
                title="No-Show Blocked List"
                size="small"
                disabled={data.items.length === 0}
              />
            </Box>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Block threshold: <strong>{data.threshold}</strong> no-shows {data.threshold === 0 ? '(blocking disabled)' : ''}
            </Typography>
            {data.threshold === 0 && (
              <Alert severity="info" sx={{ mb: 2 }}>Set <code>no_show_block_threshold</code> in Settings → AI config to enable blocking.</Alert>
            )}
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Phone</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell align="right">No-Show Count</TableCell>
                  {canEditNoShowBlocked && <TableCell align="right">Actions</TableCell>}
                </TableRow>
              </TableHead>
              <TableBody>
                {data.items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={canEditNoShowBlocked ? 4 : 3}>
                      <Typography variant="body2" color="text.secondary">
                        {loading ? 'Loading...' : 'No blocked numbers.'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
                {data.items.map((row) => (
                  <TableRow key={row.phone}>
                    <TableCell>{formatPhoneForDisplay(row.phone)}</TableCell>
                    <TableCell>{row.name || '—'}</TableCell>
                    <TableCell align="right">{row.no_show_count}</TableCell>
                    {canEditNoShowBlocked && (
                      <TableCell align="right">
                        <Button
                          size="small"
                          variant="outlined"
                          color="primary"
                          disabled={resetting === row.phone}
                          onClick={() => handleReset(row.phone)}
                        >
                          {resetting === row.phone ? 'Resetting...' : 'Reset (allow booking)'}
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </Box>
  )
}
