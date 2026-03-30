import { useEffect, useMemo, useState } from 'react'
import { Box, Button, Card, CardContent, Grid, IconButton, Stack, Switch, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography, Alert } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { WhatsAppTrigger, listTriggers, updateTrigger, deleteTrigger, testTriggerWebhook } from '../../api/whatsapp'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useAlert } from '@contexts/AlertContext'

function formatMatchValue(v: unknown): string {
  if (v == null) return ''
  if (Array.isArray(v)) return v.map((x) => String(x)).join(' · ')
  return String(v)
}

export default function TriggersIndex(){
  const { effectiveTenant: tenant, ready } = useEffectiveTenant()
  const { showConfirm } = useAlert()
  const navigate = useNavigate()
  const [items, setItems] = useState<WhatsAppTrigger[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string|null>(null)
  const [message, setMessage] = useState<string|null>(null)
  const [testTo, setTestTo] = useState<string>('')
  const [testBody, setTestBody] = useState<string>('hi')
  const [testResult, setTestResult] = useState<string>('')

  async function refresh(){
    if(!ready || !tenant) return
    setLoading(true); setError(null)
    try{
      const res = await listTriggers(tenant)
      setItems(res.items || [])
    }catch(e:any){
      const d = e?.response?.data?.detail
      let msg = 'Failed to load triggers'
      if (typeof d === 'string') msg = d
      else if (Array.isArray(d) && d.length) msg = d[0]?.msg || JSON.stringify(d[0])
      else if (d && typeof d === 'object') msg = d.msg || JSON.stringify(d)
      else if (e?.message) msg = e.message
      setError(String(msg))
    }finally{ setLoading(false) }
  }
  useEffect(()=>{ refresh() // eslint-disable-next-line
  },[tenant, ready])

  async function toggleEnabled(row: WhatsAppTrigger){
    try{
      await updateTrigger(tenant, row.trigger_id, { enabled: !row.enabled })
      setItems(items.map(it => it.trigger_id === row.trigger_id ? { ...it, enabled: !row.enabled } : it))
    }catch(e:any){
      setError(String(e?.response?.data?.detail || e?.message || 'Failed to update'))
    }
  }

  async function changePriority(row: WhatsAppTrigger, value: number){
    try{
      await updateTrigger(tenant, row.trigger_id, { priority: value })
      setItems(items.map(it => it.trigger_id === row.trigger_id ? { ...it, priority: value } : it))
    }catch(e:any){
      setError(String(e?.response?.data?.detail || e?.message || 'Failed to update priority'))
    }
  }

  async function onDelete(row: WhatsAppTrigger){
    const ok = await showConfirm({ title: 'Delete trigger', message: `Delete trigger "${row.trigger_id}"?` })
    if(!ok) return
    try{
      await deleteTrigger(tenant, row.trigger_id)
      setItems(items.filter(it => it.trigger_id !== row.trigger_id))
      setMessage('Deleted')
    }catch(e:any){
      setError(String(e?.response?.data?.detail || e?.message || 'Delete failed'))
    }
  }

  async function onTest(){
    setError(null); setMessage(null); setTestResult('')
    try{
      if(!testTo){ setError('Enter a To number (tenant WhatsApp number)'); return }
      const xml = await testTriggerWebhook(testTo, testBody || 'hi')
      setTestResult(xml)
    }catch(e:any){
      setError(String(e?.response?.data?.detail || e?.message || 'Test failed'))
    }
  }

  const sorted = useMemo(()=>{
    return [...items].sort((a,b)=> (b.priority - a.priority) || a.trigger_id.localeCompare(b.trigger_id))
  },[items])

  return (
    <Box sx={{ p:1 }}>
      <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems="center" justifyContent="space-between" sx={{ mb:2 }}>
        <Typography variant="h5">WhatsApp Triggers</Typography>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" onClick={()=>navigate('/whatsapp')}>Back</Button>
          <Button
            variant="contained"
            disabled={!tenant}
            onClick={()=>{
              const q = tenant ? `?tenant=${encodeURIComponent(tenant)}` : ''
              navigate(`/whatsapp/triggers/new${q}`)
            }}
          >New Trigger</Button>
        </Stack>
      </Stack>

      {(!tenant) && ready && (
        <Alert severity='warning' sx={{ mb:2 }}>No tenants available. Please create a tenant first.</Alert>
      )}
      {error && <Alert severity='error' sx={{ mb:2 }}>{error}</Alert>}
      {message && <Alert severity='success' sx={{ mb:2 }}>{message}</Alert>}

      <Card sx={{ mb:2 }}>
        <CardContent>
          <Typography variant="subtitle1" sx={{ mb:1 }}>Test a phrase (calls dummy Twilio webhook)</Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <TextField label="To (tenant WhatsApp number)" placeholder="+911234567890" fullWidth size="small" value={testTo} onChange={e=>setTestTo(e.target.value)} />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField label="Message" placeholder="hi | book | enquiry" fullWidth size="small" value={testBody} onChange={e=>setTestBody(e.target.value)} />
            </Grid>
            <Grid item xs={12} md={4}>
              <Button variant="outlined" onClick={onTest} sx={{ mt:{ xs:1, md:0 } }}>Send Test</Button>
            </Grid>
            {testResult && (
              <Grid item xs={12}>
                <TextField label="Response (TwiML XML)" value={testResult} fullWidth multiline minRows={3} />
              </Grid>
            )}
          </Grid>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Enabled</TableCell>
                <TableCell>Trigger ID</TableCell>
                <TableCell>Match</TableCell>
                <TableCell>Action</TableCell>
                <TableCell>Priority</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sorted.map(row => (
                <TableRow key={row.trigger_id} hover>
                  <TableCell>
                    <Switch checked={!!row.enabled} onChange={()=>toggleEnabled(row)} />
                  </TableCell>
                  <TableCell>{row.trigger_id}</TableCell>
                  <TableCell>{row.match?.type}: {formatMatchValue(row.match?.value)}{row.match?.locale ? ` (${row.match.locale})` : ''}</TableCell>
                  <TableCell>
                    {row.action?.kind}
                    {(row.action as any)?.action_id ? ` → ${(row.action as any).action_id}` : ''}
                    {row.action && (row.action as any).menu_id ? ` / ${(row.action as any).menu_id}` : ''}
                    {row.action && (row.action as any).node_id ? ` / node ${(row.action as any).node_id}` : ''}
                    {row.action?.kind === 'static_text' ? ` (text length: ${String((row.action as any).text || '').length})` : ''}
                    {row.action?.kind === 'invoke_action' && !(row.action as any).action_id ? (
                      <Typography component="span" color="warning.main" sx={{ ml: 0.5 }}>— fix: pick action</Typography>
                    ) : null}
                  </TableCell>
                  <TableCell>
                    <TextField type="number" size="small" value={row.priority} onChange={(e)=>changePriority(row, parseInt(e.target.value || '0',10))} sx={{ width: 100 }} />
                  </TableCell>
                  <TableCell align="right">
                    <IconButton onClick={()=>navigate(`/whatsapp/triggers/${encodeURIComponent(row.trigger_id)}`)} title="Edit"><EditIcon /></IconButton>
                    <IconButton onClick={()=>onDelete(row)} color="error" title="Delete"><DeleteIcon /></IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {!loading && !items.length && <Typography sx={{ mt:2 }} color="text.secondary">No triggers yet. Click "New Trigger" to add one.</Typography>}
        </CardContent>
      </Card>
    </Box>
  )
}
