import { useEffect, useState } from 'react'
import { Box, Button, Card, CardContent, Divider, Grid, IconButton, Stack, Step, StepLabel, Stepper, TextField, Typography, Alert, MenuItem, List, ListItem, ListItemText } from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import { useNavigate } from 'react-router-dom'
import { upsertMenu, publishMenu, createTrigger, testTriggerWebhook } from '@api/whatsapp'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { templatesCatalog, defaultTrigger, MenuTemplate } from '../../modules/WhatsApp/templates'

type TriggerDraft = {
  trigger_id: string
  match: { type: 'exact'|'prefix'|'contains'|'regex'; value: string; locale?: string }
  action: { kind: 'render_submenu'; menu_id: string; node_id?: string }
  enabled: boolean
  priority: number
}

export default function WhatsAppMenuWizard(){
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const [activeStep, setActiveStep] = useState(0)
  const [error, setError] = useState<string|null>(null)
  const [message, setMessage] = useState<string|null>(null)

  const [menuId, setMenuId] = useState('default')
  const [name, setName] = useState('Default Menu')
  const [selectedKey, setSelectedKey] = useState<string>('retail')
  const [draft, setDraft] = useState<MenuTemplate>(()=>templatesCatalog[0].tpl)
  const [trigger, setTrigger] = useState<TriggerDraft>(defaultTrigger('default') as TriggerDraft)
  const [testTo, setTestTo] = useState<string>('')

  const navigate = useNavigate()

  useEffect(()=>{
    const t = templatesCatalog.find(x=>x.key===selectedKey)?.tpl || templatesCatalog[0].tpl
    // Clone to avoid mutating catalog
    const cloned: MenuTemplate = JSON.parse(JSON.stringify(t))
    cloned.menu_id = menuId
    cloned.name = name
    setDraft(cloned)
    setTrigger(defaultTrigger(menuId) as TriggerDraft)
  },[selectedKey, menuId, name])

  async function onSaveDraft(){
    if(!tenant) { setError('Select a tenant'); return }
    setError(null); setMessage(null)
    try{
      await upsertMenu(tenant, { menu_id: menuId.trim()||'default', name: name.trim()||menuId, tree: draft.tree, locales: draft.locales||{} })
      setMessage('Draft saved')
    }catch(e:any){ setError(e?.response?.data?.detail || 'Failed to save draft') }
  }

  async function onPublish(){
    if(!tenant) { setError('Select a tenant'); return }
    setError(null); setMessage(null)
    try{
      await upsertMenu(tenant, { menu_id: menuId.trim()||'default', name: name.trim()||menuId, tree: draft.tree, locales: draft.locales||{} })
      await createTrigger(tenant, trigger)
      await publishMenu(tenant, menuId.trim()||'default')
      setMessage('Menu published successfully')
    }catch(e:any){ setError(e?.response?.data?.detail || 'Failed to publish') }
  }

  async function onTest(){
    setError(null); setMessage(null)
    if(!testTo.trim()){ setError('Enter a To number (your WhatsApp sandbox number)'); return }
    try{
      await testTriggerWebhook(testTo.trim(), 'hello')
      setMessage('Webhook invoked.')
    }catch(e:any){ setError(e?.response?.data?.detail || 'Failed to send test') }
  }

  function StepBasics(){
    return (
      <Stack spacing={2}>
        {tenant ? <Alert severity="info" icon={false}>Tenant: <strong>{tenant}</strong></Alert> : null}
        <TextField label="Menu ID" value={menuId} onChange={e=>setMenuId(e.target.value)} helperText="Use 'default' unless you need multiple menus." sx={{ maxWidth: 360 }} />
        <TextField label="Menu name" value={name} onChange={e=>setName(e.target.value)} sx={{ maxWidth: 480 }} />
        <TextField select label="Template" value={selectedKey} onChange={e=>setSelectedKey(e.target.value)} sx={{ maxWidth: 360 }}>
          {templatesCatalog.map(t => <MenuItem key={t.key} value={t.key}>{t.label}</MenuItem>)}
        </TextField>
        <Alert severity='info'>You can start from a template and tweak labels later.</Alert>
      </Stack>
    )
  }

  function StepItems(){
    // Simple editor: just edit English labels for root items
    const items = (draft.tree?.items||[]) as any[]
    function updateLabel(idx: number, text: string){
      const next = { ...draft, tree: { ...draft.tree, items: draft.tree.items.map((it: any, i: number)=> i===idx? { ...it, label: { ...(it.label||{}), en: text } }: it) } }
      setDraft(next)
    }
    return (
      <Stack spacing={2}>
        <Typography variant='body2' color='text.secondary'>Edit top-level option labels. Advanced editing is available in the Menu Editor after publishing.</Typography>
        <List dense>
          {items.map((it, idx)=> (
            <ListItem key={it.id||idx} secondaryAction={null}>
              <ListItemText primary={`Item ${idx+1}`} secondary={String(it.action?.action_id||it.action?.kind||'action')} />
              <TextField label='Label (en)' value={String(it?.label?.en||'')} onChange={e=>updateLabel(idx, e.target.value)} sx={{ minWidth: 320 }} />
            </ListItem>
          ))}
          {!items.length && <Typography variant='body2' color='text.secondary'>No items in this template. You can add them later in Menu Editor.</Typography>}
        </List>
      </Stack>
    )
  }

  function StepTriggers(){
    return (
      <Stack spacing={2}>
        <Typography variant='body2' color='text.secondary'>A default trigger will show your menu when users say "hello". You can add more later.</Typography>
        <TextField label='Trigger ID' value={trigger.trigger_id} onChange={e=> setTrigger({ ...trigger, trigger_id: e.target.value })} sx={{ maxWidth: 360 }} />
        <TextField select label='Match type' value={trigger.match.type} onChange={e=> setTrigger({ ...trigger, match: { ...trigger.match, type: e.target.value as any } })} sx={{ maxWidth: 200 }}>
          <MenuItem value='exact'>exact</MenuItem>
          <MenuItem value='prefix'>prefix</MenuItem>
          <MenuItem value='contains'>contains</MenuItem>
          <MenuItem value='regex'>regex</MenuItem>
        </TextField>
        <TextField label='Match value' value={trigger.match.value} onChange={e=> setTrigger({ ...trigger, match: { ...trigger.match, value: e.target.value } })} sx={{ maxWidth: 360 }} />
        <TextField label='Action menu_id' value={trigger.action.menu_id} onChange={e=> setTrigger({ ...trigger, action: { ...trigger.action, menu_id: e.target.value } })} sx={{ maxWidth: 360 }} />
        <TextField label='Priority' type='number' value={trigger.priority} onChange={e=> setTrigger({ ...trigger, priority: Number(e.target.value||0) })} sx={{ maxWidth: 160 }} />
      </Stack>
    )
  }

  function StepPreview(){
    const items = (draft.tree?.items||[]) as any[]
    return (
      <Stack spacing={2}>
        <Typography variant='subtitle1'>Preview</Typography>
        <Card variant='outlined'>
          <CardContent>
            <Typography variant='body1' sx={{ mb:1 }}>{draft.tree?.title?.en || 'Menu'}</Typography>
            <List dense>
              {items.map((it, idx)=> <ListItem key={it.id||idx}><ListItemText primary={`${idx+1}) ${String(it?.label?.en||'')}`} /></ListItem>)}
            </List>
            {!items.length && <Typography variant='body2' color='text.secondary'>No items yet</Typography>}
          </CardContent>
        </Card>
        <Divider />
        <Stack direction={{ xs:'column', sm:'row' }} spacing={2} alignItems='center'>
          <TextField label='Test To number' value={testTo} onChange={e=>setTestTo(e.target.value)} placeholder='+911234567890' sx={{ maxWidth: 280 }} />
          <Button variant='outlined' onClick={onTest}>Send test "hello"</Button>
        </Stack>
        <Stack direction='row' spacing={1}>
          <Button variant='outlined' onClick={onSaveDraft}>Save Draft</Button>
          <Button variant='contained' onClick={onPublish}>Publish</Button>
        </Stack>
      </Stack>
    )
  }

  function renderStep(){
    if(activeStep===0) return <StepBasics />
    if(activeStep===1) return <StepItems />
    if(activeStep===2) return <StepTriggers />
    return <StepPreview />
  }

  return (
    <Box sx={{ p:1 }}>
      <Stack direction='row' spacing={1} alignItems='center' sx={{ mb:2 }}>
        <IconButton onClick={()=>navigate('/whatsapp')}><ArrowBackIcon /></IconButton>
        <Typography variant='h5'>Create WhatsApp Menu</Typography>
      </Stack>

      {error && <Alert severity='error' sx={{ mb:2 }}>{error}</Alert>}
      {message && <Alert severity='success' sx={{ mb:2 }}>{message}</Alert>}

      <Stepper activeStep={activeStep} alternativeLabel sx={{ mb:2 }}>
        {['Basics','Items & Actions','Triggers','Preview & Publish'].map(label=> (
          <Step key={label}><StepLabel>{label}</StepLabel></Step>
        ))}
      </Stepper>

      <Grid container spacing={2}>
        <Grid item xs={12}>
          {renderStep()}
        </Grid>
      </Grid>

      <Stack direction='row' spacing={1} justifyContent='space-between' sx={{ mt:2 }}>
        <Button disabled={activeStep===0} onClick={()=>setActiveStep(s=>Math.max(0, s-1))}>Back</Button>
        <Stack direction='row' spacing={1}>
          {activeStep<3 && <Button variant='contained' onClick={()=>setActiveStep(s=>Math.min(3, s+1))}>Next</Button>}
          {activeStep===3 && <Button variant='contained' onClick={onPublish}>Publish</Button>}
        </Stack>
      </Stack>
    </Box>
  )
}
