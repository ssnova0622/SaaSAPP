import { useEffect, useState } from 'react'
import { Box, Button, Card, CardContent, MenuItem, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from '@mui/material'
import { getRetentionSummary, listRetention, RetentionSummary } from '@api/retention'
import { Link as RouterLink } from 'react-router-dom'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { formatPhoneForDisplay } from '../../utils/phone'

export default function Retention(){
  const { effectiveTenant } = useEffectiveTenant()
  const tenant = effectiveTenant
  const [summary,setSummary]=useState<RetentionSummary|undefined>()
  const [segment,setSegment]=useState<'active'|'at_risk'|'churned'>('at_risk')
  const [days,setDays]=useState<number|''>('' as any)
  const [items,setItems]=useState<any[]>([])
  const [loading,setLoading]=useState(false)

  async function loadSummary(){
    if(!tenant) return
    const rid = ++(loadSummary as any).__rid || (((loadSummary as any).__rid = 1))
    try{
      const s = await getRetentionSummary(tenant)
      if (rid !== (loadSummary as any).__rid) return
      setSummary(s)
    } catch {}
  }
  async function loadList(){
    if(!tenant) return
    const rid = ++(loadList as any).__rid || (((loadList as any).__rid = 1))
    setLoading(true)
    try{
      const res = await listRetention(tenant, { segment, days: (segment!=='active' && days)? Number(days) : undefined, page:1, size:100 })
      if (rid !== (loadList as any).__rid) return
      setItems(res.items)
    } finally{ if (rid === (loadList as any).__rid) setLoading(false) }
  }

  useEffect(()=>{ loadSummary() // eslint-disable-next-line
  },[tenant])
  useEffect(()=>{ loadList() // eslint-disable-next-line
  },[tenant, segment, days])

  return (
    <Box sx={{ p:1 }}>
      <Typography variant="h5" sx={{ mb:2 }}>Retention</Typography>
      <Card sx={{ mb:2 }}>
        <CardContent>
          <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems="center">
            <Typography>Active: <b>{summary?.active ?? '-'}</b></Typography>
            <Typography>At Risk: <b>{summary?.at_risk ?? '-'}</b></Typography>
            <Typography>Churned: <b>{summary?.churned ?? '-'}</b></Typography>
          </Stack>
        </CardContent>
      </Card>

      <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems="center" sx={{ mb:2 }}>
        <TextField select size="small" label="Segment" value={segment} onChange={e=>setSegment(e.target.value as any)} sx={{ minWidth: 180 }}>
          <MenuItem value="active">active</MenuItem>
          <MenuItem value="at_risk">at_risk</MenuItem>
          <MenuItem value="churned">churned</MenuItem>
        </TextField>
        {(segment==='at_risk' || segment==='churned') && (
          <TextField size="small" type="number" label="Days (optional)" value={days} onChange={e=>setDays(e.target.value? Number(e.target.value) as any : '' as any)} />
        )}
        <Button component={RouterLink} to={`/promotions/new?segment=${segment}${days ? `&days=${days}` : ''}`} variant="outlined">Create promotion for this segment</Button>
      </Stack>

      <Card>
        <CardContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Phone</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Last Visit</TableCell>
                <TableCell>Days</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((r,i)=> (
                <TableRow key={(r.phone||'')+i}>
                  <TableCell>{r.name || '-'}</TableCell>
                  <TableCell>{formatPhoneForDisplay(r.phone) || '-'}</TableCell>
                  <TableCell>{r.email || '-'}</TableCell>
                  <TableCell>{r.last_visit_at || '-'}</TableCell>
                  <TableCell>{r.days ?? '-'}</TableCell>
                </TableRow>
              ))}
              {!items.length && (
                <TableRow><TableCell colSpan={5}><Typography variant="body2" color="text.secondary">{loading? 'Loading...' : 'No data'}</Typography></TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Box>
  )
}
