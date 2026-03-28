import { useEffect, useMemo, useState } from 'react'
import { Box, Button, Card, CardContent, Grid, Stack, TextField, Typography, Alert, Divider, MenuItem, Switch, FormControlLabel, IconButton, Chip, ListSubheader, InputAdornment } from '@mui/material'
import { useAlert } from '@contexts/AlertContext'
import DeleteIcon from '@mui/icons-material/Delete'
import AddIcon from '@mui/icons-material/Add'
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward'
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { getMenu, upsertMenu, publishMenu } from '@api/whatsapp'
import { listWorkflows } from '@api/workflows'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { TEMPLATE_SALON, TEMPLATE_CLINIC, TEMPLATE_STORE, STARTER_EMPTY } from './templates'

export default function WhatsAppMenuEditor(){
  const { id = 'default' } = useParams()
  const [searchParams] = useSearchParams()
  const { effectiveTenant: tenantFromHook, setEffectiveTenant } = useEffectiveTenant()
  const tenant = tenantFromHook || ''
  const { showAlert, showConfirm } = useAlert()
  const [error, setError] = useState<string|null>(null)
  const [message, setMessage] = useState<string|null>(null)
  const [name, setName] = useState<string>('')
  // Visual builder state
  const [tree, setTree] = useState<any>({ root:'root', nodes:[{ id:'root', type:'submenu', title:'Welcome', prompt:'Choose:', options:[] }] })
  const [selectedNodeId, setSelectedNodeId] = useState<string>('root')
  const [visualMode, setVisualMode] = useState<boolean>(true)
  const [treeText, setTreeText] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<'draft'|'published'|''>('')
  const [version, setVersion] = useState<number|undefined>(undefined)
  const [readOnly, setReadOnly] = useState<boolean>(false)
  const [preview, setPreview] = useState<string>('')
  const [workflows, setWorkflows] = useState<Array<{ workflow_id: string; name: string }>>([])
  const [actionSearch, setActionSearch] = useState('')
  const navigate = useNavigate()
  const filteredActions: Array<{ id: string; label: string; module: string }> = []
  const actionsByModule = useMemo(() => [{ module: 'workflow', actions: filteredActions }], [])
  const moduleLabel = (mod: string) => mod === 'workflow' ? 'Workflow' : mod

  // Sync tenant from URL (?tenant=) to effective tenant when present (e.g. deep link from Menus list)
  useEffect(() => {
    const tFromQuery = searchParams.get('tenant') || ''
    if (tFromQuery && tFromQuery !== tenantFromHook) setEffectiveTenant(tFromQuery)
  }, [searchParams, tenantFromHook, setEffectiveTenant])

  useEffect(()=>{
    // On first open, seed name from query if provided
    const qn = searchParams.get('name')
    if(qn) setName(qn)
  }, [searchParams])

  // Load workflows for tenant (assign workflow to each menu option)
  useEffect(() => {
    (async () => {
      if (!tenant) return
      try {
        const { items } = await listWorkflows(tenant)
        setWorkflows(items || [])
      } catch {
        setWorkflows([])
      }
    })()
  }, [tenant])

  async function load(){
    if(!tenant || !id) return
    setLoading(true); setError(null); setMessage(null)
    try{
      const qStatus = (searchParams.get('status')||'').toLowerCase()
      const qVersionRaw = searchParams.get('version')
      const qVersion = qVersionRaw && !isNaN(Number(qVersionRaw)) ? Number(qVersionRaw) : undefined
      let m: any
      if(qStatus === 'published'){
        m = await getMenu(tenant, id, 'published', qVersion)
      }else if(qStatus === 'draft'){
        m = await getMenu(tenant, id, 'draft')
      }else{
        m = await getMenu(tenant, id)
      }
      setName(m.name || id)
      setStatus(m.status || 'draft')
      setVersion(m.version)
      const t = m.tree || { root:'root', nodes: [ { id:'root', type:'submenu', title:'Welcome', prompt:'Choose:', options:[] } ] }
      setTree(t)
      setSelectedNodeId(t.root || 'root')
      setTreeText(JSON.stringify(t, null, 2))
      // Determine read-only: published with explicit version OR with status=published in query
      const ro = (m.status === 'published') && (qStatus === 'published')
      setReadOnly(!!ro)
    }catch(e:any){
      // If not found, create a basic skeleton
      setStatus('draft'); setVersion(undefined); setReadOnly(false)
      const t = { root:'root', nodes:[{ id:'root', type:'submenu', title:'Welcome', prompt:'Choose:', options:[] }] }
      setTree(t)
      setSelectedNodeId('root')
      setTreeText(JSON.stringify(t, null, 2))
    }finally{ setLoading(false) }
  }
  useEffect(()=>{ load() // eslint-disable-next-line
  },[tenant, id, searchParams])

  async function saveDraft(){
    if(readOnly){ setError('This is a published version (read-only). Use "Fork as Draft" to edit.'); return }
    if(!tenant || !id){ setError('Please select a tenant before saving'); return }
    setError(null); setMessage(null)
    const parsed: any = visualMode ? tree : safeParseTree(treeText)
    if (!parsed){ setError('Invalid JSON in menu tree'); return }
    const v = validateTree(parsed)
    if(!v.ok){ setError('Validation failed: ' + v.error); return }
    try{
      await upsertMenu(tenant, { menu_id: id, name: name || id, tree: parsed })
      setMessage('Draft saved')
      await load()
    }catch(e:any){
      const d = e?.response?.data?.detail
      let msg = 'Save failed'
      if (typeof d === 'string') msg = d
      else if (Array.isArray(d) && d.length) msg = d[0]?.msg || JSON.stringify(d[0])
      else if (d && typeof d === 'object') msg = d.msg || JSON.stringify(d)
      else if (e?.message) msg = e.message
      setError(msg)
    }
  }

  async function onPublish(){
    if(readOnly){ setError('This is a published version (read-only). Use "Fork as Draft" to create a draft and publish.'); return }
    if(!tenant || !id){ setError('Please select a tenant before publishing'); return }
    const ok = await showConfirm({ title: 'Publish menu', message: `Publish menu "${id}"?` })
    if(!ok) return
    setError(null); setMessage(null)
    // validate before publish
    const parsed: any = visualMode ? tree : safeParseTree(treeText)
    if (!parsed){ setError('Invalid JSON in menu tree'); return }
    const v = validateTree(parsed)
    if(!v.ok){ setError('Validation failed: ' + v.error); return }
    try{
      await publishMenu(tenant, id)
      setMessage('Published')
      await load()
    }catch(e:any){ setError(e?.response?.data?.detail || 'Publish failed') }
  }

  async function onForkFromPublished(){
    if(!tenant || !id){ setError('Please select a tenant'); return }
    try{
      await upsertMenu(tenant, { menu_id: id, name: name || id, tree })
      setMessage('Draft created from this version')
      // Remove status/version from URL and reload draft
      const params = new URLSearchParams(searchParams)
      params.delete('status'); params.delete('version')
      navigate(`/whatsapp/menus/${encodeURIComponent(id)}${params.toString()?`?${params.toString()}`:''}`)
    }catch(e:any){
      const d = e?.response?.data?.detail
      let msg = 'Fork failed'
      if (typeof d === 'string') msg = d
      else if (Array.isArray(d) && d.length) msg = d[0]?.msg || JSON.stringify(d[0])
      else if (d && typeof d === 'object') msg = d.msg || JSON.stringify(d)
      else if (e?.message) msg = e.message
      setError(msg)
    }
  }

  // ---- Client-side helpers ----
  type ValidationResult = { ok: true } | { ok: false; error: string }
  function validateTree(tree: any): ValidationResult {
    if (!tree || typeof tree !== 'object') return { ok: false, error: 'tree must be an object' }
    const root = tree.root
    const nodes = Array.isArray(tree.nodes) ? tree.nodes : []
    if (!root || typeof root !== 'string') return { ok: false, error: 'tree.root is required' }
    if (!nodes.length) return { ok: false, error: 'tree.nodes must be a non-empty array' }
    const ids = nodes.map((n:any)=>n?.id)
    if (new Set(ids).size !== ids.length) return { ok: false, error: 'Duplicate node ids' }
    if (!ids.includes(root)) return { ok: false, error: 'tree.root must reference an existing node id' }
    // submenu option keys unique & next references valid
    const idSet = new Set(ids)
    for (const n of nodes){
      if (!n || typeof n !== 'object') return { ok: false, error: 'Each node must be an object' }
      if (!n.id) return { ok: false, error: 'Node missing id' }
      if (n.type === 'submenu'){
        const opts = Array.isArray(n.options) ? n.options : []
        const keys = opts.map((o:any)=>String(o?.key))
        if (new Set(keys).size !== keys.length) return { ok: false, error: `Duplicate option keys in submenu '${n.id}'` }
        for (const o of opts) {
          if (!o?.next) continue
          if (idSet.has(o.next)) continue
          if (typeof o.next === 'string' && o.next.trim().startsWith('workflow.')) continue
          return { ok: false, error: `Option in '${n.id}' points to missing node or invalid workflow '${o.next}'` }
        }
      } else if (n.type === 'action'){
        // nothing extra for now
      } else {
        return { ok: false, error: `Unsupported node.type for '${n.id}'` }
      }
    }
    // Optional: depth check (simple DFS from root)
    const graph: Record<string, string[]> = {}
    for (const n of nodes){
      if (n.type === 'submenu'){
        graph[n.id] = (n.options||[]).map((o:any)=>o?.next).filter((next: any)=> next && idSet.has(next))
      }
    }
    let maxDepth = 0
    const seen = new Set<string>()
    function dfs(id:string, d:number){
      if (d>20){ maxDepth = d; return } // hard cap to avoid cycles
      maxDepth = Math.max(maxDepth, d)
      seen.add(id)
      for (const nxt of (graph[id]||[])){
        if (!seen.has(nxt)) dfs(nxt, d+1)
      }
    }
    dfs(root, 1)
    if (maxDepth > 6) return { ok: false, error: 'Menu depth exceeds 6 levels' }
    return { ok: true }
  }

  function safeParseTree(txt: string){
    try{ return JSON.parse(txt) }catch{ return null }
  }

  function renderPreview(): void {
    try{
      const t = visualMode ? tree : JSON.parse(treeText)
      const rootId = t.root
      const nodes = Array.isArray(t.nodes)? t.nodes : []
      const findNode = (nid:string)=> nodes.find((n:any)=>n.id===nid)
      const node = findNode(rootId)
      if (!node){ setPreview('Invalid: root node missing'); return }
      if (node.type === 'submenu'){
        const title = node.title || ''
        const prompt = node.prompt || 'Please choose an option:'
        const lines: string[] = []
        if (title) lines.push(String(title))
        lines.push(String(prompt))
        for (const o of (node.options||[])){
          lines.push(`${o.key}) ${o.label || o.title || 'Option'}`)
        }
        lines.push('Reply with a number.')
        setPreview(lines.join('\n'))
      } else {
        setPreview(node.title || node.label || 'Processing...')
      }
    }catch{
      setPreview('Invalid JSON — cannot render preview')
    }
  }

  useEffect(()=>{ renderPreview() // eslint-disable-next-line
  }, [treeText, tree, visualMode])

  function importTemplate(kind: 'salon' | 'clinic' | 'store' | 'empty'){
    const t = kind === 'salon' ? TEMPLATE_SALON
      : kind === 'clinic' ? TEMPLATE_CLINIC
      : kind === 'store' ? TEMPLATE_STORE
      : STARTER_EMPTY
    setTree(t)
    setSelectedNodeId(t.root || 'root')
    setTreeText(JSON.stringify(t, null, 2))
    setMessage('Template loaded — remember to Save Draft')
  }

  // ---------- Visual builder helpers ----------
  const nodeIds: string[] = useMemo(()=> (Array.isArray(tree?.nodes)? tree.nodes.map((n:any)=>String(n.id)):[]), [tree])
  function addNode(type: 'submenu'|'action'){
    const base = type === 'submenu' ? 'submenu' : 'action'
    let idx = 1
    let nid = `${base}_${idx}`
    while(nodeIds.includes(nid)){ idx += 1; nid = `${base}_${idx}` }
    const nn = type === 'submenu'
      ? { id: nid, type:'submenu', title:'', prompt:'Choose:', options:[] as any[] }
      : { id: nid, type:'action', action:'open_ticket', title:'', params:{}, requires_caps: [] as string[] }
    const nodes = [...(tree.nodes||[]), nn]
    const nt = { ...tree, nodes }
    setTree(nt)
    setSelectedNodeId(nid)
  }
  function deleteNode(nid: string){
    if(nid === tree.root){ showAlert('Cannot delete root node', 'warning'); return }
    // Check inbound references from other submenu options
    const inbound = (tree.nodes||[]).filter((n:any)=> n.type==='submenu' && (n.options||[]).some((o:any)=> o.next===nid))
    if(inbound.length){
      const typed = prompt(`Node '${nid}' is referenced by ${inbound.length} node(s). Type the node id to confirm delete:`)
      if(typed !== nid) return
    }
    const nodes = (tree.nodes||[]).filter((n:any)=>n.id!==nid)
    // Remove references from submenu options
    for(const n of nodes){ if(n.type==='submenu'){ n.options = (n.options||[]).map((o:any)=> o.next===nid? {...o, next: undefined }: o) } }
    const nt = { ...tree, nodes }
    setTree(nt)
    if(selectedNodeId===nid) setSelectedNodeId(nt.root)
  }
  function updateNode(nid: string, patch: any){
    setTree(prev => {
      const nodes = (prev.nodes||[]).map((n:any)=> n.id===nid ? { ...n, ...patch } : n)
      return { ...prev, nodes }
    })
  }
  function renameNode(nid: string, newId: string){
    newId = newId.trim()
    if(!newId || nodeIds.includes(newId)) return
    const nodes = (tree.nodes||[]).map((n:any)=> n.id===nid ? { ...n, id:newId } : n)
    // Update references
    for(const n of nodes){ if(n.type==='submenu'){ n.options = (n.options||[]).map((o:any)=> o.next===nid? { ...o, next:newId } : o) } }
    const root = (tree.root===nid) ? newId : tree.root
    setTree({ ...tree, nodes, root })
    if(selectedNodeId===nid) setSelectedNodeId(newId)
  }
  function addOption(nid: string){
    const n = (tree.nodes||[]).find((x:any)=>x.id===nid)
    if(!n || n.type!=='submenu') return
    const opts = [...(n.options||[])]
    let k = 1
    const keys = new Set(opts.map((o:any)=>String(o.key)))
    while(keys.has(String(k))){ k += 1 }
    opts.push({ key:String(k), label:'Option', next: undefined })
    updateNode(nid, { options: opts })
  }
  function removeOption(nid: string, idx: number){
    const n = (tree.nodes||[]).find((x:any)=>x.id===nid)
    if(!n || n.type!=='submenu') return
    const opts = [...(n.options||[])]
    opts.splice(idx,1)
    updateNode(nid, { options: opts })
  }
  function moveOption(nid: string, idx: number, dir: -1|1){
    const n = (tree.nodes||[]).find((x:any)=>x.id===nid)
    if(!n || n.type!=='submenu') return
    const opts = [...(n.options||[])]
    const ni = idx + dir
    if(ni<0 || ni>=opts.length) return
    const tmp = opts[idx]
    opts[idx] = opts[ni]
    opts[ni] = tmp
    updateNode(nid, { options: opts })
  }
  function setRoot(nid: string){
    setTree({ ...tree, root: nid })
  }

  return (
    <Box sx={{ p:1 }}>
      <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems="center" justifyContent="space-between" sx={{ mb:2 }}>
        <Typography variant="h5">Edit Menu: {id}</Typography>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" onClick={()=>navigate('/whatsapp')}>Back</Button>
          {!readOnly && <Button variant="outlined" onClick={saveDraft}>Save Draft</Button>}
          {!readOnly && <Button variant="contained" onClick={onPublish}>Publish</Button>}
          {readOnly && <Button variant="contained" onClick={onForkFromPublished}>Fork as Draft</Button>}
        </Stack>
      </Stack>

      {readOnly && (
        <Alert severity='info' sx={{ mb:2 }}>Viewing published version {typeof version==='number'?`v${version}`:''} (read-only). Use "Fork as Draft" to make changes.</Alert>
      )}
      {(!tenant) && (
        <Alert severity='warning' sx={{ mb:2 }}>Select a tenant to create or edit a WhatsApp menu.</Alert>
      )}
      {error && <Alert severity='error' sx={{ mb:2 }}>{error}</Alert>}
      {message && <Alert severity='success' sx={{ mb:2 }}>{message}</Alert>}

      <Card>
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField fullWidth label='Name' value={name} onChange={e=>setName(e.target.value)} />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField fullWidth label='Status' value={status} disabled />
            </Grid>
            <Grid item xs={12} md={2}>
              <FormControlLabel control={<Switch checked={visualMode} onChange={e=>setVisualMode(e.target.checked)} />} label="Visual mode" />
            </Grid>

            {/* Templates - removed to simplify */}
            {/* <Grid item xs={12}>
              <Stack direction={{ xs:'column', md:'row' }} spacing={1} alignItems='center'>
                <Typography variant='subtitle2' sx={{ mr: 1 }}>Templates:</Typography>
                <Button size='small' onClick={()=>importTemplate('salon')}>Salon</Button>
                <Button size='small' onClick={()=>importTemplate('clinic')}>Clinic</Button>
                <Button size='small' onClick={()=>importTemplate('store')}>Store</Button>
                <Button size='small' onClick={()=>importTemplate('empty')}>Empty</Button>
              </Stack>
            </Grid> */}

            {/* Visual Builder or JSON editor */}
            {visualMode ? (
              <>
                <Grid item xs={12} md={3}>
                  <Typography variant='subtitle2' sx={{ mb:1 }}>Nodes</Typography>
                  <Stack spacing={1}>
                    <TextField select size='small' label='Root' value={tree.root} onChange={e=>setRoot(e.target.value)}>
                      {nodeIds.map(n=> (<MenuItem key={n} value={n}>{n}</MenuItem>))}
                    </TextField>
                    <Button size='small' startIcon={<AddIcon/>} onClick={()=>addNode('submenu')}>Add submenu</Button>
                    <Divider/>
                    <Stack spacing={0.5}>
                      {(tree.nodes||[]).map((n:any)=> (
                        <Stack key={n.id} direction='row' spacing={1} alignItems='center'>
                          <Button size='small' variant={selectedNodeId===n.id? 'contained':'outlined'} onClick={()=>setSelectedNodeId(n.id)} sx={{ textTransform:'none' }}>{n.id}</Button>
                          <Chip size='small' label={n.type} />
                          {n.id!==tree.root && (
                            <IconButton size='small' onClick={()=>deleteNode(n.id)} aria-label='delete'><DeleteIcon fontSize='small'/></IconButton>
                          )}
                        </Stack>
                      ))}
                    </Stack>
                  </Stack>
                </Grid>
                <Grid item xs={12} md={9}>
                  <Typography variant='subtitle2' sx={{ mb:1 }}>Inspector</Typography>
                  {(() => {
                    const node = (tree.nodes||[]).find((n:any)=>n.id===selectedNodeId)
                    if(!node) return <Typography variant='body2' color='text.secondary'>Select a node to edit</Typography>
                    if(node.type==='submenu'){
                      return (
                        <Stack spacing={2}>
                          <TextField label='Node id' value={node.id} onChange={e=>renameNode(node.id, e.target.value)} />
                          <TextField label='Title (menu header)' value={node.title||''} onChange={e=>updateNode(node.id,{ title:e.target.value })} helperText="Sent as the bold header of the menu" />
                          <TextField label='Prompt' value={node.prompt||''} onChange={e=>updateNode(node.id,{ prompt:e.target.value })} helperText="The instruction text (e.g., 'Choose an option')" />
                          <Divider/>
                          <Typography variant='subtitle2'>Options</Typography>
                          <Stack spacing={1}>
                            {(node.options||[]).map((o:any, idx:number)=> (
                              <Stack key={idx} direction={{ xs:'column', md:'row' }} spacing={1} alignItems='center'>
                                <TextField size='small' label='Key' value={o.key} onChange={e=>{
                                  const opts=[...(node.options||[])]; opts[idx] = { ...o, key: e.target.value }; updateNode(node.id,{ options: opts })
                                }} sx={{ width: 90 }} />
                                <TextField size='small' label='Label' value={o.label||''} onChange={e=>{ const opts=[...(node.options||[])]; opts[idx] = { ...o, label: e.target.value }; updateNode(node.id,{ options: opts }) }} />
                                <TextField select size='small' label='Next' value={o.next||''} onChange={e=>{ const opts=[...(node.options||[])]; opts[idx] = { ...o, next: e.target.value||undefined }; updateNode(node.id,{ options: opts }) }} sx={{ minWidth: 200 }}>
                                  <MenuItem value=''>—</MenuItem>
                                  <ListSubheader>Submenus</ListSubheader>
                                  {(tree.nodes||[]).filter((n:any)=>n.type==='submenu').map((n:any)=> (
                                    <MenuItem key={n.id} value={n.id}>{n.id}</MenuItem>
                                  ))}
                                  {workflows.length > 0 && <ListSubheader>Workflows</ListSubheader>}
                                  {workflows.map(w=> (
                                    <MenuItem key={w.workflow_id} value={`workflow.${w.workflow_id}`}>{w.name || w.workflow_id}</MenuItem>
                                  ))}
                                </TextField>
                                <IconButton size='small' onClick={()=>moveOption(node.id, idx, -1)}><ArrowUpwardIcon fontSize='small' /></IconButton>
                                <IconButton size='small' onClick={()=>moveOption(node.id, idx, +1)}><ArrowDownwardIcon fontSize='small' /></IconButton>
                                <IconButton size='small' color='error' onClick={()=>removeOption(node.id, idx)}><DeleteIcon fontSize='small' /></IconButton>
                              </Stack>
                            ))}
                            <Button size='small' startIcon={<AddIcon/>} onClick={()=>addOption(node.id)}>Add option</Button>
                          </Stack>
                        </Stack>
                      )
                    }
                    // action
                    return (
                      <Stack spacing={2}>
                        <TextField label='Node id' value={node.id} onChange={e=>renameNode(node.id, e.target.value)} />
                        <TextField label='Title (reply text)' value={node.title||''} onChange={e=>updateNode(node.id,{ title:e.target.value })} helperText="Text sent to user when this action is triggered" />
                        <TextField
                          size='small'
                          placeholder='Search actions by name or id...'
                          value={actionSearch}
                          onChange={e=>setActionSearch(e.target.value)}
                          InputProps={{ startAdornment: <InputAdornment position='start'>🔍</InputAdornment> }}
                        />
                        <Box>
                          <Typography component='label' variant='body2' color='text.secondary' sx={{ display: 'block', mb: 0.5 }}>
                            Action type
                          </Typography>
                          <Box
                            component='select'
                            value={node.action || node.action_id || 'core.open_ticket'}
                            onChange={e => {
                              const v = (e.target as HTMLSelectElement).value
                              updateNode(node.id, { action: v, action_id: v })
                            }}
                            sx={{
                              width: '100%',
                              minHeight: 40,
                              px: 1.5,
                              py: 1,
                              fontSize: '0.875rem',
                              fontFamily: 'inherit',
                              color: 'text.primary',
                              bgcolor: 'background.paper',
                              border: '1px solid',
                              borderColor: 'divider',
                              borderRadius: 1,
                              '&:focus': { outline: 'none', borderColor: 'primary.main' },
                            }}
                          >
                            {(() => {
                              const currentVal = node.action || node.action_id || 'core.open_ticket'
                              const inList = filteredActions.some(a => a.id === currentVal)
                              return (
                                <>
                                  {!inList && currentVal && <option value={currentVal}>{currentVal} (current)</option>}
                                  {actionsByModule.map(({ module: mod, actions: list }) => (
                                    <optgroup key={mod} label={moduleLabel(mod)}>
                                      {list.map(a => (
                                        <option key={a.id} value={a.id}>{a.label} ({a.id})</option>
                                      ))}
                                    </optgroup>
                                  ))}
                                </>
                              )
                            })()}
                          </Box>
                          <Typography variant='caption' color='text.secondary' sx={{ display: 'block', mt: 0.5 }}>
                            Only actions for this tenant’s modules are shown
                          </Typography>
                        </Box>
                        {/* Remove Params and Capabilities to keep it simple as requested */}
                        {/* <TextField label='Params (JSON)' multiline minRows={4} value={JSON.stringify(node.params||{}, null, 2)} onChange={e=>{
                          try{ const v = JSON.parse(e.target.value); updateNode(node.id,{ params: v }) }catch{  }
                        }} /> */}
                      </Stack>
                    )
                  })()}
                </Grid>
                {/* Visual mode right side (Preview & Validation) - Hidden to keep it simple */}
                {/* <Grid item xs={12} md={4}>
                  <Typography variant='subtitle2' sx={{ mb:1 }}>Live Preview</Typography>
                  <Box sx={{ p: 2, bgcolor: '#fafafa', border: '1px solid #eee', borderRadius: 1, whiteSpace: 'pre-wrap', fontFamily: 'monospace', minHeight: '320px' }}>
                    {preview || '—'}
                  </Box>
                  <Box sx={{ mt:2 }}>
                    ...
                  </Box>
                </Grid> */}
              </>
            ) : (
              <>
                <Grid item xs={12}>
                  <TextField fullWidth multiline minRows={20} label='Menu Tree (JSON)' value={treeText} onChange={e=>setTreeText(e.target.value)} />
                </Grid>
              </>
            )}
          </Grid>
        </CardContent>
      </Card>
    </Box>
  )
}
