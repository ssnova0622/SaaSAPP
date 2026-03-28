import { useEffect, useMemo, useState } from 'react'
import { Box, Button, Card, CardContent, Grid, MenuItem, Stack, TextField, Typography, Alert } from '@mui/material'
import { getWhatsAppConfig, putWhatsAppConfig } from '@api/tenants'
import { api } from '@api/axios'
import { getApiBaseURL } from '@api/config'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'

export default function WhatsAppConfigPage(){
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const [cfg, setCfg] = useState<any>({ provider:'twilio', from_numbers:[], webhook_secret:'dev', account_sid:'', auth_token:'', locale_default:'en', phone_number_id:'', access_token:'', active_menu_id:'' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string|null>(null)
  const [message, setMessage] = useState<string|null>(null)
  const [invalidNums, setInvalidNums] = useState<string[]>([])
  const [testFrom, setTestFrom] = useState<string>('+911112223334')
  const [testTo, setTestTo] = useState<string>('')
  const [testBody, setTestBody] = useState<string>('1')
  const [testResp, setTestResp] = useState<string>('')

  useEffect(()=>{
    (async()=>{
      if(!tenant) return
      setError(null); setMessage(null)
      try{
        const c = await getWhatsAppConfig(tenant)
        const list = Array.isArray(c?.from_numbers) ? c.from_numbers.map((n:any)=>String(n)) : []
        setCfg({
          provider: (c.provider||'twilio'),
          from_numbers: list,
          webhook_secret: c.webhook_secret||'dev',
          account_sid: c.account_sid||'',
          auth_token: c.auth_token||'',
          locale_default: c.locale_default||'en',
          phone_number_id: c.phone_number_id||'',
          access_token: c.access_token||'',
          active_menu_id: c.active_menu_id||'',
        })
        // restore last test payload for this tenant if available
        try{
          const saved = localStorage.getItem(`wa_test_${tenant}`)
          if(saved){
            const t = JSON.parse(saved)
            if(t?.from) setTestFrom(String(t.from))
            if(t?.to && list.includes(String(t.to))) setTestTo(String(t.to))
            else setTestTo(list[0] || '')
            if(t?.body) setTestBody(String(t.body))
          } else {
            setTestTo(list[0] || '')
          }
        }catch{ setTestTo(list[0] || '') }
      }catch(e:any){ setError(e?.response?.data?.detail || 'Failed to load config') }
    })()
  },[tenant])

  // E.164 validation for numbers
  useEffect(()=>{
    const nums = Array.isArray(cfg?.from_numbers) ? cfg.from_numbers : []
    const invalid = nums.filter((n:string)=>{
      let v = String(n || '')
      // Accept values with optional "whatsapp:" prefix
      if (v.toLowerCase().startsWith('whatsapp:')) v = v.slice('whatsapp:'.length)
      return !/^\+?[1-9]\d{6,14}$/.test(v)
    })
    // Show invalids normalized (without prefix) to help the user
    const normalized = invalid.map((n:string)=>{
      let v = String(n || '')
      return v.toLowerCase().startsWith('whatsapp:') ? v.slice('whatsapp:'.length) : v
    })
    setInvalidNums(normalized)
  }, [cfg?.from_numbers])

  const webhookUrl = useMemo(()=> `${getApiBaseURL()}/integrations/twilio/whatsapp/webhook`, [])

  async function onSave(){
    if(!tenant) return
    setLoading(true); setError(null); setMessage(null)
    try{
      // Normalize numbers: accept optional whatsapp: prefix; store as +E.164
      const raw = Array.isArray(cfg.from_numbers)? cfg.from_numbers : []
      const normalized = raw.map((n:string)=>{
        let v = String(n||'').trim()
        if (v.toLowerCase().startsWith('whatsapp:')) v = v.slice('whatsapp:'.length)
        return v
      }).filter(Boolean)
      if (normalized.length === 0){ throw new Error('Please add at least one valid From number') }
      const payload = { ...cfg, from_numbers: normalized }
      await putWhatsAppConfig(tenant, payload)
      setMessage('WhatsApp configuration saved')
    }catch(e:any){
      const d = e?.response?.data?.detail
      let msg = 'Save failed'
      if (typeof d === 'string') msg = d
      else if (Array.isArray(d) && d.length) msg = d[0]?.msg || JSON.stringify(d[0])
      else if (d && typeof d === 'object') msg = d.msg || JSON.stringify(d)
      else if (e?.message) msg = e.message
      setError(msg)
    }finally{ setLoading(false) }
  }

  async function testWebhook(){
    setTestResp('')
    try{
      // persist last test payload for this tenant
      try{ localStorage.setItem(`wa_test_${tenant}`, JSON.stringify({ from: testFrom, to: testTo, body: testBody })) }catch{}
      const res = await api.post('/integrations/twilio/whatsapp/webhook', { From: testFrom, To: testTo, Body: testBody }, { responseType: 'text' })
      setTestResp(String(res.data || ''))
    }catch(e:any){
      setTestResp(String(e?.response?.data || e?.message || 'Request failed'))
    }
  }

  return (
    <Box sx={{ p:1 }}>
      <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems="center" justifyContent="space-between" sx={{ mb:2 }}>
        <Typography variant="h5">WhatsApp Config</Typography>
        {tenant ? <Alert severity="info" icon={false} sx={{ py: 0.5 }}>Tenant: <strong>{tenant}</strong></Alert> : null}
      </Stack>

      {error && <Alert severity='error' sx={{ mb:2 }}>{error}</Alert>}
      {message && <Alert severity='success' sx={{ mb:2 }}>{message}</Alert>}

      <Card>
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField select fullWidth label="Provider" value={cfg.provider||'twilio'} onChange={e=>setCfg((p:any)=>({ ...p, provider: e.target.value }))}>
                <MenuItem value="twilio">Twilio (dummy/dev)</MenuItem>
                <MenuItem value="meta_cloud">Meta Cloud (dummy interactive)</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField fullWidth label="Default Locale" value={cfg.locale_default||'en'} onChange={e=>setCfg((p:any)=>({ ...p, locale_default: e.target.value }))} placeholder="en" />
            </Grid>
            <Grid item xs={12}>
              <TextField fullWidth multiline minRows={2} label="From numbers (one per line, E.164 e.g., +911234567890)" value={(cfg.from_numbers||[]).join('\n')} onChange={e=>{
                const list = e.target.value.split(/\n|,/).map(s=>s.trim()).filter(Boolean)
                setCfg((p:any)=>({ ...p, from_numbers: list }))
              }} helperText="Accepts optional 'whatsapp:+..' prefix; we will normalize to +E.164" />
              {invalidNums.length>0 && (
                <Typography variant='body2' color='error' sx={{ mt: 1 }}>Invalid numbers: {invalidNums.join(', ')}</Typography>
              )}
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField fullWidth label="Webhook secret (dev)" value={cfg.webhook_secret||''} onChange={e=>setCfg((p:any)=>({ ...p, webhook_secret: e.target.value }))} helperText="Used to sign bot requests; keep 'dev' for local tests" />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField fullWidth label="Account SID (optional)" value={cfg.account_sid||''} onChange={e=>setCfg((p:any)=>({ ...p, account_sid: e.target.value }))} />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField fullWidth type="password" label="Auth token (optional)" value={cfg.auth_token||''} onChange={e=>setCfg((p:any)=>({ ...p, auth_token: e.target.value }))} />
            </Grid>
            {String(cfg.provider||'twilio')==='meta_cloud' && (
              <>
                <Grid item xs={12} md={6}>
                  <TextField fullWidth label="Meta phone_number_id" value={cfg.phone_number_id||''} onChange={e=>setCfg((p:any)=>({ ...p, phone_number_id: e.target.value }))} helperText="Dummy mode: any value allowed" />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField fullWidth type="password" label="Meta access_token" value={cfg.access_token||''} onChange={e=>setCfg((p:any)=>({ ...p, access_token: e.target.value }))} helperText="Dummy mode: any value allowed" />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField fullWidth label="Active menu id (optional)" value={cfg.active_menu_id||''} onChange={e=>setCfg((p:any)=>({ ...p, active_menu_id: e.target.value }))} helperText="If empty, latest published menu will be used" />
                </Grid>
                <Grid item xs={12}>
                  <Alert severity='info'>Meta Cloud is in dummy mode: we log interactive payloads and send a text fallback. Tapping buttons requires Meta webhook, which we can add next.</Alert>
                </Grid>
              </>
            )}
            <Grid item xs={12}>
              <Button variant="contained" onClick={onSave} disabled={loading || !tenant || invalidNums.length>0}>Save</Button>
              <Typography variant='body2' color='text.secondary' sx={{ mt:1 }}>Webhook URL: {webhookUrl}</Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Test-send to dummy webhook */}
      <Card sx={{ mt: 2 }}>
        <CardContent>
          <Typography variant='h6' sx={{ mb: 1 }}>Test webhook (dummy/dev)</Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <TextField fullWidth label='From' value={testFrom} onChange={e=>setTestFrom(e.target.value)} placeholder='+911112223334' />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField select fullWidth label='To (tenant number)' value={testTo} onChange={e=>setTestTo(e.target.value)}>
                {(cfg.from_numbers||[]).map((n:string)=>(<MenuItem key={n} value={n}>{n}</MenuItem>))}
              </TextField>
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField fullWidth label='Body' value={testBody} onChange={e=>setTestBody(e.target.value)} placeholder='1' />
            </Grid>
            <Grid item xs={12}>
              <Button variant='outlined' onClick={testWebhook} disabled={!tenant || !testTo}>Send test</Button>
            </Grid>
            {testResp && (
              <Grid item xs={12}>
                <Typography variant='subtitle2' sx={{ mb:1 }}>Response (TwiML/XML)</Typography>
                <Box sx={{ p:1, bgcolor:'#fafafa', border:'1px solid #eee', borderRadius:1, fontFamily:'monospace', whiteSpace:'pre-wrap' }}>{testResp}</Box>
              </Grid>
            )}
          </Grid>
        </CardContent>
      </Card>
    </Box>
  )
}
