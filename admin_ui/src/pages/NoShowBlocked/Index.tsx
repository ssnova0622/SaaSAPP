import { useEffect, useState, useCallback } from 'react'
import { Box, Button, Card, CardContent, Chip, Table, TableBody, TableCell, TableHead, TableRow, Typography, Alert, TextField, InputAdornment } from '@mui/material'
import SearchIcon from '@mui/icons-material/Search'
import { listNoShowBlocked, resetNoShow, type NoShowBlockedItem } from '@api/appointments'
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

  const load = useCallback(async () => {
    if (!tenant) return
    setLoading(true)
    try {
      const res = await listNoShowBlocked(tenant, search.trim() || undefined)
      setData({ items: res.items || [], threshold: res.threshold ?? 3 })
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'Failed to load no-show list'
      showAlert(msg, 'error')
      setData({ items: [], threshold: 3 })
    } finally {
      setLoading(false)
    }
  }, [tenant, search])

  useEffect(() => {
    if (tenant) load()
    else setData(null)
  }, [tenant, load])

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
      <Typography variant="h5" sx={{ mb: 2 }}>No-Show Tracker</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        All customers who have missed at least one appointment. Those at or above the block threshold are automatically blocked from booking. Reset to allow booking again.
      </Typography>

      {!tenant && (
        <Alert severity="warning">Select a tenant to view the no-show list.</Alert>
      )}

      {tenant && loading && !data && (
        <Typography variant="body2" color="text.secondary">Loading no-show list...</Typography>
      )}

      {tenant && data && (
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
                filename="no_show_tracker"
                title="No-Show Tracker"
                size="small"
                disabled={data.items.length === 0}
              />
            </Box>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Block threshold: <strong>{data.threshold > 0 ? data.threshold : 'Not set'}</strong> no-shows
              {data.threshold <= 0 && ' — blocking disabled'}
            </Typography>
            {data.threshold <= 0 && (
              <Alert severity="info" sx={{ mb: 2 }}>Set <code>no_show_block_threshold</code> in Settings → AI config to auto-block repeat no-shows.</Alert>
            )}
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Phone</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell align="right">No-Show Count</TableCell>
                  <TableCell align="center">Status</TableCell>
                  {canEditNoShowBlocked && <TableCell align="right">Actions</TableCell>}
                </TableRow>
              </TableHead>
              <TableBody>
                {data.items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={canEditNoShowBlocked ? 5 : 4}>
                      <Typography variant="body2" color="text.secondary">
                        {loading ? 'Loading...' : 'No no-show records found.'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
                {data.items.map((row) => {
                  const isBlocked = data.threshold > 0 && row.no_show_count >= data.threshold
                  return (
                    <TableRow key={row.phone}>
                      <TableCell>{formatPhoneForDisplay(row.phone)}</TableCell>
                      <TableCell>{row.name || '—'}</TableCell>
                      <TableCell align="right">{row.no_show_count}</TableCell>
                      <TableCell align="center">
                        {isBlocked
                          ? <Chip label="Blocked" color="error" size="small" />
                          : <Chip label="Warned" color="warning" size="small" />}
                      </TableCell>
                      {canEditNoShowBlocked && (
                        <TableCell align="right">
                          <Button
                            size="small"
                            variant="outlined"
                            color="primary"
                            disabled={resetting === row.phone}
                            onClick={() => handleReset(row.phone)}
                          >
                            {resetting === row.phone ? 'Resetting...' : 'Reset'}
                          </Button>
                        </TableCell>
                      )}
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </Box>
  )
}
