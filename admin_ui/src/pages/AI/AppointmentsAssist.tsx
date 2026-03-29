import { useEffect, useState } from 'react'
import { Box, Stack, Typography, Alert, Card, CardContent, TextField, MenuItem, Button, Chip, Divider } from '@mui/material'
import { getTenantSettings, TenantSettings } from '@api/tenants'
import { getRecommendedSlots, RecommendSlotsResponse } from '@api/ai'
import { listProfessionalBriefs, ProfessionalBrief } from '@api/professionals'
import { Link as RouterLink } from 'react-router-dom'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'

export default function AppointmentsAssist(){
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const [settings, setSettings] = useState<TenantSettings|undefined>()
  const [professional, setProfessional] = useState<string>('')
  const [pros, setPros] = useState<ProfessionalBrief[]>([])
  const [resp, setResp] = useState<RecommendSlotsResponse|undefined>()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string|null>(null)

  useEffect(()=>{
    (async()=>{
      if(!tenant) return
      try{
        // Load tenant settings for AI gating
        const s = await getTenantSettings(tenant)
        // Normalize casing for robust checks
        const mods = (s.modules||[]).map(m=>String(m).toLowerCase())
        const caps = (s.capabilities||[]).map(c=>String(c).toLowerCase())
        setSettings({ ...s, modules: mods as any, capabilities: caps as any })
        // Load professionals via dedicated API
        const briefs = await listProfessionalBriefs(tenant)
        const profs = (briefs || []).filter((b) => b.professional_id || b.name)
        setPros(profs)
        if (profs.length && !professional) setProfessional(profs[0].professional_id || profs[0].name)
      }catch(e:any){ setError(e?.response?.data?.detail || 'Failed to load tenant settings') }
    })()
  },[tenant])

  async function fetchRecs(){
    if(!tenant) return
    setLoading(true); setError(null)
    try{
      const data = await getRecommendedSlots(tenant, { professional: professional || undefined, top: 3 }) // id or legacy name
      setResp(data)
    }catch(e:any){ setError(e?.response?.data?.detail || 'Failed to fetch recommendations') }
    finally{ setLoading(false) }
  }

  const hasAI = (settings?.modules||[]).includes('ai')
  const canAppt = (settings?.capabilities||[]).includes('ai.appointment_recs')

  return (
    <Box sx={{ p:2 }}>
      <Stack spacing={2}>
        <Typography variant='h5'>AI · Appointments Assist</Typography>
        {!hasAI && <Alert severity='warning'>AI module is disabled. Enable it in Settings → Modules.</Alert>}
        {!canAppt && <Alert severity='info'>Capability <code>ai.appointment_recs</code> is not enabled for this tenant.</Alert>}
        {error && <Alert severity='error'>{error}</Alert>}

        <Card>
          <CardContent>
            <Stack spacing={2}>
              <Typography variant='subtitle1'>Try recommendations</Typography>
              <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems='center'>
                <TextField select size='small' label='Professional' value={professional} onChange={e=>setProfessional(e.target.value)} sx={{ minWidth: 220 }}>
                  {pros.map(p => {
                    const v = p.professional_id || p.name
                    return (
                      <MenuItem key={v} value={v}>
                        {p.name}{p.professional_id ? ` · ${p.professional_id.slice(0, 8)}…` : ''}
                      </MenuItem>
                    )
                  })}
                  {!pros.length && <MenuItem value=''>No professionals configured</MenuItem>}
                </TextField>
                <Button variant='contained' disabled={!tenant || !hasAI || !canAppt || loading || pros.length===0} onClick={fetchRecs}>{loading? 'Loading...' : 'Get Recommendations'}</Button>
              </Stack>

              {!pros.length && (
                <Alert severity='info'>
                  No professionals found for this tenant. Please add at least one in the <Button component={RouterLink} to="/professionals" size="small">Professionals</Button> page.
                </Alert>
              )}

              {resp && (
                <Box>
                  <Typography variant='subtitle2' sx={{ mb:1 }}>Recommended</Typography>
                  <Stack direction='row' spacing={1} flexWrap='wrap'>
                    {(resp.recommended ?? []).map(t => <Chip key={t} label={t} color='primary' />)}
                  </Stack>
                  <Typography variant='body2' color='text.secondary' sx={{ mt:1 }}>{resp.rationale ?? ''}</Typography>
                  <Divider sx={{ my:2 }} />
                  <Typography variant='subtitle2' sx={{ mb:1 }}>All available</Typography>
                  <Stack direction='row' spacing={1} flexWrap='wrap'>
                    {(resp.all_available ?? []).map(t => <Chip key={t} label={t} />)}
                  </Stack>
                </Box>
              )}
            </Stack>
          </CardContent>
        </Card>
      </Stack>
    </Box>
  )
}
