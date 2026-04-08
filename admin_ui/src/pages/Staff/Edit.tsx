import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Box, Button, Card, CardContent, Chip, Stack, TextField, Typography, FormControlLabel, Checkbox } from '@mui/material'
import SaveIcon from '@mui/icons-material/Save'
import LockIcon from '@mui/icons-material/Lock'
import { getStaff, Staff, updateStaff } from '@api/staff'
import { listUsers, setPassword } from '@api/users'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'
import { displayE164FromEntity } from '../../utils/phone'

export default function StaffEdit() {
  const { effectiveTenant, role: userRole } = useEffectiveTenant()
  const tenant = effectiveTenant
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const canManagePortal = userRole === 'tenant_admin' || userRole === 'super_admin'

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['staff', 'detail', tenant, id],
    queryFn: async () => {
      if (!tenant || !id) throw new Error('Missing context')
      return await getStaff(tenant, id)
    },
    enabled: !!tenant && !!id,
  })

  const { data: portalUsersData } = useQuery({
    queryKey: ['users', tenant, 'staff'],
    queryFn: async () => {
      if (!tenant) return { items: [] }
      return await listUsers({ tenant, role: 'staff', page: 1, size: 200 })
    },
    enabled: !!tenant && !!data?.email?.trim() && canManagePortal,
  })

  const portalUser = useMemo(() => {
    const email = (data?.email || '').trim().toLowerCase()
    if (!email) return null
    return (portalUsersData?.items ?? []).find(u => (u.email || '').trim().toLowerCase() === email) ?? null
  }, [data?.email, portalUsersData?.items])

  const [name, setName] = useState('')
  const [role, setRole] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [skillsInput, setSkillsInput] = useState('')
  const [skills, setSkills] = useState<string[]>([])
  const [active, setActive] = useState(true)
  const [portalPassword, setPortalPassword] = useState('')
  const [portalPasswordConfirm, setPortalPasswordConfirm] = useState('')
  const [portalPasswordError, setPortalPasswordError] = useState<string | null>(null)
  const [portalPasswordSaving, setPortalPasswordSaving] = useState(false)

  useEffect(() => {
    if (data) {
      setName(data.name || '')
      setRole(data.role || '')
      setPhone(displayE164FromEntity(data) || data.phone || '')
      setEmail(data.email || '')
      setSkills(data.skills || [])
      setActive(!!data.active)
    }
  }, [data])

  const addSkill = () => {
    const parts = skillsInput.split(',').map(s=>s.trim()).filter(Boolean)
    const next = Array.from(new Set([...(skills||[]), ...parts]))
    setSkills(next)
    setSkillsInput('')
  }
  const removeSkill = (s: string) => setSkills((skills||[]).filter(x=>x!==s))

  const mutation = useMutation({
    mutationFn: async (payload: Partial<Staff>) => {
      if (!tenant || !id) throw new Error('Missing context')
      const p = { ...payload, phone: payload.phone ?? undefined, email: payload.email ?? undefined }
      return await updateStaff(tenant, id, p as import('@api/staff').StaffUpdate)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['staff'] })
      navigate('/staff')
    },
  })

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !role.trim()) return
    try {
      await mutation.mutateAsync({ name: name.trim(), role: role.trim(), phone: phone || undefined, email: email || undefined, skills, active })
    } catch (err) {
      // error surfaced below
    }
  }

  const onSetPortalPassword = async () => {
    if (!portalUser?.id) return
    setPortalPasswordError(null)
    if (portalPassword.length < 8) {
      setPortalPasswordError('Password must be at least 8 characters')
      return
    }
    if (portalPassword !== portalPasswordConfirm) {
      setPortalPasswordError('Passwords do not match')
      return
    }
    setPortalPasswordSaving(true)
    try {
      await setPassword(portalUser.id, portalPassword)
      setPortalPassword('')
      setPortalPasswordConfirm('')
      setPortalPasswordError(null)
    } catch (e: any) {
      setPortalPasswordError(e?.response?.data?.detail ?? 'Failed to update password')
    } finally {
      setPortalPasswordSaving(false)
    }
  }

  if (isLoading) return <Typography>Loading...</Typography>
  if (isError) return <Typography color="error">{(error as any)?.response?.data?.detail || (error as Error).message}</Typography>

  return (
    <Box component="form" onSubmit={onSubmit}>
      <Typography variant="h5" sx={{ mb: 2 }}>Edit Staff</Typography>
      <Card>
        <CardContent>
          <Stack spacing={2}>
            <TextField label="Name" required value={name} onChange={e => setName(e.target.value)} />
            <TextField label="Role" required value={role} onChange={e => setRole(e.target.value)} />
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField label="Phone" value={phone} onChange={e => setPhone(e.target.value)} sx={{ flex: 1 }} />
              <TextField label="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} sx={{ flex: 1 }} />
            </Stack>
            <Stack spacing={1}>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ xs: 'stretch', sm: 'center' }}>
                <TextField label="Add skills (comma to split)" value={skillsInput} onChange={e => setSkillsInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSkill() } }} fullWidth />
                <Button variant="outlined" onClick={addSkill}>Add</Button>
              </Stack>
              <Stack direction="row" spacing={1} flexWrap="wrap">
                {(skills || []).map(s => <Chip key={s} label={s} onDelete={() => removeSkill(s)} />)}
              </Stack>
            </Stack>
            <FormControlLabel control={<Checkbox checked={active} onChange={e => setActive(e.target.checked)} />} label="Active" />
            {mutation.isError && <Typography color="error">{(mutation.error as any)?.response?.data?.detail || (mutation.error as Error).message}</Typography>}
            <Stack direction="row" spacing={2}>
              <Button type="submit" variant="contained" startIcon={<SaveIcon />} disabled={mutation.isPending}>Save</Button>
              <Button variant="text" onClick={() => navigate('/staff')}>Cancel</Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {canManagePortal && portalUser && (
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Stack spacing={2}>
              <Typography variant="subtitle1" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <LockIcon fontSize="small" /> Portal sign-in password
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Set or change the password this staff member uses to log in to the portal. Only tenant admin can change it.
              </Typography>
              <TextField
                label="New password"
                type="password"
                value={portalPassword}
                onChange={e => setPortalPassword(e.target.value)}
                fullWidth
                helperText="Min 8 characters"
              />
              <TextField
                label="Confirm password"
                type="password"
                value={portalPasswordConfirm}
                onChange={e => setPortalPasswordConfirm(e.target.value)}
                fullWidth
              />
              {portalPasswordError && <Typography color="error" variant="body2">{portalPasswordError}</Typography>}
              <Button
                variant="outlined"
                startIcon={<LockIcon />}
                onClick={onSetPortalPassword}
                disabled={portalPasswordSaving || portalPassword.length < 8 || portalPassword !== portalPasswordConfirm}
              >
                {portalPasswordSaving ? 'Updating...' : 'Update password'}
              </Button>
            </Stack>
          </CardContent>
        </Card>
      )}
    </Box>
  )
}
