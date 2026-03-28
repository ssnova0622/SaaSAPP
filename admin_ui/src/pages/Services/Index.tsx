import { useState, useEffect } from 'react'
import { Box, Typography, Card, CardContent, Table, TableHead, TableRow, TableCell, TableBody, Stack, Button, IconButton, Dialog, DialogTitle, DialogContent, DialogActions, TextField, Switch } from '@mui/material'
import { Delete as DeleteIcon, Edit as EditIcon, Add as AddIcon } from '@mui/icons-material'
import { listServices, createService, updateService, deleteService, TenantService } from '@api/services'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { useCapabilities } from '../../hooks/useCapabilities'
import { useAlert } from '@contexts/AlertContext'
import ExportMenu from '@components/ExportMenu'

export default function ServicesPage() {
  const { effectiveTenant: tenant } = useEffectiveTenant()
  const { canEditServices } = useCapabilities()
  const { showAlert, showConfirm } = useAlert()
  const [services, setServices] = useState<TenantService[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [editingService, setEditingService] = useState<Partial<TenantService>>({})
  const [isEdit, setIsEdit] = useState(false)

  const loadServices = async () => {
    if (!tenant) return
    setLoading(true)
    try {
      const data = await listServices(tenant)
      setServices(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadServices()
  }, [tenant])

  const handleSave = async () => {
    if (!tenant || !editingService.name) return
    try {
      if (isEdit) {
        const { name, tenant: t, ...updates } = editingService
        await updateService(tenant, name!, updates)
      } else {
        await createService(tenant, editingService)
      }
      setOpen(false)
      loadServices()
    } catch (e: any) {
      showAlert(e.response?.data?.detail || 'Failed to save service', 'error')
    }
  }

  const handleDelete = async (name: string) => {
    if (!tenant) return
    const ok = await showConfirm({ title: 'Delete service', message: `Delete service "${name}"?` })
    if (!ok) return
    try {
      await deleteService(tenant, name)
      loadServices()
    } catch (e) {
      showAlert('Failed to delete service', 'error')
    }
  }

  const handleToggleActive = async (service: TenantService) => {
    if (!tenant) return
    try {
      await updateService(tenant, service.name, { active: !service.active })
      loadServices()
    } catch (e) {
      showAlert('Failed to update service status', 'error')
    }
  }

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h5">Tenant Services</Typography>
        <Stack direction="row" spacing={1} alignItems="center">
          <ExportMenu
            data={services}
            columns={[{ key: 'name', label: 'Name' }, { key: 'description', label: 'Description' }, { key: 'price', label: 'Price' }, { key: 'duration', label: 'Duration (min)' }, { key: 'active', label: 'Active' }]}
            filename="services"
            title="Services"
            size="small"
            disabled={!tenant || services.length === 0}
          />
          {canEditServices && (
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => { setEditingService({ active: true, price: 0, duration: 30 }); setIsEdit(false); setOpen(true); }} disabled={!tenant}>
            New Service
          </Button>
          )}
        </Stack>
      </Stack>

      <Card>
        <CardContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Description</TableCell>
                <TableCell>Price</TableCell>
                <TableCell>Duration (min)</TableCell>
                <TableCell>Active</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {services.map((s) => (
                <TableRow key={s.name}>
                  <TableCell sx={{ fontWeight: 'bold' }}>{s.name}</TableCell>
                  <TableCell>{s.description}</TableCell>
                  <TableCell>{s.price}</TableCell>
                  <TableCell>{s.duration}</TableCell>
                  <TableCell>
                    {canEditServices ? (
                      <Switch checked={s.active} onChange={() => handleToggleActive(s)} size="small" />
                    ) : (
                      <Typography variant="body2">{s.active ? 'Yes' : 'No'}</Typography>
                    )}
                  </TableCell>
                  <TableCell align="right">
                    {canEditServices && (
                      <>
                        <IconButton size="small" onClick={() => { setEditingService(s); setIsEdit(true); setOpen(true); }}>
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton size="small" color="error" onClick={() => handleDelete(s.name)}>
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {!services.length && !loading && (
                <TableRow>
                  <TableCell colSpan={6} align="center">No services configured. Add one to categorize professionals.</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>{isEdit ? 'Edit Service' : 'New Service'}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField 
              label="Service Name" 
              fullWidth 
              size="small" 
              value={editingService.name || ''} 
              onChange={(e) => setEditingService({ ...editingService, name: e.target.value })}
              disabled={isEdit}
              placeholder="e.g. Dentist, Eye Doctor, Hair Cut"
            />
            <TextField 
              label="Description" 
              fullWidth 
              size="small" 
              multiline 
              rows={2}
              value={editingService.description || ''} 
              onChange={(e) => setEditingService({ ...editingService, description: e.target.value })}
            />
            <Stack direction="row" spacing={2}>
              <TextField 
                label="Base Price" 
                type="number" 
                fullWidth 
                size="small" 
                value={editingService.price || 0} 
                onChange={(e) => setEditingService({ ...editingService, price: Number(e.target.value) })}
              />
              <TextField 
                label="Duration (min)" 
                type="number" 
                fullWidth 
                size="small" 
                value={editingService.duration || 30} 
                onChange={(e) => setEditingService({ ...editingService, duration: Number(e.target.value) })}
              />
            </Stack>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleSave} disabled={!editingService.name}>Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
