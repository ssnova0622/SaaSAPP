import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import {
  Box, Button, Card, CardContent, Chip, MenuItem, Stack,
  TextField, Typography, FormControlLabel, Checkbox,
} from '@mui/material'
import SaveIcon from '@mui/icons-material/Save'
import { createStaff, StaffCreate } from '@api/staff'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'

const ROLE_OPTIONS = [
  { value: '',         label: '— Not set (assign after portal access) —' },
  { value: 'manager',  label: 'Manager' },
  { value: 'editor',   label: 'Editor' },
  { value: 'viewer',   label: 'Viewer' },
  { value: 'custom',   label: 'Custom Staff' },
]

export default function StaffNew() {
  const { effectiveTenant, role: userRole } = useEffectiveTenant()
  const tenant = effectiveTenant
  const navigate = useNavigate()
  const canCreate = userRole === 'tenant_admin' || userRole === 'super_admin'

  useEffect(() => {
    if (userRole && !canCreate) navigate('/staff', { replace: true })
  }, [userRole, canCreate, navigate])

  const [name, setName] = useState('')
  const [role, setRole] = useState('')
  const [position, setPosition] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [skillsInput, setSkillsInput] = useState('')
  const [skills, setSkills] = useState<string[]>([])
  const [active, setActive] = useState(true)

  const addSkill = () => {
    const parts = skillsInput.split(',').map((s) => s.trim()).filter(Boolean)
    setSkills(Array.from(new Set([...skills, ...parts])))
    setSkillsInput('')
  }
  const removeSkill = (s: string) => setSkills(skills.filter((x) => x !== s))

  const mutation = useMutation({
    mutationFn: async (payload: StaffCreate) => {
      if (!tenant) throw new Error('Select a tenant')
      return await createStaff(tenant, payload)
    },
    onSuccess: () => navigate('/staff'),
  })

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    try {
      await mutation.mutateAsync({
        name: name.trim(),
        role: role || undefined,
        position: position.trim() || undefined,
        phone: phone || undefined,
        email: email || undefined,
        skills,
        active,
      })
    } catch {
      // error surfaced below
    }
  }

  return (
    <Box component="form" onSubmit={onSubmit}>
      <Typography variant="h5" sx={{ mb: 2 }}>New Staff</Typography>
      <Card>
        <CardContent>
          <Stack spacing={2}>
            <TextField
              label="Name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              helperText="Staff member's full name"
            />

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField
                select
                label="Portal Role"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                sx={{ flex: 1 }}
                helperText="Leave blank — will be set automatically when portal access is granted"
              >
                {ROLE_OPTIONS.map((o) => (
                  <MenuItem key={o.value} value={o.value}>{o.label}</MenuItem>
                ))}
              </TextField>
              <TextField
                label="Position / Job Title"
                placeholder="e.g. Receptionist, Assistant, Therapist"
                value={position}
                onChange={(e) => setPosition(e.target.value)}
                sx={{ flex: 1 }}
                helperText="Their job title at the business (optional)"
              />
            </Stack>

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <TextField label="Phone" value={phone} onChange={(e) => setPhone(e.target.value)} sx={{ flex: 1 }} />
              <TextField label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} sx={{ flex: 1 }} helperText="Used as login email for portal access" />
            </Stack>

            <Stack spacing={1}>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ xs: 'stretch', sm: 'center' }}>
                <TextField
                  label="Add skills (comma-separated)"
                  value={skillsInput}
                  onChange={(e) => setSkillsInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSkill() } }}
                  fullWidth
                />
                <Button variant="outlined" onClick={addSkill}>Add</Button>
              </Stack>
              <Stack direction="row" spacing={1} flexWrap="wrap">
                {skills.map((s) => <Chip key={s} label={s} onDelete={() => removeSkill(s)} />)}
              </Stack>
            </Stack>

            <FormControlLabel control={<Checkbox checked={active} onChange={(e) => setActive(e.target.checked)} />} label="Active" />

            {mutation.isError && (
              <Typography color="error">
                {(mutation.error as any)?.response?.data?.detail || (mutation.error as Error).message}
              </Typography>
            )}

            <Stack direction="row" spacing={2}>
              <Button type="submit" variant="contained" startIcon={<SaveIcon />} disabled={mutation.isPending || !name.trim()}>
                Create Staff
              </Button>
              <Button variant="text" onClick={() => navigate('/staff')}>Cancel</Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  )
}
