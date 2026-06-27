import { useEffect, useState } from 'react'
import {
  Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle,
  IconButton, MenuItem, Stack, Table, TableBody, TableCell, TableHead, TableRow,
  TextField, Typography, Alert, FormControlLabel, Switch,
} from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import AddIcon from '@mui/icons-material/Add'
import { useNavigate } from 'react-router-dom'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useAlert } from '@contexts/AlertContext'
import {
  listCustomActions, upsertCustomAction, deleteCustomAction,
  listAvailableActions, PLACEHOLDER_HINTS, TenantCustomAction,
} from '@api/whatsapp'

const EMPTY: TenantCustomAction = {
  action_id: '',
  name: '',
  action_type: 'static_text',
  text: '',
  system_action_id: '',
  workflow_id: '',
  params: {},
  enabled: true,
}

export default function WhatsAppCustomActionsPage() {
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const navigate = useNavigate()
  const { showAlert, showConfirm } = useAlert()
  const [items, setItems] = useState<TenantCustomAction[]>([])
  const [systemActions, setSystemActions] = useState<Array<{ id: string; label: string }>>([])
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<TenantCustomAction>(EMPTY)
  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    if (!tenant) return
    try {
      const [customRes, actions] = await Promise.all([
        listCustomActions(tenant),
        listAvailableActions(tenant),
      ])
      setItems(customRes.items || [])
      setSystemActions(
        (actions || [])
          .filter(a => a.module !== 'custom' && a.id !== 'static_text')
          .map(a => ({ id: a.id, label: a.label }))
      )
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err.response?.data?.detail || 'Failed to load custom actions')
    }
  }

  useEffect(() => { refresh() }, [tenant])

  async function onSave() {
    if (!tenant) return
    setError(null)
    try {
      await upsertCustomAction(tenant, draft)
      setOpen(false)
      await refresh()
      showAlert('Action saved', 'success')
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setError(err.response?.data?.detail || 'Save failed')
    }
  }

  async function onDelete(actionId: string) {
    if (!tenant) return
    const ok = await showConfirm({ title: 'Delete action', message: `Delete "${actionId}"?` })
    if (!ok) return
    await deleteCustomAction(tenant, actionId)
    await refresh()
  }

  function openNew() {
    setDraft({ ...EMPTY, action_id: `action_${Date.now().toString(36)}` })
    setOpen(true)
  }

  function openEdit(row: TenantCustomAction) {
    setDraft({ ...row })
    setOpen(true)
  }

  return (
    <Box sx={{ p: 1 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5">WhatsApp Custom Actions</Typography>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" onClick={() => navigate('/whatsapp')}>Back</Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={openNew} disabled={!tenant}>
            New action
          </Button>
        </Stack>
      </Stack>

      {!tenant && <Alert severity="warning" sx={{ mb: 2 }}>Select a tenant first.</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Alert severity="info" sx={{ mb: 2 }}>
        Reusable actions appear in the Menu Editor action picker as <strong>custom.*</strong>.
        Placeholders: {PLACEHOLDER_HINTS.join(', ')}
      </Alert>

      <Card>
        <CardContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Runtime ref</TableCell>
                <TableCell>Enabled</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map(row => (
                <TableRow key={row.action_id}>
                  <TableCell>{row.action_id}</TableCell>
                  <TableCell>{row.name}</TableCell>
                  <TableCell><Chip size="small" label={row.action_type} /></TableCell>
                  <TableCell><code>custom.{row.action_id}</code></TableCell>
                  <TableCell>{row.enabled === false ? 'No' : 'Yes'}</TableCell>
                  <TableCell align="right">
                    <IconButton size="small" onClick={() => openEdit(row)}><EditIcon fontSize="small" /></IconButton>
                    <IconButton size="small" color="error" onClick={() => onDelete(row.action_id)}><DeleteIcon fontSize="small" /></IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {!items.length && (
                <TableRow>
                  <TableCell colSpan={6}>
                    <Typography variant="body2" color="text.secondary">No custom actions yet.</Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{draft.action_id && items.some(i => i.action_id === draft.action_id) ? 'Edit' : 'New'} custom action</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField label="Action ID (slug)" value={draft.action_id}
              onChange={e => setDraft({ ...draft, action_id: e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, '') })}
              helperText="Lowercase letters, numbers, _, -" disabled={items.some(i => i.action_id === draft.action_id && open)} />
            <TextField label="Display name" value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} />
            <TextField select label="Type" value={draft.action_type}
              onChange={e => setDraft({ ...draft, action_type: e.target.value as TenantCustomAction['action_type'] })}>
              <MenuItem value="static_text">Static text</MenuItem>
              <MenuItem value="predefined">Predefined system action</MenuItem>
              <MenuItem value="workflow">Workflow</MenuItem>
            </TextField>
            {(draft.action_type === 'static_text' || draft.action_type === 'predefined') && (
              <TextField label="Message text (optional prefix for predefined)" value={draft.text || ''}
                onChange={e => setDraft({ ...draft, text: e.target.value })} multiline minRows={4}
                helperText={`Supports placeholders: ${PLACEHOLDER_HINTS.join(', ')}`} />
            )}
            {draft.action_type === 'predefined' && (
              <TextField select label="System action" value={draft.system_action_id || ''}
                onChange={e => setDraft({ ...draft, system_action_id: e.target.value })}>
                {systemActions.map(a => <MenuItem key={a.id} value={a.id}>{a.label} ({a.id})</MenuItem>)}
              </TextField>
            )}
            {draft.action_type === 'workflow' && (
              <TextField label="Workflow ID" value={draft.workflow_id || ''}
                onChange={e => setDraft({ ...draft, workflow_id: e.target.value })}
                helperText="Without workflow. prefix — e.g. salon_booking_flow" />
            )}
            <FormControlLabel control={<Switch checked={draft.enabled !== false}
              onChange={e => setDraft({ ...draft, enabled: e.target.checked })} />}
              label="Enabled" />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={onSave}>Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
