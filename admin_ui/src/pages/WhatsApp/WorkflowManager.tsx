import { useState, useEffect, Fragment } from 'react'
import { Box, Typography, Card, CardContent, Table, TableHead, TableRow, TableCell, TableBody, Button, Stack, IconButton, Chip, Dialog, DialogTitle, DialogContent, DialogActions, TextField, Divider, ListSubheader, Autocomplete } from '@mui/material'
import { Add as AddIcon, Delete as DeleteIcon, Edit as EditIcon, ArrowUpward as UpIcon, ArrowDownward as DownIcon } from '@mui/icons-material'
import { listWorkflows, upsertWorkflow, deleteWorkflow, listAvailableWorkflowActions, WorkflowDefinition, WorkflowStep, WorkflowActionMeta } from '@api/workflows'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useAlert } from '@contexts/AlertContext'

const MODULE_ORDER = ['salon', 'clinic', 'store', 'core']
const MODULE_LABELS: Record<string, string> = { salon: 'Salon', clinic: 'Clinic', store: 'Store', core: 'Core' }
// Green "End" button adds END (close workflow). "Finalize booking" is the step that saves the appointment.
const WORKFLOW_END_ACTION_CODE = 'END'

export default function WorkflowManager() {
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const { showAlert, showConfirm } = useAlert()
  const [workflows, setWorkflows] = useState<WorkflowDefinition[]>([])
  const [availableActions, setAvailableActions] = useState<WorkflowActionMeta[]>([])
  const [open, setOpen] = useState(false)
  const [editingWf, setEditingWf] = useState<Partial<WorkflowDefinition>>({})
  const [loading, setLoading] = useState(false)

  const loadData = async () => {
    if (!tenant) return
    setLoading(true)
    try {
      const [wfRes, actionsRes] = await Promise.all([
        listWorkflows(tenant),
        listAvailableWorkflowActions(tenant)
      ])
      setWorkflows(wfRes.items)
      setAvailableActions(actionsRes.items)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [tenant])

  const handleSave = async () => {
    const wfId = (editingWf.workflow_id ?? '').trim()
    const wfName = (editingWf.name ?? '').trim()
    if (!tenant || !wfId || !wfName) return
    try {
      await upsertWorkflow(tenant, {
        tenant,
        workflow_id: wfId,
        name: wfName,
        steps: editingWf.steps || [],
        active: editingWf.active ?? true
      })
      setOpen(false)
      loadData()
    } catch (e) {
      showAlert('Failed to save workflow', 'error')
    }
  }

  const handleDelete = async (wf: WorkflowDefinition) => {
    if (!tenant) return
    const ok = await showConfirm({ title: 'Delete workflow', message: `Delete "${wf.name}" (${wf.workflow_id})? This cannot be undone.` })
    if (!ok) return
    try {
      await deleteWorkflow(tenant, wf.workflow_id)
      showAlert('Workflow deleted', 'success')
      loadData()
      if (editingWf?.workflow_id === wf.workflow_id) setOpen(false)
    } catch (e) {
      showAlert('Failed to delete workflow', 'error')
    }
  }

  const addStep = () => {
    const steps = [...(editingWf.steps || [])]
    steps.push({
      action_code: availableActions[0]?.action_code || 'SHOW_SERVICES',
      input_required: true,
      ui_type: 'list'
    })
    setEditingWf({ ...editingWf, steps })
  }

  const removeStep = (idx: number) => {
    const steps = [...(editingWf.steps || [])]
    steps.splice(idx, 1)
    setEditingWf({ ...editingWf, steps })
  }

  const updateStep = (idx: number, patch: Partial<WorkflowStep>) => {
    const steps = [...(editingWf.steps || [])]
    steps[idx] = { ...steps[idx], ...patch }
    
    // Auto-fill from meta
    if (patch.action_code) {
        const meta = availableActions.find(a => a.action_code === patch.action_code)
        if (meta) {
            steps[idx].input_required = meta.input_required
            steps[idx].ui_type = meta.ui_type
            steps[idx].output_key = meta.output_key
        }
    }
    
    setEditingWf({ ...editingWf, steps })
  }

  const moveStep = (idx: number, dir: number) => {
    const steps = [...(editingWf.steps || [])]
    const newIdx = idx + dir
    if (newIdx < 0 || newIdx >= steps.length) return
    const tmp = steps[idx]
    steps[idx] = steps[newIdx]
    steps[newIdx] = tmp
    setEditingWf({ ...editingWf, steps })
  }

  const END_ACTION_CODES = [WORKFLOW_END_ACTION_CODE]
  const stepActions = availableActions.filter(a => !END_ACTION_CODES.includes(a.action_code))
  const endActions = availableActions.filter(a => END_ACTION_CODES.includes(a.action_code))
  const actionsByModule = (() => {
    const map: Record<string, WorkflowActionMeta[]> = {}
    for (const a of stepActions) {
      const mod = (a.module || 'core').toLowerCase()
      if (!map[mod]) map[mod] = []
      map[mod].push(a)
    }
    return MODULE_ORDER.filter(m => map[m]?.length).map(m => ({ module: m, label: MODULE_LABELS[m] || m, actions: map[m]! }))
  })()
  const actionOptions: WorkflowActionMeta[] = [...actionsByModule.flatMap(g => g.actions), ...endActions]
  const getActionGroup = (a: WorkflowActionMeta) => END_ACTION_CODES.includes(a.action_code) ? 'End' : (MODULE_LABELS[(a.module || 'core').toLowerCase()] || a.module || 'Core')
  const isEndAction = (actionCode: string) => END_ACTION_CODES.includes(actionCode)
  const stepLabel = (actionCode: string) => isEndAction(actionCode) ? 'End' : (availableActions.find(a => a.action_code === actionCode)?.label || actionCode)

  const addEndAction = () => {
    const steps = [...(editingWf.steps || [])]
    const endMeta = endActions[0]
    if (!endMeta) return
    steps.push({
      action_code: endMeta.action_code,
      input_required: endMeta.input_required,
      ui_type: endMeta.ui_type,
      output_key: endMeta.output_key
    })
    setEditingWf({ ...editingWf, steps })
  }

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h5">Workflows</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => { setEditingWf({ steps: [], active: true }); setOpen(true); }}>New Workflow</Button>
      </Stack>

      <Card>
        <CardContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>ID / Name</TableCell>
                <TableCell>Steps</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {workflows.map((wf) => (
                <TableRow key={wf.workflow_id}>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">{wf.name}</Typography>
                    <Typography variant="caption" color="text.secondary">{wf.workflow_id}</Typography>
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap', gap: 0.5 }}>
                        {wf.steps.map((s, i) => (
                            <Chip key={i} label={END_ACTION_CODES.includes(s.action_code) ? 'End' : (availableActions.find(a => a.action_code === s.action_code)?.label || s.action_code)} size="small" variant="outlined" color={END_ACTION_CODES.includes(s.action_code) ? 'success' : 'default'} />
                        ))}
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Chip label={wf.active ? 'Active' : 'Inactive'} color={wf.active ? 'success' : 'default'} size="small" />
                  </TableCell>
                  <TableCell align="right">
                    <IconButton size="small" onClick={() => { setEditingWf(wf); setOpen(true); }} aria-label="Edit"><EditIcon fontSize="small" /></IconButton>
                    <IconButton size="small" color="error" onClick={() => handleDelete(wf)} aria-label="Delete"><DeleteIcon fontSize="small" /></IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {!workflows.length && <TableRow><TableCell colSpan={4} align="center">No workflows defined</TableCell></TableRow>}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>{editingWf.workflow_id ? 'Edit Workflow' : 'New Workflow'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Stack direction="row" spacing={2}>
                <TextField label="Workflow ID" fullWidth size="small" value={editingWf.workflow_id || ''} onChange={e => setEditingWf({ ...editingWf, workflow_id: e.target.value })} placeholder="e.g. booking" disabled={!!workflows.find(w => w.workflow_id === editingWf.workflow_id && w !== editingWf)} helperText="Required" />
                <TextField label="Display Name" fullWidth size="small" value={editingWf.name || ''} onChange={e => setEditingWf({ ...editingWf, name: e.target.value })} placeholder="e.g. Booking flow" helperText="Required" />
            </Stack>
            
            <Divider>Steps</Divider>
            <Typography variant="caption" display="block" color="text.secondary" sx={{ mb: 1 }}>
              Add <strong>Finalize booking</strong> from the list to save the appointment. Use the green <strong>End</strong> button for <strong>End (close workflow)</strong> — thank-you only (no booking save).
            </Typography>

            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
              <Chip label="Start" size="small" color="primary" sx={{ fontWeight: 600 }} />
              <Typography variant="caption" color="text.secondary">→ steps run in order →</Typography>
            </Stack>

            {editingWf.steps?.map((step, idx) => (
                <Card key={idx} variant="outlined" sx={{ p: 1, bgcolor: isEndAction(step.action_code) ? 'rgba(34, 197, 94, 0.12)' : 'rgba(51, 65, 85, 0.5)', borderColor: isEndAction(step.action_code) ? '#22c55e' : '#334155' }}>
                    <Stack spacing={1}>
                        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                            <Typography variant="caption" sx={{ fontWeight: 'bold', minWidth: 20, color: '#e2e8f0' }}>{idx + 1}. {stepLabel(step.action_code)}</Typography>
                            <Autocomplete
                              size="small"
                              sx={{ flex: 2, minWidth: 220 }}
                              options={actionOptions}
                              value={actionOptions.find(a => a.action_code === step.action_code) ?? null}
                              onChange={(_, val) => updateStep(idx, { action_code: val?.action_code ?? '' })}
                              getOptionLabel={(a) => `${a.label ?? a.action_code} (${a.action_code})`}
                              groupBy={getActionGroup}
                              filterOptions={(opts, { inputValue }) => {
                                const q = (inputValue || '').trim().toLowerCase()
                                if (!q) return opts
                                return opts.filter(o =>
                                  (o.label || '').toLowerCase().includes(q) ||
                                  (o.action_code || '').toLowerCase().includes(q) ||
                                  (o.module || '').toLowerCase().includes(q)
                                )
                              }}
                              renderInput={(params) => <TextField {...params} label="Action" />}
                              renderGroup={(params) => (
                                <Fragment key={params.key}>
                                  <ListSubheader sx={{ bgcolor: params.group === 'End' ? 'rgba(34, 197, 94, 0.2)' : 'action.hover', color: params.group === 'End' ? 'success.dark' : undefined, fontWeight: 600 }}>
                                    {params.group}
                                  </ListSubheader>
                                  {params.children}
                                </Fragment>
                              )}
                            />
                            <TextField label="Custom Prompt (optional)" size="small" sx={{ flex: 3, minWidth: 140 }} value={step.label || ''} onChange={e => updateStep(idx, { label: e.target.value })} placeholder="Override default question" />
                            {isEndAction(step.action_code) && (
                                <Chip label="End" size="small" color="success" sx={{ flexShrink: 0 }} />
                            )}
                            <Stack direction="row">
                                <IconButton size="small" onClick={() => moveStep(idx, -1)} disabled={idx === 0}><UpIcon fontSize="small"/></IconButton>
                                <IconButton size="small" onClick={() => moveStep(idx, 1)} disabled={idx === (editingWf.steps?.length || 0) - 1}><DownIcon fontSize="small"/></IconButton>
                                <IconButton size="small" color="error" onClick={() => removeStep(idx)}><DeleteIcon fontSize="small"/></IconButton>
                            </Stack>
                        </Stack>
                        <Stack direction="row" spacing={2} sx={{ ml: 4 }} flexWrap="wrap">
                            <Typography variant="caption" sx={{ color: '#94a3b8' }}>Input: {step.input_required ? 'Yes' : 'No'} | UI: {step.ui_type} | Key: {step.output_key || 'N/A'}</Typography>
                        </Stack>
                    </Stack>
                </Card>
            ))}
            
            <Stack direction="row" spacing={1} flexWrap="wrap" alignItems="center">
              <Button startIcon={<AddIcon />} onClick={addStep}>Add Step</Button>
              {endActions.length > 0 && (
                <Button variant="outlined" color="success" startIcon={<AddIcon />} onClick={addEndAction}>
                  End
                </Button>
              )}
              <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}><strong>End</strong> = close workflow (message only). Booking: … → <strong>Finalize booking</strong> → optional <strong>End (close workflow)</strong>.</Typography>
            </Stack>
          </Stack>
        </DialogContent>
        <DialogActions>
          {!tenant && <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>Select a tenant to save.</Typography>}
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained" disabled={!tenant || !(editingWf.workflow_id ?? '').trim() || !(editingWf.name ?? '').trim()}>Save Workflow</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
