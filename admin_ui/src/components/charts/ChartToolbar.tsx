import { useEffect, useState } from 'react'
import { TextField, MenuItem } from '@mui/material'

export type ChartOption = { value: string; label: string }

export default function ChartToolbar({
  label = 'Chart',
  options,
  value: controlledValue,
  onChange,
  persistKey,
}: {
  label?: string
  options: ChartOption[]
  value: string
  onChange: (v: string) => void
  persistKey?: string
}){
  const [val, setVal] = useState<string>(controlledValue)
  useEffect(()=>{ setVal(controlledValue) }, [controlledValue])
  useEffect(()=>{
    if(!persistKey) return
    try{ localStorage.setItem(persistKey, val) } catch {}
  }, [val, persistKey])
  return (
    <TextField select size='small' label={label} value={val}
      onChange={e=>{ setVal(e.target.value); onChange(e.target.value) }} sx={{ minWidth: 160 }}>
      {options.map(opt => (
        <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
      ))}
    </TextField>
  )
}
