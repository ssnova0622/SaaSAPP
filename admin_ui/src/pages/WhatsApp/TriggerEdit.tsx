import { useEffect, useState } from 'react'
import { Alert, Box, Button, Card, CardContent, Grid, Stack, Switch, TextField, Typography, MenuItem } from '@mui/material'
import { useNavigate, useParams } from 'react-router-dom'
import { createTrigger, updateTrigger, listMenus, getMenu, getTrigger, listAvailableActions } from '../../api/whatsapp'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'

type MatchType = 'exact' | 'prefix' | 'contains' | 'regex'
type ActionKind = 'render_submenu' | 'jump_node' | 'static_text' | 'invoke_action'

export default function TriggerEdit(){
  const { id } = useParams()
  const isNew = !id || id === 'new'
  const navigate = useNavigate()
  const { effectiveTenant: tenant, ready } = useEffectiveTenant()

  const [triggerId, setTriggerId] = useState(id && id !== 'new' ? id : '')
  const [enabled, setEnabled] = useState(true)
  const [priority, setPriority] = useState<number>(100)
  const [matchType, setMatchType] = useState<MatchType>('exact')
  const [matchValue, setMatchValue] = useState('')
  const [matchLocale, setMatchLocale] = useState('')
  const [actionKind, setActionKind] = useState<ActionKind>('render_submenu')
  const [actionMenuId, setActionMenuId] = useState('default')
  const [actionNodeId, setActionNodeId] = useState('')
  const [actionText, setActionText] = useState('')
  const [actionId, setActionId] = useState('')
  const [error, setError] = useState<string|null>(null)
  const [message, setMessage] = useState<string|null>(null)
  const [menuIds, setMenuIds] = useState<string[]>([])
  const [nodeIds, setNodeIds] = useState<{ id: string; type: string }[]>([])
  const [availableActions, setAvailableActions] = useState<{ id: string; label: string }[]>([])
  const [loadingMenus, setLoadingMenus] = useState(false)
  const [loadingNodes, setLoadingNodes] = useState(false)
  const [loadingActions, setLoadingActions] = useState(false)
  const [loadingTrigger, setLoadingTrigger] = useState(false)

  // Wait for effective tenant to be ready; no additional setup required here

  // Load available menus for the tenant
  useEffect(()=>{
    (async()=>{
      if(!ready || !tenant) return
      setLoadingMenus(true)
      setError(null)
      try{
        const res = await listMenus(tenant)
        // unique menu ids from items
        const ids = Array.from(new Set((res.items||[]).map(m=>m.menu_id))).sort()
        setMenuIds(ids)
        // If current actionMenuId is not in list, pick a sensible default
        if(ids.length){
          if(!ids.includes(actionMenuId)){
            const preferred = ids.includes('default') ? 'default' : ids[0]
            setActionMenuId(preferred)
          }
        }
      }catch(e:any){
        const d = e?.response?.data?.detail
        let msg = 'Failed to load menus'
        if (typeof d === 'string') msg = d
        else if (Array.isArray(d) && d.length) msg = d[0]?.msg || JSON.stringify(d[0])
        else if (d && typeof d === 'object') msg = d.msg || JSON.stringify(d)
        else if (e?.message) msg = e.message
        setError(String(msg))
      }finally{
        setLoadingMenus(false)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[tenant, ready])

  // Load valid actions for tenant (for invoke_action)
  useEffect(()=>{
    (async()=>{
      if(!ready || !tenant) return
      setLoadingActions(true)
      try{
        const items = await listAvailableActions(tenant)
        setAvailableActions((items || []).map(a=> ({ id: a.id, label: a.label || a.id })))
      }catch{
        setAvailableActions([])
      }finally{
        setLoadingActions(false)
      }
    })()
  },[tenant, ready])

  // Load nodes when menu changes (prefer published, fallback to draft)
  useEffect(()=>{
    (async()=>{
      if(!tenant || !actionMenuId) { setNodeIds([]); return }
      setLoadingNodes(true)
      try{
        let menuDoc: any | null = null
        try{
          menuDoc = await getMenu(tenant, actionMenuId, 'published')
        }catch{
          // ignore; try draft/default get
        }
        if(!menuDoc){
          try{ menuDoc = await getMenu(tenant, actionMenuId) }catch{ /* ignore */ }
        }
        const nodes = (menuDoc?.tree?.nodes || []) as Array<any>
        const options = nodes
          .filter((n)=> typeof n?.id === 'string' && !!n.id)
          .map((n)=> ({ id: String(n.id), type: String(n.type||'') }))
        setNodeIds(options)
        if(actionNodeId && !options.find(o=>o.id===actionNodeId)){
          setActionNodeId('')
        }
      }finally{
        setLoadingNodes(false)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[tenant, actionMenuId])

  // Load existing trigger when editing
  useEffect(()=>{
    (async()=>{
      if(!ready || !tenant) return
      if(isNew || !id) return
      setLoadingTrigger(true)
      setError(null)
      try{
        const trig = await getTrigger(tenant, id)
        setTriggerId(trig.trigger_id || '')
        setEnabled(!!trig.enabled)
        setPriority(Number(trig.priority ?? 100))
        const mt = (trig.match?.type as MatchType) || 'exact'
        setMatchType(mt)
        const mv = trig.match?.value as any
        // Convert array or string to a CSV string for the input control
        let mvStr = ''
        if (Array.isArray(mv)) mvStr = mv.join(', ')
        else if (typeof mv === 'string') mvStr = mv
        setMatchValue(mvStr)
        setMatchLocale(String(trig.match?.locale || ''))
        const ak = (trig.action?.kind as ActionKind) || 'render_submenu'
        setActionKind(ak)
        // For non-static actions, load menu/node if present
        const mid = (trig.action as any)?.menu_id || 'default'
        setActionMenuId(mid)
        const nid = (trig.action as any)?.node_id || ''
        setActionNodeId(nid)
        const aid = (trig.action as any)?.action_id || ''
        setActionId(aid)
      }catch(e:any){
        // Leave defaults; show a warning but allow creating a new trigger with this id
        const d = e?.response?.data?.detail
        let msg = 'Failed to load trigger'
        if (typeof d === 'string') msg = d
        else if (Array.isArray(d) && d.length) msg = d[0]?.msg || JSON.stringify(d[0])
        else if (d && typeof d === 'object') msg = d.msg || JSON.stringify(d)
        else if (e?.message) msg = e.message
        setError(String(msg))
      }finally{
        setLoadingTrigger(false)
      }
    })()
  },[ready, tenant, isNew, id])

  function validate(): string | null{
    if(!tenant) return 'No tenant available'
    if(!triggerId.trim()) return 'Trigger ID is required'
    if(!matchValue.trim()) return 'Match value is required'
    if(actionKind === 'static_text' && !actionText.trim()) return 'Text is required for static_text'
    if(actionKind !== 'static_text' && actionKind !== 'invoke_action' && !actionMenuId.trim()) return 'Menu is required for this action'
    if(actionKind === 'jump_node' && !actionNodeId.trim()) return 'node_id is required for jump_node'
    if(actionKind === 'invoke_action' && !actionId.trim()) return 'Select a valid action for this tenant'
    return null
  }

  async function onSave(){
    setError(null); setMessage(null)
    const v = validate()
    if(v){ setError(v); return }
    // Prepare match.value — split CSV into array for non-regex types
    const matchVal = (()=>{
      if (matchType === 'regex') return matchValue.trim()
      const parts = matchValue
        .split(',')
        .map(s=>s.trim())
        .filter(Boolean)
      return parts
    })()

    const payload: any = {
      trigger_id: triggerId.trim(),
      match: { type: matchType, value: matchVal as any, ...(matchLocale.trim()? { locale: matchLocale.trim() }: {}) },
      action: (()=>{
        if(actionKind === 'static_text') return { kind: actionKind, text: actionText }
        if(actionKind === 'invoke_action' && actionId.trim())
          return { kind: actionKind, action_id: actionId.trim() }
        const base = { kind: actionKind, menu_id: actionMenuId || 'default' }
        if(actionNodeId) (base as any).node_id = actionNodeId
        return base
      })(),
      enabled: !!enabled,
      priority: Number.isFinite(priority) ? priority : 0,
    }
    try{
      if(isNew){
        await createTrigger(tenant, payload)
        setMessage('Created')
        navigate('/whatsapp/triggers')
      }else{
        await updateTrigger(tenant, triggerId, payload)
        setMessage('Saved')
        navigate('/whatsapp/triggers')
      }
    }catch(e:any){
      const d = e?.response?.data?.detail
      let msg = 'Save failed'
      if (typeof d === 'string') msg = d
      else if (Array.isArray(d) && d.length) msg = d[0]?.msg || JSON.stringify(d[0])
      else if (d && typeof d === 'object') msg = d.msg || JSON.stringify(d)
      else if (e?.message) msg = e.message
      setError(String(msg))
    }
  }

  return (
    <Box sx={{ p:1 }}>
      <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems="center" justifyContent="space-between" sx={{ mb:2 }}>
        <Typography variant="h5">{isNew? 'New Trigger' : `Edit Trigger: ${id}`}</Typography>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" onClick={()=>navigate('/whatsapp/triggers')}>Back</Button>
          <Button variant="contained" onClick={onSave} disabled={!tenant || !ready}>Save</Button>
        </Stack>
      </Stack>

      {(!tenant && ready) && <Alert severity='warning' sx={{ mb:2 }}>No tenants available. Please create a tenant first.</Alert>}
      {error && <Alert severity='error' sx={{ mb:2 }}>{error}</Alert>}
      {message && <Alert severity='success' sx={{ mb:2 }}>{message}</Alert>}

      <Card>
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField label="Trigger ID" value={triggerId} onChange={e=>setTriggerId(e.target.value)} fullWidth disabled={!isNew} helperText={isNew? 'Unique id (e.g., greeting-hi, book-shortcut)' : 'ID cannot be changed'} />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField label="Priority" type="number" value={priority} onChange={e=>setPriority(parseInt(e.target.value||'0',10))} fullWidth />
            </Grid>
            <Grid item xs={12} md={3} sx={{ display:'flex', alignItems:'center' }}>
              <Stack direction='row' spacing={1} alignItems='center'>
                <Typography>Enabled</Typography>
                <Switch checked={enabled} onChange={e=>setEnabled(e.target.checked)} />
              </Stack>
            </Grid>

            <Grid item xs={12} md={3}>
              <TextField select label="Match Type" value={matchType} onChange={e=>setMatchType(e.target.value as MatchType)} fullWidth>
                <MenuItem value='exact'>exact</MenuItem>
                <MenuItem value='prefix'>prefix</MenuItem>
                <MenuItem value='contains'>contains</MenuItem>
                <MenuItem value='regex'>regex</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField label="Match Value" value={matchValue} onChange={e=>setMatchValue(e.target.value)} fullWidth placeholder="hi | book | enquiry" />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField label="Locale (optional)" value={matchLocale} onChange={e=>setMatchLocale(e.target.value)} fullWidth placeholder="en | ta" />
            </Grid>

            <Grid item xs={12} md={4}>
              <TextField select label="Action Kind" value={actionKind} onChange={e=>setActionKind(e.target.value as ActionKind)} fullWidth>
                <MenuItem value='render_submenu'>render_submenu</MenuItem>
                <MenuItem value='jump_node'>jump_node</MenuItem>
                <MenuItem value='static_text'>static_text</MenuItem>
                <MenuItem value='invoke_action'>invoke_action</MenuItem>
              </TextField>
            </Grid>
            {actionKind === 'invoke_action' && (
              <Grid item xs={12} md={8}>
                <TextField select label="Action (valid for this tenant)" value={actionId} onChange={e=>setActionId(e.target.value)} fullWidth disabled={loadingActions} helperText={loadingActions ? 'Loading…' : (availableActions.length ? 'Choose the action to run when this trigger matches.' : 'No actions available for this tenant.')}>
                  <MenuItem value="">— Select action —</MenuItem>
                  {availableActions.map(a => (
                    <MenuItem key={a.id} value={a.id}>{a.label} ({a.id})</MenuItem>
                  ))}
                </TextField>
              </Grid>
            )}
            <Grid item xs={12} md={4}>
              <TextField select label="Menu" value={actionMenuId} onChange={e=>setActionMenuId(e.target.value)} fullWidth disabled={actionKind==='static_text' || loadingMenus} helperText={!menuIds.length ? 'No menus found. Create one in WhatsApp → Menus.' : ''}>
                {menuIds.map(mid => (
                  <MenuItem key={mid} value={mid}>{mid}</MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField select label="Node (from selected menu)" value={actionNodeId} onChange={e=>setActionNodeId(e.target.value)} fullWidth disabled={actionKind==='render_submenu' || actionKind==='static_text' || (actionKind==='invoke_action' && !!actionId) || loadingNodes} helperText={(actionKind==='render_submenu' || actionKind==='static_text') ? 'Node not required' : actionKind==='invoke_action' && actionId ? 'Using Action ID; node optional.' : 'Required for jump_node; optional for invoke_action (legacy).'}>
                {nodeIds.map(n => (
                  <MenuItem key={n.id} value={n.id}>{n.id} {n.type? `(${n.type})` : ''}</MenuItem>
                ))}
              </TextField>
            </Grid>
            {actionKind==='static_text' && (
              <Grid item xs={12}>
                <TextField label="Text" value={actionText} onChange={e=>setActionText(e.target.value)} fullWidth multiline minRows={3} placeholder="Reply text to send" />
              </Grid>
            )}
          </Grid>
        </CardContent>
      </Card>
    </Box>
  )
}
