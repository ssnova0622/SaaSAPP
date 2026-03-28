import { useEffect, useState } from 'react'
import { Box, Button, Card, CardContent, MenuItem, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from '@mui/material'
import { listFollowups, cancelFollowup, Followup } from '@api/followups'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useDebounce } from '../../hooks/useDebounce'
import { formatPhoneForDisplay } from '../../utils/phone'

export default function Followups(){
  const { effectiveTenant } = useEffectiveTenant()
  const tenant = effectiveTenant
  const [items,setItems]=useState<Followup[]>([])
  const [loading,setLoading]=useState(false)
  const [status,setStatus]=useState<string>('')
  const [searchType, setSearchType] = useState<string>('name')
  const [searchValue, setSearchValue] = useState<string>('')
  const debouncedSearch = useDebounce(searchValue.trim(), 400)

  async function load(){
    if(!tenant) return
    const rid = ++(load as any).__rid || (((load as any).__rid = 1))
    setLoading(true)
    try{
      const res = await listFollowups(tenant, { 
        status: status || undefined, 
        customer_name: debouncedSearch && searchType === 'name' ? debouncedSearch : undefined,
        customer_phone: debouncedSearch && searchType === 'phone' ? debouncedSearch : undefined,
        page:1, 
        size:100 
      });
      if (rid !== (load as any).__rid) return
      setItems(res.items)
    } finally{ if (rid === (load as any).__rid) setLoading(false) }
  }
  useEffect(()=>{ load() // eslint-disable-next-line
  },[tenant, status, searchType, debouncedSearch])

  async function onCancel(id: string){
    if(!tenant) return
    await cancelFollowup(tenant, id)
    await load()
  }

  return (
    <Box sx={{ p:1 }}>
      <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems="center" justifyContent="space-between" sx={{ mb:2 }}>
        <Typography variant="h5">Follow-ups</Typography>
        <Stack direction="row" spacing={1} alignItems="center">
          <TextField
            select
            size="small"
            label="Search By"
            value={searchType}
            onChange={e => setSearchType(e.target.value)}
            sx={{ minWidth: 120 }}
          >
            <MenuItem value="name">Name</MenuItem>
            <MenuItem value="phone">Mobile</MenuItem>
          </TextField>
          <TextField
            size="small"
            label="Search Value"
            value={searchValue}
            onChange={e => setSearchValue(e.target.value)}
            sx={{ minWidth: 150 }}
          />
          <TextField select size="small" label="Status" value={status} onChange={e=>setStatus(e.target.value)} sx={{ minWidth: 120 }}>
            <MenuItem value="">All Status</MenuItem>
            <MenuItem value="scheduled">scheduled</MenuItem>
            <MenuItem value="sent">sent</MenuItem>
            <MenuItem value="failed">failed</MenuItem>
            <MenuItem value="canceled">canceled</MenuItem>
          </TextField>
        </Stack>
      </Stack>
      <Card>
        <CardContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Run At</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Customer</TableCell>
                <TableCell>To</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map(f=> (
                <TableRow key={f.id}>
                  <TableCell>{f.run_at}</TableCell>
                  <TableCell>{f.type}</TableCell>
                  <TableCell>{f.payload?.customer_name || '-'}</TableCell>
                  <TableCell>{f.to_phone ? formatPhoneForDisplay(f.to_phone) : (f.to_email || '-')}</TableCell>
                  <TableCell>{f.status}</TableCell>
                  <TableCell align="right">
                    {f.status==='scheduled' && <Button size="small" onClick={()=>onCancel(f.id)}>Cancel</Button>}
                  </TableCell>
                </TableRow>
              ))}
              {!items.length && (
                <TableRow><TableCell colSpan={6}><Typography variant="body2" color="text.secondary">{loading? 'Loading...' : 'No follow-ups'}</Typography></TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </Box>
  )
}
