import { useEffect, useState } from 'react'
import { Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography, Alert } from '@mui/material'
import { useAlert } from '@contexts/AlertContext'
import { listMenus, deleteMenu, publishMenu, WhatsAppMenu, getMenu, upsertMenu } from '@api/whatsapp'
import { getWhatsAppConfig } from '@api/tenants'
import { useNavigate } from 'react-router-dom'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useTenantDisplayPreferences } from '../../hooks/useTenantDateFormat'
import { formatDateTimeForDisplay } from '../../utils/dateFormat'

export default function WhatsAppMenusIndex(){
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const { dateFormat, timeZone } = useTenantDisplayPreferences()
  const { showConfirm } = useAlert()
  const [items, setItems] = useState<WhatsAppMenu[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string|null>(null)
  const [message, setMessage] = useState<string|null>(null)
  const [openNew, setOpenNew] = useState(false)
  const [newId, setNewId] = useState('default')
  const [newName, setNewName] = useState('Default')
  const navigate = useNavigate()

  async function refresh(){
    if(!tenant) return
    setLoading(true); setError(null)
    try{
      const res = await listMenus(tenant)
      setItems(res.items)
    }catch(e:any){ setError(e?.response?.data?.detail || 'Failed to load menus') }
    finally{ setLoading(false) }
  }
  useEffect(()=>{ refresh() // eslint-disable-next-line
  },[tenant])

  function create(){
    setOpenNew(true)
    setNewId('default'); setNewName('Default')
  }

  function onEdit(m: WhatsAppMenu){
    // Drafts are editable; published versions should be viewed via status/version
    if(m.status === 'published'){
      const q = `?status=published&version=${encodeURIComponent(String(m.version||''))}&tenant=${encodeURIComponent(tenant)}`
      navigate(`/whatsapp/menus/${encodeURIComponent(m.menu_id)}${q}`)
    }else{
      const q = `?tenant=${encodeURIComponent(tenant)}`
      navigate(`/whatsapp/menus/${encodeURIComponent(m.menu_id)}${q}`)
    }
  }

  async function onPublish(m: WhatsAppMenu){
    if(!tenant) return
    const ok = await showConfirm({ title: 'Publish menu', message: `Publish menu "${m.menu_id}"?` })
    if(!ok) return
    setError(null); setMessage(null)
    try{
      await publishMenu(tenant, m.menu_id)
      // After publish, if Meta Cloud provider is used and no active menu is set, suggest setting it
      try{
        const cfg = await getWhatsAppConfig(tenant)
        if(String(cfg?.provider||'')==='meta_cloud' && !String(cfg?.active_menu_id||'').trim()){
          setMessage('Menu published. Tip: set Active menu id in WhatsApp Config for Meta Cloud.')
        }else{
          setMessage('Menu published')
        }
      }catch{ setMessage('Menu published') }
      await refresh()
    }catch(e:any){ setError(e?.response?.data?.detail || 'Publish failed') }
  }

  async function onFork(m: WhatsAppMenu){
    if(!tenant) return
    if(m.status !== 'published'){ setError('Fork is only available from published versions'); return }
    setError(null); setMessage(null)
    try{
      // Load the exact published version
      const doc = await getMenu(tenant, m.menu_id, 'published', m.version || undefined)
      const payload = { menu_id: m.menu_id, name: doc.name || m.menu_id, tree: doc.tree || {} }
      await upsertMenu(tenant, payload)
      setMessage(`Draft created from v${m.version}`)
      // Navigate to edit the draft
      navigate(`/whatsapp/menus/${encodeURIComponent(m.menu_id)}?tenant=${encodeURIComponent(tenant)}`)
    }catch(e:any){ setError(String(e?.response?.data?.detail || e?.message || 'Fork failed')) }
  }

  async function onDelete(m: WhatsAppMenu){
    if(!tenant) return
    if(m.status !== 'draft'){ setError('Only draft menus can be deleted'); return }
    const typed = prompt(`Type the menu id to confirm deletion: ${m.menu_id}`)
    if(typed !== m.menu_id) return
    setError(null); setMessage(null)
    try{
      await deleteMenu(tenant, m.menu_id)
      setMessage('Draft deleted')
      await refresh()
    }catch(e:any){ setError(e?.response?.data?.detail || 'Delete failed') }
  }

  function onNewSubmit(e: React.FormEvent){
    e.preventDefault()
    if(!newId.trim()) return
    setOpenNew(false)
    navigate(`/whatsapp/menus/${encodeURIComponent(newId.trim().toLowerCase())}?name=${encodeURIComponent(newName.trim()||newId.trim())}&tenant=${encodeURIComponent(tenant)}`)
  }

  return (
    <Box sx={{ p:1 }}>
      <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems="center" justifyContent="space-between" sx={{ mb:2 }}>
        <Typography variant="h5">WhatsApp Menus</Typography>
        <Stack direction="row" spacing={1} alignItems="center">
          <Button variant="outlined" onClick={()=>navigate('/whatsapp/workflows')}>Workflows</Button>
          <Button variant="outlined" onClick={()=>navigate('/whatsapp/custom-actions')}>Custom actions</Button>
          <Button variant="outlined" onClick={()=>navigate('/whatsapp/triggers')}>Triggers</Button>
          <Button variant="contained" onClick={create} disabled={!tenant}>New Menu</Button>
        </Stack>
      </Stack>

      {error && <Alert severity='error' sx={{ mb:2 }}>{error}</Alert>}
      {message && <Alert severity='success' sx={{ mb:2 }}>{message}</Alert>}

      <Card>
        <CardContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Menu ID</TableCell>
                <TableCell>Name</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Version</TableCell>
                <TableCell>Updated</TableCell>
                <TableCell>Published</TableCell>
                <TableCell align='right'>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map(m => (
                <TableRow key={`${m.menu_id}-${m.status}-${m.version||0}`} hover>
                  <TableCell>{m.menu_id}</TableCell>
                  <TableCell>{m.name}</TableCell>
                  <TableCell>
                    <Chip size='small' label={m.status} color={m.status==='published'?'success':'default'} />
                  </TableCell>
                  <TableCell>{m.version ?? '-'}</TableCell>
                  <TableCell>{m.updated_at ? formatDateTimeForDisplay(m.updated_at, dateFormat, timeZone) : '-'}</TableCell>
                  <TableCell>{m.published_at ? formatDateTimeForDisplay(m.published_at, dateFormat, timeZone) : '-'}</TableCell>
                  <TableCell align='right'>
                    <Stack direction="row" spacing={1} justifyContent='flex-end'>
                  {m.status==='published' && <Button size='small' onClick={()=>onEdit(m)}>View</Button>}
                  {m.status==='published' && <Button size='small' onClick={()=>onFork(m)}>Fork as Draft</Button>}
                  {m.status==='draft' && <Button size='small' onClick={()=>onEdit(m)}>Edit</Button>}
                  {m.status==='draft' && <Button size='small' onClick={()=>onPublish(m)}>Publish</Button>}
                  {m.status==='draft' && <Button size='small' color='error' onClick={()=>onDelete(m)}>Delete</Button>}
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
              {!items.length && (
                <TableRow><TableCell colSpan={7}><Typography variant='body2' color='text.secondary'>{loading? 'Loading...' : 'No menus yet'}</Typography></TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={openNew} onClose={()=>setOpenNew(false)} maxWidth='sm' fullWidth>
        <DialogTitle>New Menu</DialogTitle>
        <Box component='form' onSubmit={onNewSubmit}>
          <DialogContent dividers>
            <Stack spacing={2}>
              <TextField label='Menu ID' value={newId} onChange={e=>setNewId(e.target.value)} helperText='e.g., default, promo_oct' fullWidth />
              <TextField label='Name' value={newName} onChange={e=>setNewName(e.target.value)} fullWidth />
              {tenant && (
                <Alert severity='info'>This menu will be created for tenant: <strong>{tenant}</strong></Alert>
              )}
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={()=>setOpenNew(false)}>Cancel</Button>
            <Button type='submit' variant='contained'>Create</Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Box>
  )
}
