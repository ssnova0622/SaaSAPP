import { useState, useEffect } from 'react'
import { Box, Typography, Card, CardContent, Table, TableHead, TableRow, TableCell, TableBody, Switch, Button, IconButton, Stack, Chip, Dialog, DialogTitle, DialogContent, DialogActions, TextField, MenuItem } from '@mui/material'
import { Delete as DeleteIcon, Refresh as RefreshIcon, Add as AddIcon, PlayArrow as RunIcon } from '@mui/icons-material'
import { listCronJobs, toggleCronJob, deleteCronJob, upsertCronJob, runCronJob, listAvailableCronActions, CronJob } from '@api/cron'
import { useAlert } from '@contexts/AlertContext'

export default function CronJobsPage() {
  const { showAlert, showConfirm } = useAlert()
  const [jobs, setJobs] = useState<CronJob[]>([])
  const [availableActions, setAvailableActions] = useState<Array<{job_id: string, name: string, type: string}>>([])
  const [loading, setLoading] = useState(false)
  const [runningJobId, setRunningJobId] = useState<string | null>(null)
  const [open, setOpen] = useState(false)
  const [editingJob, setEditingJob] = useState<Partial<CronJob>>({})

  const loadJobs = async () => {
    setLoading(true)
    try {
      const [data, actions] = await Promise.all([
        listCronJobs(),
        listAvailableCronActions()
      ])
      setJobs(data)
      setAvailableActions(actions)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadJobs()
  }, [])

  const handleToggle = async (jobId: string, current: boolean) => {
    try {
      await toggleCronJob(jobId, !current)
      loadJobs()
    } catch (e) {
      showAlert('Failed to toggle job', 'error')
    }
  }

  const handleDelete = async (jobId: string) => {
    const ok = await showConfirm({ title: 'Delete job', message: 'Are you sure?' })
    if (!ok) return
    try {
      await deleteCronJob(jobId)
      loadJobs()
    } catch (e) {
      showAlert('Failed to delete job', 'error')
    }
  }

  const handleSave = async () => {
    try {
        if (typeof editingJob.schedule_value === 'string') {
            try {
                editingJob.schedule_value = JSON.parse(editingJob.schedule_value)
            } catch(e) {
                showAlert("Invalid JSON in Schedule Value", "error")
                return
            }
        }
      await upsertCronJob(editingJob)
      setOpen(false)
      loadJobs()
    } catch (e) {
      showAlert('Failed to save job', 'error')
    }
  }

  const handleRunNow = async (jobId: string) => {
    setRunningJobId(jobId)
    try {
      await runCronJob(jobId)
      showAlert(`Job ${jobId} triggered successfully`, 'success')
      loadJobs()
    } catch (e: any) {
      showAlert('Failed to trigger job: ' + (e.response?.data?.detail || e.message), 'error')
    } finally {
      setRunningJobId(null)
    }
  }

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h5">Cron Jobs Management (Super Admin)</Typography>
        <Stack direction="row" spacing={1}>
            <Button startIcon={<RefreshIcon />} onClick={loadJobs}>Refresh</Button>
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => { setEditingJob({ schedule_type: 'interval', schedule_value: {}, enabled: true }); setOpen(true); }}>New Job</Button>
        </Stack>
      </Stack>

      <Card>
        <CardContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Job ID / Name</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Schedule</TableCell>
                <TableCell>Enabled</TableCell>
                <TableCell>Last Run</TableCell>
                <TableCell>Next Run</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {jobs.map((job) => (
                <TableRow key={job.job_id}>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">{job.name}</Typography>
                    <Typography variant="caption" color="text.secondary">{job.job_id}</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={job.type} size="small" />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{job.schedule_type}</Typography>
                    <Typography variant="caption">{JSON.stringify(job.schedule_value)}</Typography>
                  </TableCell>
                  <TableCell>
                    <Switch checked={job.enabled} onChange={() => handleToggle(job.job_id, job.enabled)} />
                  </TableCell>
                  <TableCell>
                    {job.last_run ? new Date(job.last_run).toLocaleString() : 'Never'}
                  </TableCell>
                  <TableCell>
                    {job.next_run ? new Date(job.next_run).toLocaleString() : (job.enabled ? 'Calculating...' : 'Disabled')}
                  </TableCell>
                  <TableCell>
                    <IconButton size="small" color="primary" onClick={() => handleRunNow(job.job_id)} disabled={runningJobId === job.job_id || !job.enabled} title="Run Now">
                      <RunIcon fontSize="small" />
                    </IconButton>
                    <IconButton size="small" onClick={() => { setEditingJob(job); setOpen(true); }}><RefreshIcon fontSize="small" /></IconButton>
                    <IconButton size="small" color="error" onClick={() => handleDelete(job.job_id)}><DeleteIcon fontSize="small" /></IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {loading && <TableRow><TableCell colSpan={6} align="center">Loading...</TableCell></TableRow>}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{editingJob.job_id ? (editingJob.id ? 'Edit Job' : 'Register Job') : 'New Cron Job'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField 
                select 
                label="Action / Job ID" 
                fullWidth 
                size="small" 
                value={editingJob.job_id || ''} 
                onChange={(e) => {
                    const action = availableActions.find(a => a.job_id === e.target.value);
                    setEditingJob({ 
                        ...editingJob, 
                        job_id: e.target.value, 
                        name: action ? action.name : (editingJob.name || ''),
                        type: action ? (action.type as any) : (editingJob.type || 'promotion')
                    });
                }} 
                disabled={!!editingJob.id}
            >
                {availableActions.map(action => (
                    <MenuItem key={action.job_id} value={action.job_id}>
                        {action.name} ({action.job_id})
                    </MenuItem>
                ))}
            </TextField>
            <TextField label="Display Name" fullWidth size="small" value={editingJob.name || ''} onChange={(e) => setEditingJob({ ...editingJob, name: e.target.value })} />
            <TextField select label="Category Type" fullWidth size="small" value={editingJob.type || 'promotion'} onChange={(e) => setEditingJob({ ...editingJob, type: e.target.value as any })}>
              <MenuItem value="promotion">Promotion</MenuItem>
              <MenuItem value="report">Report / Task</MenuItem>
              <MenuItem value="retention">Retention</MenuItem>
              <MenuItem value="stock_alert">Stock Alert</MenuItem>
            </TextField>
            <TextField select label="Schedule Type" fullWidth size="small" value={editingJob.schedule_type || 'interval'} onChange={(e) => setEditingJob({ ...editingJob, schedule_type: e.target.value as any })}>
              <MenuItem value="interval">Interval</MenuItem>
              <MenuItem value="cron">Cron</MenuItem>
            </TextField>
            <TextField 
                label="Schedule Value (JSON)" 
                fullWidth 
                multiline 
                rows={2} 
                size="small" 
                value={typeof editingJob.schedule_value === 'string' ? editingJob.schedule_value : JSON.stringify(editingJob.schedule_value)} 
                onChange={(e) => setEditingJob({ ...editingJob, schedule_value: e.target.value })} 
                helperText="e.g. {'seconds': 30} or {'hour': 9, 'minute': 30}"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={handleSave} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
