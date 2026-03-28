import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Box, Button, Card, CardContent, Chip, Stack, TextField, Typography, FormControlLabel, Checkbox } from '@mui/material'
import SaveIcon from '@mui/icons-material/Save'
import { createStaff, StaffCreate } from '@api/staff'
import { useEffectiveTenant } from '../../hooks/useEffectiveTenant'

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
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [skillsInput, setSkillsInput] = useState('')
  const [skills, setSkills] = useState<string[]>([])
  const [active, setActive] = useState(true)

  const addSkill = () => {
    const parts = skillsInput.split(',').map(s=>s.trim()).filter(Boolean)
    const next = Array.from(new Set([...skills, ...parts]))
    setSkills(next)
    setSkillsInput('')
  }
  const removeSkill = (s: string) => setSkills(skills.filter(x=>x!==s))

  const mutation = useMutation({
    mutationFn: async (payload: StaffCreate) => {
      if(!tenant) throw new Error('Select a tenant')
      return await createStaff(tenant, payload)
    },
    onSuccess: ()=> navigate('/staff')
  })

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if(!name.trim() || !role.trim()) return
    try {
      await mutation.mutateAsync({ name: name.trim(), role: role.trim(), phone: phone || undefined, email: email || undefined, skills, active })
    } catch (err) {
      // error surfaced below
    }
  }

  return (
    <Box component="form" onSubmit={onSubmit}>
      <Typography variant="h5" sx={{ mb:2 }}>New Staff</Typography>
      <Card>
        <CardContent>
          <Stack spacing={2}>
            <TextField label="Name" required value={name} onChange={e=>setName(e.target.value)} />
            <TextField label="Role" required value={role} onChange={e=>setRole(e.target.value)} />
            <Stack direction={{ xs:'column', sm:'row' }} spacing={2}>
              <TextField label="Phone" value={phone} onChange={e=>setPhone(e.target.value)} sx={{ flex:1 }} />
              <TextField label="Email" type="email" value={email} onChange={e=>setEmail(e.target.value)} sx={{ flex:1 }} />
            </Stack>
            <Stack spacing={1}>
              <Stack direction={{ xs:'column', sm:'row' }} spacing={1} alignItems={{ xs:'stretch', sm:'center' }}>
                <TextField label="Add skills (comma to split)" value={skillsInput} onChange={e=>setSkillsInput(e.target.value)} onKeyDown={(e)=>{ if(e.key==='Enter'){ e.preventDefault(); addSkill() } }} fullWidth />
                <Button variant="outlined" onClick={addSkill}>Add</Button>
              </Stack>
              <Stack direction="row" spacing={1} flexWrap="wrap">
                {skills.map(s=> <Chip key={s} label={s} onDelete={()=>removeSkill(s)} />)}
              </Stack>
            </Stack>
            <FormControlLabel control={<Checkbox checked={active} onChange={e=>setActive(e.target.checked)} />} label="Active" />
            {mutation.isError && <Typography color="error">{(mutation.error as any)?.response?.data?.detail || (mutation.error as Error).message}</Typography>}
            <Stack direction="row" spacing={2}>
              <Button type="submit" variant="contained" startIcon={<SaveIcon />} disabled={mutation.isPending}>Create</Button>
              <Button variant="text" onClick={()=>navigate('/staff')}>Cancel</Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  )
}
