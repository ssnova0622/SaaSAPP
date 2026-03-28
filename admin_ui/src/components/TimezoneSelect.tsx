import { Autocomplete, TextField } from '@mui/material'
import { useMemo } from 'react'

type Props = {
  value: string | null | undefined
  onChange: (tz: string) => void
  label?: string
  placeholder?: string
  fullWidth?: boolean
}

const FALLBACK_TZS = [
  'UTC',
  'Europe/London',
  'Europe/Berlin',
  'Europe/Paris',
  'Europe/Madrid',
  'Europe/Rome',
  'Europe/Moscow',
  'Africa/Johannesburg',
  'Asia/Kolkata',
  'Asia/Dubai',
  'Asia/Singapore',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Australia/Sydney',
  'Pacific/Auckland',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Sao_Paulo',
];

function getTimeZones(): string[] {
  try {
    // @ts-ignore: supportedValuesOf may not exist on older TS lib versions
    const list = typeof Intl !== 'undefined' && (Intl as any).supportedValuesOf ? (Intl as any).supportedValuesOf('timeZone') : null
    if (Array.isArray(list) && list.length > 0) return list
  } catch {
    // ignore
  }
  return FALLBACK_TZS
}

export default function TimezoneSelect({ value, onChange, label = 'Timezone (IANA)', placeholder = 'Asia/Kolkata', fullWidth = true }: Props) {
  const options = useMemo(() => getTimeZones(), [])
  const val = value || ''

  return (
    <Autocomplete
      options={options}
      value={val as any}
      onChange={(_, newVal) => {
        const tz = (newVal as string) || ''
        if (tz) onChange(tz)
      }}
      renderInput={(params) => (
        <TextField {...params} label={label} placeholder={placeholder} fullWidth={fullWidth} />
      )}
      fullWidth={fullWidth}
      autoHighlight
      disableClearable
      getOptionLabel={(o) => String(o)}
    />
  )
}
