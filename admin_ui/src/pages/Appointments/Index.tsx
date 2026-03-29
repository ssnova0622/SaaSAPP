import { useEffect, useState } from 'react'
import { Box, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogTitle, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography, MenuItem, Alert, Menu } from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import MoreVertIcon from '@mui/icons-material/MoreVert'
import { listAppointments, createAppointment, cancelAppointment, rescheduleAppointment, updateAppointmentStatus, Appointment } from '@api/appointments'
import { formatPhoneForDisplay } from '../../utils/phone'
import { formatDateForDisplay } from '../../utils/dateFormat'
import { useTenantDateFormat } from '../../hooks/useTenantDateFormat'
import { getAppointmentStatusLabel, APPOINTMENT_STATUS_OPTIONS, APPOINTMENT_STATUS } from '../../constants/appointmentStatus'
import { listProfessionalsFull, ProfessionalFull, Slot } from '@api/professionals'
import { api } from '@api/axios'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useCapabilities } from '../../hooks/useCapabilities'
import { useDebounce } from '../../hooks/useDebounce'
import { useAlert } from '@contexts/AlertContext'
import ExportMenu from '@components/ExportMenu'

export default function Appointments(){
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const { canEditAppointments } = useCapabilities()
  const { showAlert } = useAlert()
  const [items,setItems]=useState<Appointment[]>([])
  const [loading,setLoading]=useState(false)
  const [filterProfessional, setFilterProfessional] = useState<string>('')
  const [filterDate, setFilterDate] = useState<string>(new Date().toISOString().split('T')[0])
  const [filterStatus, setFilterStatus] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const debouncedSearch = useDebounce(searchQuery.trim(), 300)

  const [open,setOpen]=useState(false)
  const [form,setForm]=useState<{customer_name:string;customer_phone:string;professional_id:string;time:string;date:string}>({customer_name:'',customer_phone:'',professional_id:'',time:'',date:new Date().toISOString().split('T')[0]})
  
  const [openReschedule, setOpenReschedule] = useState(false)
  const [rescheduleAppt, setRescheduleAppt] = useState<Appointment | null>(null)
  const [rescheduleDate, setRescheduleDate] = useState<string>('')
  const [rescheduleTime, setRescheduleDateSetTime] = useState<string>('')
  
  const [profs, setProfs] = useState<ProfessionalFull[]>([])
  const [profsLoading, setProfsLoading] = useState(false)
  const [availableSlots, setAvailableSlots] = useState<Slot[]>([])
  const [slotsLoading, setSlotsLoading] = useState(false)

  const [rescheduleSlots, setRescheduleSlots] = useState<Slot[]>([])
  const [rescheduleSlotsLoading, setRescheduleSlotsLoading] = useState(false)
  const [actionMenuAnchor, setActionMenuAnchor] = useState<{ el: HTMLElement; appt: Appointment } | null>(null)
  const dateFormat = useTenantDateFormat()

  async function load(){
    if(!tenant) return
    const rid = ++(load as any).__rid || (((load as any).__rid = 1))
    setLoading(true)
    try{
      const list = await listAppointments(tenant, { 
        professional: filterProfessional || undefined,
        date: filterDate || undefined,
        status: filterStatus || undefined,
        search: debouncedSearch || undefined
      })
      if (rid !== (load as any).__rid) return
      setItems(list)
    } finally{ if (rid === (load as any).__rid) setLoading(false) }
  }
  useEffect(()=>{ load() // eslint-disable-next-line
  },[tenant, filterProfessional, filterDate, filterStatus, debouncedSearch])

  // Load professionals for dropdown (reacts to tenant changes)
  useEffect(()=>{
    (async()=>{
      if(!tenant){ setProfs([]); return }
      const rid = ++(setProfs as any).__rid || (((setProfs as any).__rid = 1))
      setProfsLoading(true)
      try{
        const list = await listProfessionalsFull(tenant)
        if (rid !== (setProfs as any).__rid) return
        setProfs(list)
      }catch{
        setProfs([])
      }finally{ if (rid === (setProfs as any).__rid) setProfsLoading(false) }
    })()
  },[tenant])

  // Load available slots when professional or date changes
  useEffect(() => {
    (async () => {
      if (!tenant || !form.professional_id || !form.date) {
        setAvailableSlots([]);
        return;
      }
      setSlotsLoading(true);
      try {
        // Use availability API to get slots for the selected date
        const res = await api.get(`/tenants/${tenant}/professionals/${encodeURIComponent(form.professional_id)}/availability`, {
          params: {
            from: form.date,
            to: form.date,
            channel: 'admin'
          }
        });
        
        // Map availability items to Slot shape
        const items: any[] = res.data;
        const mappedSlots: Slot[] = items.map(it => ({
          time: it.start.split('T')[1].substring(0, 5),
          status: it.blocked ? 'blocked' : (it.bookable ? 'available' : 'booked')
        }));

        // Create appointment: only show bookable (available) slots in the dropdown
        const availableOnly = mappedSlots.filter(s => s.status === 'available');
        setAvailableSlots(availableOnly);
        setForm(prev => ({
          ...prev,
          time: prev.time && availableOnly.some(s => s.time === prev.time) ? prev.time : ''
        }));
      } catch (err) {
        console.error('Failed to load slots', err);
        setAvailableSlots([]);
      } finally {
        setSlotsLoading(false);
      }
    })();
  }, [tenant, form.professional_id, form.date]);

  // Load available slots for reschedule when professional or date changes
  useEffect(() => {
    (async () => {
      const rk = rescheduleAppt?.professional_id || rescheduleAppt?.professional
      if (!tenant || !rk || !rescheduleDate) {
        setRescheduleSlots([]);
        return;
      }
      setRescheduleSlotsLoading(true);
      try {
        const res = await api.get(`/tenants/${tenant}/professionals/${encodeURIComponent(rk)}/availability`, {
          params: {
            from: rescheduleDate,
            to: rescheduleDate,
            channel: 'admin'
          }
        });
        
        const items: any[] = res.data;
        const mappedSlots: Slot[] = items.map(it => ({
          time: it.start.split('T')[1].substring(0, 5),
          status: it.blocked ? 'blocked' : (it.bookable ? 'available' : 'booked')
        }));

        setRescheduleSlots(mappedSlots.filter(s => s.status === 'available' || s.status === 'blocked'));
      } catch (err) {
        console.error('Failed to load reschedule slots', err);
        setRescheduleSlots([]);
      } finally {
        setRescheduleSlotsLoading(false);
      }
    })();
  }, [tenant, rescheduleAppt?.professional_id, rescheduleAppt?.professional, rescheduleDate]);

  async function onCreate(){
    if(!tenant) return
    try {
      const prof = profs.find(p => (p.professional_id || p.name) === form.professional_id)
      const payload = {
        tenant,
        customer_name: form.customer_name,
        customer_phone: form.customer_phone,
        professional: prof?.name || '',
        professional_id: prof?.professional_id || form.professional_id || undefined,
        time: form.time,
        date: form.date,
      }
      await createAppointment(tenant, payload)
      setOpen(false)
      setForm({customer_name:'',customer_phone:'',professional_id:'',time:'',date:filterDate})
      await load()
    } catch (err: any) {
      console.error('Failed to create appointment', err)
      const detail = err?.response?.data?.detail
      const detailStr = typeof detail === 'string' ? detail : JSON.stringify(detail || '')
      if (detailStr && (detailStr.includes('Booking blocked') || detailStr.includes('too many no-shows'))) {
        showAlert('This phone number is blocked from booking due to repeated no-shows. Use Settings → No-Show Blocked to reset if appropriate.', 'error')
      } else {
        showAlert('Failed to create appointment: ' + (detailStr || 'Unknown error'), 'error')
      }
    }
  }

  async function onCancel(id: string, reason: 'canceled' | 'needs_reschedule' = 'canceled'){
    if(!tenant) return
    await cancelAppointment(tenant, id, reason)
    await load()
  }

  function handleOpenReschedule(appt: Appointment) {
    setRescheduleAppt(appt)
    setRescheduleDate(appt.date || new Date().toISOString().split('T')[0])
    setRescheduleDateSetTime('')
    setOpenReschedule(true)
  }

  async function onReschedule() {
    if (!tenant || !rescheduleAppt || !rescheduleTime) return
    try {
      if (rescheduleTime === 'notify') {
        await onCancel(rescheduleAppt.id, 'needs_reschedule')
      } else {
        await rescheduleAppointment(tenant, rescheduleAppt.id, {
          new_time: rescheduleTime,
          new_date: rescheduleDate
        })
      }
      setOpenReschedule(false)
      await load()
    } catch (err: any) {
      console.error('Failed to reschedule', err)
      const detail = err?.response?.data?.detail
      const errorMsg = typeof detail === 'string' ? detail : JSON.stringify(detail)
      showAlert('Failed to reschedule: ' + (errorMsg || 'Unknown error'), 'error')
    }
  }

  async function onComplete(id: string) {
    if (!tenant) return
    try {
      await updateAppointmentStatus(tenant, id, 'completed')
      await load()
    } catch (err: any) {
      console.error('Failed to complete appointment', err)
      showAlert('Failed to complete appointment', 'error')
    }
  }

  async function onNoShow(id: string) {
    if (!tenant) return
    try {
      await updateAppointmentStatus(tenant, id, 'no_show')
      await load()
    } catch (err: any) {
      console.error('Failed to mark no show', err)
      const detail = err?.response?.data?.detail
      showAlert('Failed to mark no show: ' + (typeof detail === 'string' ? detail : 'Unknown error'), 'error')
    }
  }

  return (
    <Box sx={{ p:1 }}>
      <Stack direction={{ xs:'column', md:'row' }} justifyContent="space-between" alignItems="center" sx={{ mb:2 }} spacing={1}>
        <Typography variant="h5">Appointments</Typography>
        <Stack direction="row" spacing={1} alignItems="center">
          <TextField
            size="small"
            label="Search"
            placeholder="Name, mobile, or token"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            sx={{ minWidth: 200 }}
          />
          <TextField
              select
              size="small"
              label="Status"
              value={filterStatus}
              onChange={e => setFilterStatus(e.target.value)}
              sx={{ minWidth: 120 }}
            >
              <MenuItem value="">All Status</MenuItem>
              {APPOINTMENT_STATUS_OPTIONS.map(({ value, label }) => (
                <MenuItem key={value} value={value}>{label}</MenuItem>
              ))}
            </TextField>
          <TextField
            type="date"
            size="small"
            label="Date"
            value={filterDate}
            onChange={e => setFilterDate(e.target.value)}
            InputLabelProps={{ shrink: true }}
          />
          <TextField
            select
            size="small"
            label="Filter by Professional"
            value={filterProfessional}
            onChange={e => setFilterProfessional(e.target.value)}
            sx={{ minWidth: 200 }}
          >
            <MenuItem value="">All Professionals</MenuItem>
            {profs.map(p => {
              const k = p.professional_id || p.name
              return (
              <MenuItem key={k} value={k}>
                {p.name}{p.professional_id ? ` · ${p.professional_id.slice(0, 8)}…` : ''}
              </MenuItem>
              )
            })}
          </TextField>
          {canEditAppointments && (
          <Button variant="contained" startIcon={<AddIcon/>} onClick={()=>{
            setForm(prev=>({...prev, date: filterDate}))
            setOpen(true)
          }} disabled={!tenant}>New</Button>
          )}
          <ExportMenu
            data={items.map((a) => ({
              id: a.id,
              date: a.date ?? '',
              time: a.time,
              professional: a.professional,
              customer_name: a.customer_name,
              customer_phone: a.customer_phone,
              status: a.status,
              price: a.price,
              created_by: a.created_by ?? '',
              updated_by: a.updated_by ?? '',
            }))}
            columns={[
              { key: 'id', label: 'Token' },
              { key: 'date', label: 'Date' },
              { key: 'time', label: 'Time' },
              { key: 'professional', label: 'Professional' },
              { key: 'customer_name', label: 'Customer' },
              { key: 'customer_phone', label: 'Phone' },
              { key: 'status', label: 'Status' },
              { key: 'price', label: 'Price' },
              { key: 'created_by', label: 'Created By' },
              { key: 'updated_by', label: 'Updated By' },
            ]}
            filename="appointments"
            title="Appointments"
            disabled={loading}
            size="small"
          />
        </Stack>
      </Stack>
      <Card>
        <CardContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Token</TableCell>
                <TableCell>Date</TableCell>
                <TableCell>Time</TableCell>
                <TableCell>Professional</TableCell>
                <TableCell>Customer</TableCell>
                <TableCell>Phone</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Staff (C/U)</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map(a=> (
                <TableRow key={a.id}>
                  <TableCell><b>{a.id}</b></TableCell>
                  <TableCell>{formatDateForDisplay(a.date, dateFormat)}</TableCell>
                  <TableCell>{a.time}</TableCell>
                  <TableCell>{a.professional}</TableCell>
                  <TableCell>{a.customer_name}</TableCell>
                  <TableCell>{formatPhoneForDisplay(a.customer_phone)}</TableCell>
                  <TableCell>{getAppointmentStatusLabel(a.status)}</TableCell>
                  <TableCell>
                    <Typography variant="caption" display="block" color="text.secondary">
                      C: {a.created_by ?? '-'}
                    </Typography>
                    <Typography variant="caption" display="block" color="text.secondary">
                      U: {a.updated_by ?? '-'}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    {canEditAppointments ? (
                    <Stack direction="row" spacing={0.5} justifyContent="flex-end" flexWrap="wrap" useFlexGap>
                      {a.status === APPOINTMENT_STATUS.BOOKED && (
                        <>
                          <Button size="small" variant="contained" color="success" onClick={() => onComplete(a.id)}>Complete</Button>
                          <Button size="small" variant="outlined" color="error" onClick={() => onCancel(a.id)}>Cancel</Button>
                          <Button
                            size="small"
                            variant="outlined"
                            aria-label="More actions"
                            onClick={(e) => setActionMenuAnchor({ el: e.currentTarget, appt: a })}
                            sx={{ minWidth: 36 }}
                          >
                            <MoreVertIcon fontSize="small" />
                          </Button>
                        </>
                      )}
                      {a.status !== APPOINTMENT_STATUS.BLOCKED && a.status !== APPOINTMENT_STATUS.COMPLETED && a.status !== APPOINTMENT_STATUS.CANCELED && a.status !== APPOINTMENT_STATUS.NO_SHOW && a.status !== APPOINTMENT_STATUS.BOOKED && (
                        <>
                          {a.status !== APPOINTMENT_STATUS.NEEDS_RESCHEDULE && (
                            <Button size="small" variant="outlined" sx={{ borderColor: '#475569', color: '#e2e8f0' }} onClick={() => handleOpenReschedule(a)}>Reschedule</Button>
                          )}
                          <Button size="small" variant="outlined" color="error" onClick={() => onCancel(a.id)}>Cancel</Button>
                        </>
                      )}
                    </Stack>
                    ) : (
                      <Typography variant="body2" color="text.secondary">View only</Typography>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {!items.length && (
                <TableRow><TableCell colSpan={8}><Typography variant="body2" color="text.secondary">{loading? 'Loading...' : 'No appointments'}</Typography></TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={open} onClose={()=>setOpen(false)}>
        <DialogTitle>New Appointment</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt:1, minWidth: 360 }}>
            <TextField label="Customer Name" value={form.customer_name} onChange={e=>setForm(prev=>({...prev, customer_name:e.target.value}))} />
            <TextField label="Customer Phone" value={form.customer_phone} onChange={e=>setForm(prev=>({...prev, customer_phone:e.target.value}))} />
            <TextField
              type="date"
              label="Date"
              value={form.date}
              onChange={e => setForm(prev => ({ ...prev, date: e.target.value, time: '' }))}
              InputLabelProps={{ shrink: true }}
            />
            <TextField select label="Professional" value={form.professional_id} onChange={e=>{setForm(prev=>({...prev, professional_id:e.target.value, time: ''}))}} disabled={!tenant || profsLoading}>
              {profs.filter(p=> (p.active ?? true)).map(p=> {
                const k = p.professional_id || p.name
                return (
                <MenuItem key={k} value={k}>
                  {p.name}{p.professional_id ? ` · ${p.professional_id.slice(0, 8)}…` : ''}
                </MenuItem>
                )
              })}
              {(!profsLoading && profs.filter(p=> (p.active ?? true)).length===0) && (
                <MenuItem value="" disabled>No professionals available</MenuItem>
              )}
            </TextField>
            <TextField select label="Available Slots" value={form.time} onChange={e=>setForm(prev=>({...prev, time:e.target.value}))} disabled={!form.professional_id || slotsLoading}>
              {availableSlots.map(s => (
                <MenuItem key={s.time} value={s.time}>{s.time}</MenuItem>
              ))}
              {(!slotsLoading && form.professional_id && availableSlots.length === 0) && (
                <MenuItem value="" disabled>No available slots</MenuItem>
              )}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setOpen(false)}>Close</Button>
          <Button variant="contained" onClick={onCreate} disabled={!tenant || !form.professional_id || !form.time}>Create</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={openReschedule} onClose={()=>setOpenReschedule(false)}>
        <DialogTitle>Reschedule Appointment</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt:1, minWidth: 360 }}>
            <Typography variant="body2">Rescheduling appointment for <b>{rescheduleAppt?.customer_name}</b> with <b>{rescheduleAppt?.professional}</b>.</Typography>
            <TextField
              type="date"
              size="small"
              label="New Date"
              value={rescheduleDate}
              onChange={e => {
                setRescheduleDate(e.target.value)
                setRescheduleDateSetTime('')
              }}
              InputLabelProps={{ shrink: true }}
            />
            <TextField 
              select 
              label="Available Slots" 
              value={rescheduleTime} 
              onChange={e=>setRescheduleDateSetTime(e.target.value)} 
              disabled={!rescheduleDate || rescheduleSlotsLoading}
            >
              <MenuItem value="notify" sx={{ color: 'primary.main', fontWeight: 'bold' }}>Notify customer to reschedule (WhatsApp)</MenuItem>
              {rescheduleSlots.map(s => (
                <MenuItem key={s.time} value={s.time} disabled={s.status === 'blocked'}>
                  {s.time} {s.status === 'blocked' ? '(Blocked)' : ''}
                </MenuItem>
              ))}
              {(!rescheduleSlotsLoading && rescheduleDate && rescheduleSlots.length === 0) && (
                <MenuItem value="" disabled>No available slots on this date</MenuItem>
              )}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setOpenReschedule(false)}>Cancel</Button>
          <Button variant="contained" onClick={onReschedule} disabled={!rescheduleTime || rescheduleSlotsLoading}>Reschedule</Button>
        </DialogActions>
      </Dialog>

      <Menu
        anchorEl={actionMenuAnchor?.el ?? null}
        open={!!actionMenuAnchor}
        onClose={() => setActionMenuAnchor(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        {actionMenuAnchor?.appt && actionMenuAnchor.appt.status === APPOINTMENT_STATUS.BOOKED && (
          <>
            <MenuItem
              onClick={() => {
                onNoShow(actionMenuAnchor!.appt.id)
                setActionMenuAnchor(null)
              }}
            >
              No show
            </MenuItem>
            <MenuItem
              onClick={() => {
                handleOpenReschedule(actionMenuAnchor!.appt)
                setActionMenuAnchor(null)
              }}
            >
              Reschedule
            </MenuItem>
          </>
        )}
      </Menu>
    </Box>
  )
}
