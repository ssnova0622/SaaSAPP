import { useEffect, useState } from 'react'
import { Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Grid, List, ListItem, ListItemButton, ListItemText, MenuItem, Select, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography, IconButton } from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import SaveIcon from '@mui/icons-material/Save'
import { createProfessional, listProfessionalsFull, setProfessionalActive, updateProfessional, updateProfessionalSlots, Slot, ProfessionalFull } from '@api/professionals'
import { formatApiDetail } from '@api/errors'
import { listServices, TenantService } from '@api/services'
import { listAppointments, createAppointment, cancelAppointment, rescheduleAppointment, Appointment } from '@api/appointments'
import { api } from '@api/axios'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useCapabilities } from '../../hooks/useCapabilities'
import { getAppointmentStatusLabel } from '../../constants/appointmentStatus'
import { useAlert } from '@contexts/AlertContext'
import ExportMenu from '@components/ExportMenu'
import { displayE164FromEntity, formatEntityPhoneForDisplay } from '../../utils/phone'

export default function Professionals(){
  const { effectiveTenant } = useEffectiveTenant()
  const tenant = effectiveTenant
  const { canEditProfessionals, canManageProfessionalDetails, canCreateProfessional, canEditAppointments } = useCapabilities()
  const { showAlert, showConfirm } = useAlert()
  const [profs,setProfs]=useState<ProfessionalFull[]>([])
  const [selected,setSelected]=useState<string>('')
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0])
  const [slots,setSlots]=useState<Slot[]>([])
  const [appointments,setAppointments]=useState<Appointment[]>([])
  const [loading,setLoading]=useState(false)
  const [editText,setEditText]=useState('')
  const [filter, setFilter] = useState<'all' | 'booked' | 'available'>('all')
  const [bulkMode, setBulkMode] = useState<'global' | 'date'>('global')
  const [openSettings, setOpenSettings] = useState(false)
  const [editCrit, setEditCrit] = useState<'daily' | 'weekly' | 'monthly'>('daily')
  const [editDays, setEditDays] = useState<string>('')

  const [openAdd,setOpenAdd]=useState(false)
  const [editMode, setEditMode] = useState(false)
  const [newName,setNewName]=useState('')
  const [newPrice,setNewPrice]=useState<number>(0)
  const [newPhone, setNewPhone] = useState('')
  const [newDegree, setNewDegree] = useState('')
  const [newAddress, setNewAddress] = useState('')
  const [newBio, setNewBio] = useState('')
  const [newEmployeeId, setNewEmployeeId] = useState('')
  const [slotIntervalMinutes, setSlotIntervalMinutes] = useState<number>(30)
  const [workStart, setWorkStart] = useState('09:00')
  const [workEnd, setWorkEnd] = useState('18:00')
  const [newAvailCrit, setNewAvailCrit] = useState<'daily' | 'weekly' | 'monthly'>('daily')
  const [newAvailDays, setNewAvailDays] = useState('')
  const [newSelectedServices, setNewSelectedServices] = useState<string[]>([])
  const [availableServices, setAvailableServices] = useState<TenantService[]>([])

  const [openBook,setOpenBook]=useState(false)
  const [bookTime,setBookTime]=useState('')
  const [custName,setCustName]=useState('')
  const [custPhone,setCustPhone]=useState('')

  const [openReschedule, setOpenReschedule] = useState(false)
  const [rescheduleAppt, setRescheduleAppt] = useState<Appointment | null>(null)
  const [rescheduleDate, setRescheduleDate] = useState<string>('')
  const [rescheduleTime, setRescheduleTime] = useState<string>('')
  const [rescheduleSlots, setRescheduleSlots] = useState<Slot[]>([])
  const [rescheduleSlotsLoading, setRescheduleSlotsLoading] = useState(false)

  async function loadList(){
    if(!tenant) return
    const rid = ++(loadList as any).__rid || (((loadList as any).__rid = 1))
    try {
      const [list, svcs] = await Promise.all([
        listProfessionalsFull(tenant),
        listServices(tenant).catch(() => [])
      ])
      if (rid !== (loadList as any).__rid) return
      setProfs(list || [])
      setAvailableServices(svcs || [])
    } catch (e: any) {
      if (rid !== (loadList as any).__rid) return
      setProfs([])
      setAvailableServices([])
      const msg = e?.response?.data?.detail || e?.message || 'Failed to load professionals'
      showAlert(typeof msg === 'string' ? msg : 'Failed to load professionals', 'error')
    }
  }
  async function loadData(name: string, date: string){
    if(!tenant || !name) return
    const rid = ++(loadData as any).__rid || (((loadData as any).__rid = 1))
    setLoading(true)
    try {
      // 1. Fetch appointments for this specific date to determine booked status
      // 2. Fetch professional's base template slots
      // 3. (Optional but better) Use availability API which already combines these
      
      const res = await api.get(`/tenants/${tenant}/professionals/${encodeURIComponent(name)}/availability`, {
        params: {
          from: date,
          to: date,
          channel: 'admin'
        }
      });
      
      const availItems: any[] = res.data;
      const mappedSlots: Slot[] = availItems.map(it => ({
        time: it.start.split('T')[1].substring(0, 5),
        status: it.blocked ? 'blocked' : (it.bookable ? 'available' : 'booked')
      }));

      const ap = await listAppointments(tenant, { date })
      
      if (rid !== (loadData as any).__rid) return
      setSlots(mappedSlots)
      setEditText(mappedSlots.map(x=>x.time).join(', '))
      setAppointments(ap)
    } finally { if (rid === (loadData as any).__rid) setLoading(false) }
  }

  useEffect(()=>{ loadList() // eslint-disable-next-line
  },[tenant])

  useEffect(()=>{ if(selected) loadData(selected, selectedDate) },[selected, selectedDate])

  // Load available slots for reschedule when professional or date changes
  useEffect(() => {
    (async () => {
      if (!tenant || !selected || !rescheduleDate) {
        setRescheduleSlots([]);
        return;
      }
      setRescheduleSlotsLoading(true);
      try {
        const res = await api.get(`/tenants/${tenant}/professionals/${encodeURIComponent(selected)}/availability`, {
          params: {
            from: rescheduleDate,
            to: rescheduleDate,
            channel: 'admin'
          }
        });
        
        const items: any[] = res.data;
        const mappedSlots: Slot[] = items.map(it => ({
          time: it.start.split('T')[1].substring(0, 5),
          status: it.bookable ? 'available' : (it.remaining === 0 ? 'booked' : 'blocked')
        }));

        setRescheduleSlots(mappedSlots.filter(s => s.status === 'available'));
      } catch (err) {
        console.error('Failed to load reschedule slots', err);
        setRescheduleSlots([]);
      } finally {
        setRescheduleSlotsLoading(false);
      }
    })();
  }, [tenant, selected, rescheduleDate]);

  function parseTimes(text: string): string[]{
    return text.split(',').map(t=>t.trim()).filter(Boolean)
  }

  const selectedProf = profs.find(
    p =>
      (p.professional_id && p.professional_id === selected) ||
      (!p.professional_id && p.name === selected)
  )
  const isSelectedActive = selectedProf?.active ?? true

  async function onSaveSlots(){
    if(!tenant || !selected) return
    const times = parseTimes(editText)
    const dateParam = bulkMode === 'date' ? selectedDate : undefined
    await updateProfessionalSlots(tenant, selected, times, dateParam)
    // After bulk editing, refresh using loadData to pick up any appointments on current date
    await loadData(selected, selectedDate)
  }

  async function onSaveProfessional() {
    if (!tenant) return
    if (editMode) {
        if (!selected) return
      // Update existing
      try {
        await updateProfessional(tenant, selected, {
          price: newPrice,
          services: newSelectedServices,
          phone: newPhone,
          degree: newDegree,
          address: newAddress,
          bio: newBio
        })
        setOpenAdd(false)
        await loadList()
      } catch (err) {
        console.error('Update failed', err)
        showAlert(formatApiDetail(err), 'error')
      }
    } else {
      await onCreate()
    }
  }

  function openEditDialog(p: ProfessionalFull) {
    setEditMode(true)
    setNewName(p.name)
    setNewPrice(p.price || 0)
    setNewPhone(displayE164FromEntity(p) || p.phone || '')
    setNewDegree(p.degree || '')
    setNewAddress(p.address || '')
    setNewBio(p.bio || '')
    setNewSelectedServices(p.services || [])
    setNewEmployeeId(p.employee_id || '')
    setOpenAdd(true)
  }

  function openAddDialog() {
    setEditMode(false)
    setNewName('')
    setNewPrice(0)
    setNewPhone('')
    setNewDegree('')
    setNewAddress('')
    setNewBio('')
    setNewSelectedServices([])
    setNewEmployeeId('')
    setSlotIntervalMinutes(30)
    setWorkStart('09:00')
    setWorkEnd('18:00')
    setNewAvailCrit('daily')
    setNewAvailDays('')
    setOpenAdd(true)
  }

  async function onCreate(){
    if(!tenant || !newName || !newEmployeeId.trim()) return
    const daysArr = newAvailDays.split(',').map(d => parseInt(d.trim(), 10)).filter(d => !Number.isNaN(d))
    try {
      const created = await createProfessional(tenant, { 
        name: newName, 
        employee_id: newEmployeeId.trim(),
        price: newPrice, 
        slot_interval_minutes: slotIntervalMinutes,
        work_start: workStart,
        work_end: workEnd,
        availability_criteria: newAvailCrit,
        available_days: daysArr,
        services: newSelectedServices,
        phone: newPhone,
        degree: newDegree,
        address: newAddress,
        bio: newBio
      })
      setOpenAdd(false)
      setNewName(''); setNewPrice(0); setNewSelectedServices([]); 
      setNewPhone(''); setNewDegree(''); setNewAddress(''); setNewBio('');
      setNewEmployeeId('')
      await loadList()
      const pid = (created as { professional_id?: string }).professional_id
      setSelected(pid || newName)
    } catch (err) {
      console.error('Creation failed', err)
      showAlert(formatApiDetail(err), 'error')
    }
  }

  function apptForTime(time: string, status: string | string[] = 'booked'): Appointment | undefined {
    const matchesPro = (a: Appointment) => {
      if (a.professional_id && selected) return a.professional_id === selected
      return a.professional === selectedProf?.name
    }
    if (Array.isArray(status)) {
      return appointments.find(a => matchesPro(a) && a.time === time && status.includes(a.status))
    }
    return appointments.find(a => matchesPro(a) && a.time === time && a.status === status)
  }

  const filteredSlots = slots.map(s => {
    const bookedAppt = apptForTime(s.time, ['booked', 'needs_reschedule'])
    let displayStatus: 'booked' | 'available' | 'blocked' = s.status as any
    // availability API returns 'blocked' if the slot is blocked in overrides.
    // If there is an appointment, we show it as booked for filtering purposes,
    // but we'll use s.status to determine if it's truly blocked.
    if (bookedAppt && s.status !== 'blocked') displayStatus = 'booked'
    
    return { ...s, displayStatus, bookedAppt }
  })
  
  // Apply filtering based on displayStatus
  .filter(s => {
    if (filter === 'all') return true
    if (filter === 'booked') return s.displayStatus === 'booked'
    if (filter === 'available') return s.displayStatus === 'available'
    if (filter === 'blocked') return s.displayStatus === 'blocked'
    return true
  })

  async function onStatusChange(time: string, next: 'available'|'booked'|'blocked'){
    if(!tenant || !selected) return
    if(next === 'booked'){
      // open booking dialog
      setBookTime(time)
      setCustName('')
      setCustPhone('')
      setOpenBook(true)
    } else if (next === 'blocked') {
      const ap = apptForTime(time)
      if (ap) {
        const ok = await showConfirm({
          title: 'Reschedule',
          message: `This slot is already booked by ${ap.customer_name}. You must reschedule it to block this slot. Open reschedule dialog?`,
        })
        if (ok) handleOpenReschedule(ap)
        return
      }
      setLoading(true)
      try {
        await api.patch(`/tenants/${tenant}/professionals/${encodeURIComponent(selected)}/slots/${time}`, { status: 'blocked' }, { params: { date: selectedDate } })
      } finally {
        setLoading(false)
      }
      await loadData(selected, selectedDate)
    } else {
      // available
      // Check if there is a blocked slot (not an appointment)
      const slot = slots.find(s => s.time === time)
      if (slot && slot.status === 'blocked') {
        setLoading(true)
        try {
          await api.patch(`/tenants/${tenant}/professionals/${encodeURIComponent(selected)}/slots/${time}`, { status: 'available' }, { params: { date: selectedDate } })
        } finally {
          setLoading(false)
        }
      } else {
        // cancel existing appointment for this pro+time if exists
        const ap = apptForTime(time)
        if(ap){
          const cancelCompletely = await showConfirm({
            title: 'Cancel appointment',
            message: 'Cancel this appointment completely? Click "No" to just mark as "Needs Reschedule".',
            confirmLabel: 'Yes, cancel',
            cancelLabel: 'No, mark Needs Reschedule',
          })
          const reason = cancelCompletely ? 'canceled' : 'needs_reschedule'
          if (reason === 'needs_reschedule') {
             const ok = await showConfirm({
               title: 'Needs reschedule',
               message: 'Mark this appointment as needing reschedule? Customer will be notified.',
             })
             if (!ok) {
               await loadData(selected, selectedDate)
               return
             }
          }
          
          setLoading(true)
          try {
            await cancelAppointment(tenant, ap.id, reason as any)
          } finally {
            setLoading(false)
          }
        }
      }
      await loadData(selected, selectedDate)
    }
  }

  async function confirmBooking(){
    if(!tenant || !selected || !bookTime) return
    setLoading(true)
    try {
      await createAppointment(tenant, { 
        tenant, 
        customer_name: custName || 'Walk-in', 
        customer_phone: custPhone || 'NA', 
        professional: selectedProf?.name || '', 
        professional_id: selected || undefined,
        time: bookTime,
        date: selectedDate
      })
    } finally {
      setLoading(false)
    }
    setOpenBook(false)
    await loadData(selected, selectedDate)
  }

  function handleOpenReschedule(appt: Appointment) {
    setRescheduleAppt(appt)
    setRescheduleDate(selectedDate)
    setRescheduleTime('')
    setOpenReschedule(true)
  }

  async function onReschedule() {
    if (!tenant || !rescheduleAppt || !rescheduleTime) return
    setLoading(true)
    try {
      if (rescheduleTime === 'notify') {
        await cancelAppointment(tenant, rescheduleAppt.id, 'needs_reschedule')
      } else {
        await rescheduleAppointment(tenant, rescheduleAppt.id, {
          new_time: rescheduleTime,
          new_date: rescheduleDate
        })
      }
      setOpenReschedule(false)
      await loadData(selected!, selectedDate)
    } catch (err) {
      console.error('Failed to reschedule', err)
      showAlert('Failed to reschedule: ' + ((err as any)?.response?.data?.detail || 'Unknown error'), 'error')
    } finally {
      setLoading(false)
    }
  }

  async function onToggleActive(){
    if(!tenant || !selected) return
    const next = !(selectedProf?.active ?? true)
    await setProfessionalActive(tenant, selected, next)
    await loadList()
  }

  async function onSaveSettings(){
    if(!tenant || !selected) return
    setLoading(true)
    try {
      const daysArr = editDays.split(',').map(d => parseInt(d.trim())).filter(d => !isNaN(d))
      await updateProfessional(tenant, selected, {
        availability_criteria: editCrit,
        available_days: daysArr
      })
      setOpenSettings(false)
      await loadList()
    } finally {
      setLoading(false)
    }
  }

  function openSettingsDialog(){
    if(!selectedProf) return
    setEditCrit(selectedProf.availability_criteria || 'daily')
    setEditDays((selectedProf.available_days || []).join(', '))
    setOpenSettings(true)
  }

  return (
    <Box sx={{ p:1 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb:2 }}>
        <Typography variant="h5">Professionals</Typography>
        <ExportMenu
          data={profs.map((p) => ({
            professional_id: p.professional_id ?? '',
            employee_id: p.employee_id ?? '',
            name: p.name,
            price: p.price ?? '',
            active: (p.active ?? true) ? 'Active' : 'Inactive',
            services: (p.services || []).join(', '),
            phone: formatEntityPhoneForDisplay(p) || '',
            degree: p.degree ?? '',
            address: p.address ?? '',
            availability_criteria: p.availability_criteria ?? 'daily',
            available_days: (p.available_days || []).join(', '),
            created_by: p.created_by ?? '',
            updated_by: p.updated_by ?? '',
          }))}
          columns={[
            { key: 'professional_id', label: 'Professional ID' },
            { key: 'employee_id', label: 'Employee ID' },
            { key: 'name', label: 'Name' },
            { key: 'price', label: 'Price' },
            { key: 'active', label: 'Status' },
            { key: 'services', label: 'Services' },
            { key: 'phone', label: 'Phone' },
            { key: 'degree', label: 'Degree' },
            { key: 'address', label: 'Address' },
            { key: 'availability_criteria', label: 'Availability Criteria' },
            { key: 'available_days', label: 'Available Days' },
            { key: 'created_by', label: 'Created By' },
            { key: 'updated_by', label: 'Updated By' },
          ]}
          filename="professionals"
          title="Professionals"
          disabled={!profs.length}
          size="small"
        />
      </Stack>
      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb:1 }}>
                <Typography variant="subtitle1">List</Typography>
                {canCreateProfessional && (
                <Button size="small" variant="contained" startIcon={<AddIcon/>} onClick={openAddDialog} disabled={!tenant}>Add</Button>
              )}
              </Stack>
              <List dense>
                {profs.map(p=> {
                  const rowKey = p.professional_id || p.name
                  return (
                  <ListItem key={rowKey} disablePadding secondaryAction={
                    <Stack direction="row" spacing={0.5} alignItems="center">
                      {canManageProfessionalDetails && (
                      <IconButton size="small" onClick={() => openEditDialog(p)} title="Edit professional details (fees, contact)"><SaveIcon fontSize="small" /></IconButton>
                    )}
                      <Chip size="small" label={(p.active??true)?'Active':'Inactive'} color={(p.active??true)?'success':'default'} />
                    </Stack>
                  }>
                    <ListItemButton selected={selected===rowKey} onClick={()=>setSelected(rowKey)}>
                      <ListItemText 
                        primary={p.name} 
                        secondary={
                          <Box component="span">
                            {p.professional_id && (
                              <Typography variant="caption" display="block" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                                ID: {p.professional_id}
                              </Typography>
                            )}
                            {p.employee_id && (
                              <Typography variant="caption" display="block" color="text.secondary">
                                Employee: {p.employee_id}
                              </Typography>
                            )}
                            {p.services && p.services.length > 0 && (
                                <Box sx={{ mt: 0.5, mb: 0.5, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                    {p.services.map(s => <Chip key={s} label={s} size="small" variant="outlined" sx={{ height: 18, fontSize: '0.65rem' }} />)}
                                </Box>
                            )}
                            <Typography variant="caption" display="block" color="text.secondary">
                              C: {p.created_by ?? '-'}
                            </Typography>
                            <Typography variant="caption" display="block" color="text.secondary">
                              U: {p.updated_by ?? '-'}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItemButton>
                  </ListItem>
                )})}
                {!profs.length && <Typography variant="body2" color="text.secondary">No professionals</Typography>}
              </List>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={8}>
          <Card sx={{ mb:2 }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb:1 }}>
                <Typography variant="subtitle1">Slots (interactive) {selectedProf ? `for ${selectedProf.name}` : ''}</Typography>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Select
                    size="small"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value as any)}
                    sx={{ minWidth: 120 }}
                  >
                    <MenuItem value="all">All</MenuItem>
                    <MenuItem value="available">Available</MenuItem>
                    <MenuItem value="booked">Booked</MenuItem>
                    <MenuItem value="blocked">Blocked</MenuItem>
                  </Select>
                  <TextField
                    type="date"
                    size="small"
                    label="Date"
                    value={selectedDate}
                    onChange={e => setSelectedDate(e.target.value)}
                    InputLabelProps={{ shrink: true }}
                  />
                  <Button size="small" variant="outlined" onClick={() => loadData(selected, selectedDate)} disabled={!tenant || !selected}>Refresh</Button>
                  {selected && canEditProfessionals && (
                    <Button size="small" variant="outlined" onClick={openSettingsDialog}>Availability</Button>
                  )}
                  {selected && canEditProfessionals && (
                    <Button size="small" onClick={onToggleActive} disabled={!tenant}>{isSelectedActive ? 'Deactivate' : 'Activate'}</Button>
                  )}
                </Stack>
              </Stack>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Time</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredSlots.map(s => {
                    const ap = s.bookedAppt
                    const isNeedsReschedule = ap?.status === 'needs_reschedule'
                    const isBlocked = s.status === 'blocked'
                    const isBooked = (ap !== undefined || isNeedsReschedule)
                    
                    // The value for the dropdown:
                    // Priority: Blocked (staff explicitly disabled it) > Booked (has an appointment) > Available
                    const value = isBlocked ? 'blocked' : (isBooked ? 'booked' : 'available')
                    
                    let rowBg = undefined
                    if (isNeedsReschedule) rowBg = 'rgba(255, 152, 0, 0.08)'
                    else if (isBooked) rowBg = 'rgba(25, 118, 210, 0.08)'
                    else if (isBlocked) rowBg = 'rgba(0, 0, 0, 0.08)'

                    return (
                      <TableRow key={s.time} sx={{ bgcolor: rowBg }}>
                        <TableCell sx={{ fontWeight: isBooked ? 600 : undefined }}>{s.time}</TableCell>
                        <TableCell>
                          <Select size="small" value={value} onChange={(e)=>onStatusChange(s.time, e.target.value as any)} disabled={!selected || !isSelectedActive || !canEditProfessionals}
                          sx={{ 
                            minWidth: 140, 
                            bgcolor: isNeedsReschedule ? 'rgba(255, 152, 0, 0.12)' : (isBooked && !isBlocked ? 'rgba(76, 175, 80, 0.08)' : (isBlocked ? 'rgba(0,0,0,0.12)' : undefined))
                          }}>
                            <MenuItem value="available">available</MenuItem>
                            <MenuItem value="booked">booked</MenuItem>
                            <MenuItem value="blocked">blocked</MenuItem>
                          </Select>
                          {isNeedsReschedule && ap && (
                            <Typography variant="caption" color="warning.main" sx={{ display: 'block', mt: 0.5 }}>
                              {getAppointmentStatusLabel(ap.status)}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell align="right">
                          {(isBooked || isBlocked) && ap && canEditAppointments ? (
                            <Stack direction="row" spacing={1} justifyContent="flex-end">
                              <Button size="small" variant="outlined" onClick={() => handleOpenReschedule(ap)} disabled={!isSelectedActive || loading}>Reschedule</Button>
                              <Button size="small" color="error" onClick={async()=>{ 
                                const ok = await showConfirm({ title: 'Cancel appointment', message: 'Cancel this appointment?' });
                                if (ok) { 
                                  setLoading(true);
                                  try {
                                    await cancelAppointment(tenant!, ap.id); 
                                  } finally {
                                    setLoading(false);
                                  }
                                  await loadData(selected!, selectedDate) 
                                } 
                              }} disabled={!isSelectedActive || loading}>Cancel</Button>
                            </Stack>
                          ) : (
                            canEditAppointments ? (
                              <Button size="small" variant="outlined" onClick={()=>onStatusChange(s.time, 'booked')} disabled={!selected || !isSelectedActive || loading}>Book</Button>
                            ) : null
                          )}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                  {!filteredSlots.length && (
                    <TableRow><TableCell colSpan={3}><Typography variant="body2" color="text.secondary">{loading? 'Loading...' : 'No slots'}</Typography></TableCell></TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <Typography variant="subtitle1" sx={{ mb:1 }}>Bulk edit slots (comma‑separated)</Typography>
              <Stack spacing={2}>
                <Stack direction="row" spacing={2} alignItems="center">
                  <Typography variant="body2">Apply to:</Typography>
                  <Select
                    size="small"
                    value={bulkMode}
                    onChange={(e) => setBulkMode(e.target.value as any)}
                    sx={{ minWidth: 150 }}
                  >
                    <MenuItem value="global">Global Template</MenuItem>
                    <MenuItem value="date">Selected Date Only</MenuItem>
                  </Select>
                  {bulkMode === 'date' && (
                    <Chip label={selectedDate} size="small" color="primary" variant="outlined" />
                  )}
                </Stack>
                <TextField label="Times (comma separated)" value={editText} onChange={e=>setEditText(e.target.value)} multiline minRows={3} disabled={!selected || !isSelectedActive} />
                <Stack direction="row" spacing={2}>
                  <Button variant="contained" startIcon={<SaveIcon/>} onClick={onSaveSlots} disabled={!tenant || !selected || !isSelectedActive || !canEditProfessionals}>Save Slots</Button>
                </Stack>
                <Typography variant="body2" color="text.secondary">Current: {slots.map(s=>{
                  const booked = apptForTime(s.time, 'booked')
                  return `${s.time}${booked?' (booked)':''}`
                }).join(', ') || (loading?'Loading...':'—')}</Typography>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Add/Edit professional dialog */}
      <Dialog open={openAdd} onClose={()=>setOpenAdd(false)}>
        <DialogTitle>{editMode ? 'Edit Professional' : 'New Professional'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt:1, minWidth: 360 }}>
            <TextField label="Name" value={newName} onChange={e=>setNewName(e.target.value)} size="small" disabled={editMode} />
            <TextField
              label="Employee ID"
              value={newEmployeeId}
              onChange={e=>setNewEmployeeId(e.target.value)}
              size="small"
              disabled={editMode}
              helperText={editMode ? 'Employee ID cannot be changed here' : 'Unique per tenant'}
              required={!editMode}
            />
            <TextField label="Price" type="number" value={newPrice} onChange={e=>setNewPrice(Number(e.target.value))} size="small" />
            <TextField label="Phone" value={newPhone} onChange={e=>setNewPhone(e.target.value)} size="small" />
            <TextField label="Degree / Qualification" value={newDegree} onChange={e=>setNewDegree(e.target.value)} size="small" />
            <TextField label="Address" value={newAddress} onChange={e=>setNewAddress(e.target.value)} size="small" multiline rows={2} />
            <TextField label="Bio / Description" value={newBio} onChange={e=>setNewBio(e.target.value)} size="small" multiline rows={3} />
            <TextField select label="Services" SelectProps={{ multiple: true }} value={newSelectedServices} onChange={e=>setNewSelectedServices(typeof e.target.value === 'string' ? e.target.value.split(',') : e.target.value)} size="small">
                {availableServices.map(s => (
                    <MenuItem key={s.name} value={s.name}>{s.name}</MenuItem>
                ))}
            </TextField>
            {!editMode && (
              <>
                <TextField
                  select
                  label="Slot interval"
                  size="small"
                  value={slotIntervalMinutes}
                  onChange={e => setSlotIntervalMinutes(Number(e.target.value))}
                >
                  {[15, 20, 30, 45, 60].map(m => (
                    <MenuItem key={m} value={m}>{m} minutes</MenuItem>
                  ))}
                </TextField>
                <Stack direction="row" spacing={2}>
                  <TextField
                    label="Work start"
                    type="time"
                    value={workStart}
                    onChange={e => setWorkStart(e.target.value)}
                    size="small"
                    InputLabelProps={{ shrink: true }}
                    inputProps={{ step: 300 }}
                  />
                  <TextField
                    label="Work end"
                    type="time"
                    value={workEnd}
                    onChange={e => setWorkEnd(e.target.value)}
                    size="small"
                    InputLabelProps={{ shrink: true }}
                    inputProps={{ step: 300 }}
                  />
                </Stack>
                <TextField select label="Availability" size="small" value={newAvailCrit} onChange={e => setNewAvailCrit(e.target.value as any)}>
                  <MenuItem value="daily">Daily (every day)</MenuItem>
                  <MenuItem value="weekly">Weekly (use day indices below)</MenuItem>
                  <MenuItem value="monthly">Monthly (use dates below)</MenuItem>
                </TextField>
                <TextField
                  label={newAvailCrit === 'weekly' ? 'Days (0=Mon … 6=Sun, comma-separated)' : 'Days / dates (comma-separated)'}
                  value={newAvailDays}
                  onChange={e => setNewAvailDays(e.target.value)}
                  size="small"
                  placeholder={newAvailCrit === 'monthly' ? 'e.g. 1, 15' : 'e.g. 0, 1, 2'}
                  helperText="Ignored when availability is daily"
                />
              </>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setOpenAdd(false)}>Cancel</Button>
          <Button variant="contained" onClick={onSaveProfessional} disabled={!tenant || !newName || (!editMode && !newEmployeeId.trim())}>{editMode ? 'Save' : 'Create'}</Button>
        </DialogActions>
      </Dialog>

      {/* Booking dialog */}
      <Dialog open={openBook} onClose={()=>setOpenBook(false)}>
        <DialogTitle>Book slot {bookTime}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt:1, minWidth: 360 }}>
            <TextField label="Customer Name" value={custName} onChange={e=>setCustName(e.target.value)} />
            <TextField label="Customer Phone" value={custPhone} onChange={e=>setCustPhone(e.target.value)} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setOpenBook(false)}>Cancel</Button>
          <Button variant="contained" onClick={confirmBooking} disabled={!tenant || !selected}>Confirm</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={openReschedule} onClose={()=>setOpenReschedule(false)}>
        <DialogTitle>Reschedule Appointment</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt:1, minWidth: 360 }}>
            <Typography variant="body2">Rescheduling appointment for <b>{rescheduleAppt?.customer_name}</b> with <b>{selected}</b>.</Typography>
            <TextField
              type="date"
              size="small"
              label="New Date"
              value={rescheduleDate}
              onChange={e => setRescheduleDate(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
            <TextField 
              select 
              label="Available Slots" 
              value={rescheduleTime} 
              onChange={e=>setRescheduleTime(e.target.value)} 
              disabled={!rescheduleDate || rescheduleSlotsLoading}
            >
              <MenuItem value="notify" sx={{ color: 'primary.main', fontWeight: 'bold' }}>Notify customer to reschedule (WhatsApp)</MenuItem>
              {rescheduleSlots.map(s => (
                <MenuItem key={s.time} value={s.time}>{s.time}</MenuItem>
              ))}
              {(!rescheduleSlotsLoading && rescheduleDate && rescheduleSlots.length === 0) && (
                <MenuItem value="" disabled>No available slots on this date</MenuItem>
              )}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setOpenReschedule(false)}>Cancel</Button>
          <Button variant="contained" onClick={onReschedule} disabled={!rescheduleTime || rescheduleSlotsLoading || loading}>Reschedule</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={openSettings} onClose={()=>setOpenSettings(false)}>
        <DialogTitle>Availability Settings for {selected}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt:1, minWidth: 360 }}>
            <TextField select label="Criteria" value={editCrit} onChange={e=>setEditCrit(e.target.value as any)}>
              <MenuItem value="daily">Daily (available every day)</MenuItem>
              <MenuItem value="weekly">Weekly (available on specific days of week)</MenuItem>
              <MenuItem value="monthly">Monthly (available on specific dates of month)</MenuItem>
            </TextField>
            {editCrit === 'weekly' && (
              <Box>
                <Typography variant="body2" sx={{ mb: 1 }}>Select Days:</Typography>
                <Stack direction="row" flexWrap="wrap" spacing={1}>
                  {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, index) => {
                    const daysArr = editDays.split(',').map(d => d.trim()).filter(Boolean)
                    const isSelected = daysArr.includes(index.toString())
                    return (
                      <Chip
                        key={day}
                        label={day}
                        color={isSelected ? 'primary' : 'default'}
                        onClick={() => {
                          let newArr
                          if (isSelected) {
                            newArr = daysArr.filter(d => d !== index.toString())
                          } else {
                            newArr = [...daysArr, index.toString()]
                          }
                          setEditDays(newArr.sort().join(', '))
                        }}
                        sx={{ mb: 1 }}
                      />
                    )
                  })}
                </Stack>
              </Box>
            )}
            {editCrit === 'monthly' && (
              <TextField 
                label="Dates (1-31)" 
                value={editDays} 
                onChange={e=>setEditDays(e.target.value)} 
                placeholder="e.g. 1, 15, 30"
                helperText="Comma separated values"
                fullWidth
              />
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setOpenSettings(false)}>Cancel</Button>
          <Button variant="contained" onClick={onSaveSettings} disabled={loading}>Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
