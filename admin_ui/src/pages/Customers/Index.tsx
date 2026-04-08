import { useEffect, useState } from 'react'
import { Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Select, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from '@mui/material'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import AddIcon from '@mui/icons-material/Add'
import { listCustomers, upsertCustomer, importCustomersCsv, Customer, setCustomerActive } from '@api/customers'
import { getTenantSettings } from '@api/tenants'
import { listCountries, type CountryOption } from '@api/meta'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useDebounce } from '../../hooks/useDebounce'
import {
  isValidPhoneInput,
  formatPhoneForDisplay,
  combineDialAndMobile,
  formatEntityPhoneForDisplay,
  displayE164FromEntity,
} from '../../utils/phone'
import ExportMenu from '@components/ExportMenu'

export default function Customers() {
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const [items, setItems] = useState<Customer[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [size] = useState(50)
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounce(search, 400)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeFilter, setActiveFilter] = useState<'all'|'active'|'inactive'>('all')

  const [editOpen, setEditOpen] = useState(false)
  const [form, setForm] = useState<{name:string;phone:string;email?:string;tags?:string}>({name:'',phone:''})
  const [phoneErr, setPhoneErr] = useState<string>('')
  const [countries, setCountries] = useState<CountryOption[]>([])
  const [custDial, setCustDial] = useState('+91')

  async function load() {
    if (!tenant) return
    const rid = ++(load as any).__rid || (((load as any).__rid = 1))
    setLoading(true); setError(null)
    try {
      const res = await listCustomers(tenant, { search: debouncedSearch, page, size, active: activeFilter === 'all' ? undefined : activeFilter === 'active' })
      if (rid !== (load as any).__rid) return
      setItems(res.items)
      setTotal(res.total)
    } catch (e:any) { if (rid === (load as any).__rid) setError(e?.response?.data?.detail || 'Failed to load') }
    finally { if (rid === (load as any).__rid) setLoading(false) }
  }

  useEffect(() => { load() // eslint-disable-next-line
  }, [tenant, page, size, activeFilter, debouncedSearch])

  useEffect(() => {
    listCountries().then(r => setCountries(r.items || [])).catch(() => setCountries([]))
  }, [])

  useEffect(() => {
    if (!tenant) return
    getTenantSettings(tenant).then(s => {
      const tc = (s.tenant_country || 'IN').toUpperCase()
      const row = countries.find(c => c.iso2 === tc)
      setCustDial(`+${row?.dial || '91'}`)
    }).catch(() => setCustDial('+91'))
  }, [tenant, countries])

  async function onSave() {
    if (!tenant) return
    const tagsArr = (form.tags||'').split(',').map(t=>t.trim()).filter(Boolean)
    const raw = (form.phone || '').trim()
    const phonePayload = raw.startsWith('+') ? raw : combineDialAndMobile(custDial, raw)
    const ok = isValidPhoneInput(raw.startsWith('+') ? raw : phonePayload)
    setPhoneErr(ok ? '' : 'Invalid phone (national digits, or full international with +)')
    if (!ok) return
    await upsertCustomer(tenant, { name: form.name, phone: phonePayload, email: form.email, tags: tagsArr })
    setEditOpen(false)
    await load()
  }

  async function onCsvSelect(e: React.ChangeEvent<HTMLInputElement>) {
    if (!tenant) return
    const file = e.target.files?.[0]
    if (!file) return
    await importCustomersCsv(tenant, file)
    await load()
    e.currentTarget.value = ''
  }

  async function onToggleActive(c: Customer) {
    if (!tenant) return
    try {
      const next = !(c.active ?? true)
      await setCustomerActive(tenant, displayE164FromEntity(c), next)
      await load()
    } catch (e:any) {
      setError(e?.response?.data?.detail || 'Failed to update status')
    }
  }

  return (
    <Box sx={{ p:1 }}>
      <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems={{ xs:'flex-start', md:'center' }} justifyContent="space-between" sx={{ mb:2 }}>
        <Typography variant="h5">Customers</Typography>
      </Stack>
      <Card>
        <CardContent>
          <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems="center" sx={{ mb:2 }}>
            <TextField size="small" placeholder="Search name/phone/email" value={search} onChange={e=>{ setSearch(e.target.value); setPage(1) }} sx={{ minWidth: 220 }} />
            <Select size="small" value={activeFilter} onChange={(e)=>{ setActiveFilter(e.target.value as any); setPage(1) }} displayEmpty>
              <MenuItem value="all">All</MenuItem>
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="inactive">Inactive</MenuItem>
            </Select>
            <Button variant="contained" startIcon={<AddIcon/>} onClick={()=>{ setForm({name:'',phone:''}); setPhoneErr(''); setEditOpen(true) }} disabled={!tenant}>Add</Button>
            <Button component="label" startIcon={<UploadFileIcon/>} disabled={!tenant}>
              Import CSV
              <input type="file" accept=".csv" hidden onChange={onCsvSelect} />
            </Button>
            <ExportMenu
              data={items.map((c) => ({
                name: c.name,
                phone: formatPhoneForDisplay(c.phone),
                email: c.email ?? '',
                tags: (c.tags || []).join(', '),
                status: (c.active ?? true) ? 'Active' : 'Inactive',
                created_by: c.created_by ?? '',
                updated_by: c.updated_by ?? '',
              }))}
              columns={[
                { key: 'name', label: 'Name' },
                { key: 'phone', label: 'Phone' },
                { key: 'email', label: 'Email' },
                { key: 'tags', label: 'Tags' },
                { key: 'status', label: 'Status' },
                { key: 'created_by', label: 'Created By' },
                { key: 'updated_by', label: 'Updated By' },
              ]}
              filename="customers"
              title="Customers"
              disabled={loading}
              size="small"
            />
            {error && <Typography color="error" variant="body2">{error}</Typography>}
          </Stack>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Phone</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Tags</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Staff (C/U)</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((c)=> (
                <TableRow key={displayE164FromEntity(c) || `${c.name}-${c.email ?? ''}`} hover>
                  <TableCell>{c.name}</TableCell>
                  <TableCell>{formatEntityPhoneForDisplay(c)}</TableCell>
                  <TableCell>{c.email}</TableCell>
                  <TableCell>{(c.tags||[]).join(', ')}</TableCell>
                  <TableCell>
                    <Chip size="small" label={(c.active??true) ? 'Active' : 'Inactive'} color={(c.active??true) ? 'success' : 'default'} />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" display="block" color="text.secondary">
                      C: {c.created_by ?? '-'}
                    </Typography>
                    <Typography variant="caption" display="block" color="text.secondary">
                      U: {c.updated_by ?? '-'}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={1} justifyContent="flex-end">
                      <Button size="small" variant="outlined" onClick={() => {
                        const pn = c.phone_number
                        let local = ''
                        const national = pn?.number ?? pn?.mobile_number
                        if (national != null && String(national).length > 0) {
                          local = String(national).replace(/\D/g, '')
                        } else {
                          const disp = formatEntityPhoneForDisplay(c)
                          const d = custDial.replace(/\D/g, '')
                          const all = disp.replace(/\D/g, '')
                          local = all.startsWith(d) ? all.slice(d.length) : all.replace(/^0+/, '')
                        }
                        setForm({ name: c.name || '', phone: local, email: c.email || '', tags: (c.tags || []).join(', ') })
                        setPhoneErr('')
                        setEditOpen(true)
                      }}>Edit</Button>
                      <Button size="small" onClick={()=>onToggleActive(c)}>{(c.active??true) ? 'Deactivate' : 'Activate'}</Button>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))}
              {!items.length && (
                <TableRow><TableCell colSpan={7}><Typography variant="body2" color="text.secondary">{loading? 'Loading...' : 'No customers'}</Typography></TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={editOpen} onClose={()=>setEditOpen(false)}>
        <DialogTitle>{form.phone ? 'Edit Customer' : 'Add Customer'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt:1, minWidth: 360 }}>
            <TextField label="Name" value={form.name} onChange={e=>setForm(prev=>({...prev, name:e.target.value}))} />
            <TextField label="Phone" value={form.phone} onChange={e=>{ setForm(prev=>({...prev, phone:e.target.value})); if(phoneErr) setPhoneErr('') }} error={!!phoneErr} helperText={phoneErr || `National digits or full +number. Default country from tenant: ${custDial}`} />
            <TextField label="Email" value={form.email||''} onChange={e=>setForm(prev=>({...prev, email:e.target.value}))} />
            <TextField label="Tags (comma separated)" value={form.tags||''} onChange={e=>setForm(prev=>({...prev, tags:e.target.value}))} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setEditOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={onSave} disabled={!tenant}>Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
