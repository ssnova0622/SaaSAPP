import { useEffect, useMemo, useState } from 'react'
import { Alert, Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, IconButton, MenuItem, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from '@mui/material'
import DeleteIcon from '@mui/icons-material/Delete'
import { listCategories, upsertCategory, patchCategory, deleteCategory, Category } from '@api/catalog'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'

export default function CategoriesPage(){
  const { effectiveTenant: tenant, isSuper } = useEffectiveTenant()
  const [items, setItems] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string|null>(null)
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [active, setActive] = useState(true)

  async function load(){
    if(!tenant) return
    const rid = ++(load as any).__rid || (((load as any).__rid = 1))
    setLoading(true); setError(null)
    try{ 
      const list = await listCategories(tenant);
      if (rid !== (load as any).__rid) return
      setItems(list) 
    } catch(e:any){ if (rid === (load as any).__rid) setError(e?.response?.data?.detail || 'Failed to load categories') } finally{ if (rid === (load as any).__rid) setLoading(false) }
  }
  useEffect(()=>{ load() // eslint-disable-next-line
  },[tenant])

  function startCreate(){ setName(''); setActive(true); setOpen(true) }

  async function save(){
    if(!tenant) return
    if(!name.trim()) { setError('Name is required'); return }
    setLoading(true); setError(null)
    try{ await upsertCategory(tenant, { name: name.trim(), active }); setOpen(false); await load() } catch(e:any){ setError(e?.response?.data?.detail || 'Save failed') } finally{ setLoading(false) }
  }

  async function toggleActive(row: Category){
    if(!tenant) return
    setLoading(true); setError(null)
    try{ await patchCategory(tenant, row.name, !row.active); await load() } catch(e:any){ setError(e?.response?.data?.detail || 'Update failed') } finally{ setLoading(false) }
  }

  async function remove(row: Category){
    if(!tenant) return
    const typed = prompt(`Type the category name to confirm deletion: ${row.name}`)
    if(typed !== row.name) return
    setLoading(true); setError(null)
    try{ await deleteCategory(tenant, row.name); await load() } catch(e:any){ setError(e?.response?.data?.detail || 'Delete failed') } finally{ setLoading(false) }
  }

  return (
    <Box sx={{ p:1 }}>
      <Stack direction={{ xs:'column', md:'row' }} spacing={2} alignItems="center" justifyContent="space-between" sx={{ mb:2 }}>
        <Typography variant="h5">Store — Categories</Typography>
        <Stack direction="row" spacing={1}>
          <Button variant="contained" onClick={startCreate} disabled={!tenant}>New Category</Button>
        </Stack>
      </Stack>

      {error && <Alert severity='error' sx={{ mb:2 }}>{error}</Alert>}

      <Card>
        <CardContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Staff (C/U)</TableCell>
                <TableCell align='right'>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map(c => (
                <TableRow key={c.name}>
                  <TableCell>{c.name}</TableCell>
                  <TableCell>
                    <Chip size='small' label={c.active ? 'Active' : 'Inactive'} color={c.active ? 'success' : 'default'} onClick={()=>toggleActive(c)} />
                  </TableCell>
                  <TableCell>
                    <Typography variant="caption" display="block" color="text.secondary">
                      C: {c.created_by ?? '-'}
                    </Typography>
                    <Typography variant="caption" display="block" color="text.secondary">
                      U: {c.updated_by ?? '-'}
                    </Typography>
                  </TableCell>
                  <TableCell align='right'>
                    <IconButton size='small' onClick={()=>remove(c)}><DeleteIcon fontSize='small' /></IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {!items.length && (
                <TableRow><TableCell colSpan={4}><Typography variant='body2' color='text.secondary'>{loading? 'Loading...' : 'No categories'}</Typography></TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={open} onClose={()=>setOpen(false)} maxWidth='xs' fullWidth>
        <DialogTitle>New Category</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2} sx={{ mt:1 }}>
            <TextField label='Name' value={name} onChange={e=>setName(e.target.value)} fullWidth />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setOpen(false)}>Cancel</Button>
          <Button variant='contained' onClick={save}>Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}
