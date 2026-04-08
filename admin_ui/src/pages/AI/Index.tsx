import { useEffect, useState } from 'react'
import { Box, Card, CardContent, Stack, Typography, Button, Chip, Alert } from '@mui/material'
import { getTenantSettings, TenantSettings } from '@api/tenants'
import { useNavigate } from 'react-router-dom'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
export default function AIIndex(){
  // Use effective tenant selection (Super Admin selects tenant; non-super is locked to their tenant)
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const [settings, setSettings] = useState<TenantSettings|undefined>()
  const [error, setError] = useState<string|null>(null)
  const navigate = useNavigate()

  useEffect(()=>{
    (async()=>{
      if(!tenant) return
      try{
        const s = await getTenantSettings(tenant)
        setSettings(s)
      }catch(e:any){ setError(e?.response?.data?.detail || 'Failed to load tenant settings') }
    })()
  },[tenant])

  // Normalize to lowercase for robust checks
  const modulesLC = (settings?.modules||[]).map(m=>String(m).toLowerCase())
  const capsLC = (settings?.capabilities||[]).map(c=>String(c).toLowerCase())
  const hasAI = modulesLC.includes('ai')
  const hasStore = modulesLC.includes('store')
  const hasSalon = modulesLC.includes('salon')
  const hasClinic = modulesLC.includes('clinic')
  const canPred = capsLC.includes('ai.predictions')
  const canAppt = capsLC.includes('ai.appointment_recs')

  const showPredictions = hasAI && hasStore && canPred
  const showAppointments = hasAI && (hasSalon || hasClinic) && canAppt

  // If only one AI feature is applicable, auto-redirect to it to avoid extra click/confusion.
  useEffect(() => {
    if (!tenant) return
    // Only redirect when we definitively know what to show
    if (showPredictions && !showAppointments) {
      navigate('/ai/predictions', { replace: true })
    } else if (showAppointments && !showPredictions) {
      navigate('/ai/appointments', { replace: true })
    }
  }, [tenant, showPredictions, showAppointments, navigate])

  return (
    <Box sx={{ p:2 }}>
      <Stack spacing={2}>
        <Typography variant="h5">AI</Typography>
        {!tenant && (
          <Alert severity='info'>Select a tenant from the top-left selector to view AI features.</Alert>
        )}
        {tenant && !hasAI && (
          <Alert severity='warning'>AI module is disabled for this tenant. Ask a Super Admin to enable it in Settings → Modules.</Alert>
        )}
        {error && <Alert severity='error'>{error}</Alert>}

        <Stack direction={{ xs:'column', md:'row' }} spacing={2}>
          {/* Store Predictions card — render only if available for this tenant */}
          {showPredictions && (
            <Card sx={{ flex:1 }}>
              <CardContent>
                <Stack spacing={1}>
                  <Stack direction='row' spacing={1} alignItems='center'>
                    <Typography variant='h6'>Store Predictions</Typography>
                    <Chip size='small' label='store' />
                  </Stack>
                  <Typography variant='body2' color='text.secondary'>Low stock forecast, top sellers, sales forecast, and cart recovery insights.</Typography>
                  <Stack direction='row'>
                    <Button variant='contained' onClick={()=>navigate('/ai/predictions')}>Open Predictions</Button>
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          )}

          {/* Appointments Assist card — render only if available for this tenant */}
          {showAppointments && (
            <Card sx={{ flex:1 }}>
              <CardContent>
                <Stack spacing={1}>
                  <Stack direction='row' spacing={1} alignItems='center'>
                    <Typography variant='h6'>Appointments Assist</Typography>
                    <Chip size='small' label={hasSalon ? 'salon' : 'clinic'} />
                  </Stack>
                  <Typography variant='body2' color='text.secondary'>Recommended time slots for faster booking in Admin and WhatsApp flows.</Typography>
                  <Stack direction='row'>
                    <Button variant='contained' onClick={()=>navigate('/ai/appointments')}>Open Appointments Assist</Button>
                  </Stack>
                </Stack>
              </CardContent>
            </Card>
          )}
        </Stack>

        {/* If AI module is enabled but no AI features are available for this tenant, show a minimal hint */}
        {tenant && hasAI && !showPredictions && !showAppointments && (
          <Alert severity='info'>AI is enabled but no vertical modules are active. Enable Store or Salon/Clinic module for this tenant to activate AI features.</Alert>
        )}
      </Stack>
    </Box>
  )
}
