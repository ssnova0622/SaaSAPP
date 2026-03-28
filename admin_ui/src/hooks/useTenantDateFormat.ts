import { useEffect, useState } from 'react'
import { getTenantSettings } from '../api/tenants'
import { useEffectiveTenant } from './useEffectiveTenant'

export type DateFormatKey = 'DD-MM-YYYY' | 'DD/MM/YYYY' | 'MM/DD/YYYY' | 'YYYY-MM-DD'

const DEFAULT_DATE_FORMAT: DateFormatKey = 'DD-MM-YYYY'

/**
 * Returns the tenant's date_format for display across the app.
 * Use with formatDateForDisplay(isoDate, dateFormat) so all dates respect tenant settings.
 */
export function useTenantDateFormat(): DateFormatKey | string {
  const { effectiveTenant } = useEffectiveTenant()
  const [dateFormat, setDateFormat] = useState<DateFormatKey | string>(DEFAULT_DATE_FORMAT)

  useEffect(() => {
    if (!effectiveTenant) {
      setDateFormat(DEFAULT_DATE_FORMAT)
      return
    }
    getTenantSettings(effectiveTenant)
      .then((s) => setDateFormat((s?.date_format as DateFormatKey) || DEFAULT_DATE_FORMAT))
      .catch(() => setDateFormat(DEFAULT_DATE_FORMAT))
  }, [effectiveTenant])

  return dateFormat
}
