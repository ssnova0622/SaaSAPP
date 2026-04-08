import { useEffect, useState } from 'react'
import { getTenantSettings } from '../api/tenants'
import { useEffectiveTenant } from './useEffectiveTenant'

export type DateFormatKey = 'DD-MM-YYYY' | 'DD/MM/YYYY' | 'MM/DD/YYYY' | 'YYYY-MM-DD'

const DEFAULT_DATE_FORMAT: DateFormatKey = 'DD-MM-YYYY'
const DEFAULT_TIMEZONE = 'Asia/Kolkata'
const DEFAULT_CURRENCY = 'INR'

/** Maps ISO 4217 currency codes to their display symbols. */
const CURRENCY_SYMBOL_MAP: Record<string, string> = {
  INR: '₹', USD: '$', EUR: '€', GBP: '£',
  AED: 'د.إ', SAR: '﷼', KWD: 'KD', OMR: 'ر.ع.', QAR: 'ر.ق', BHD: '.د.ب', JOD: 'JD',
  MYR: 'RM', SGD: 'S$', AUD: 'A$', CAD: 'C$', NZD: 'NZ$',
  JPY: '¥', CNY: '¥', KRW: '₩', TWD: 'NT$',
  THB: '฿', BDT: '৳', PKR: '₨', LKR: 'Rs', NPR: 'Rs',
  IDR: 'Rp', PHP: '₱', VND: '₫',
  NGN: '₦', ZAR: 'R', EGP: 'E£', TRY: '₺', BRL: 'R$', MXN: '$',
  CHF: 'Fr', SEK: 'kr', NOK: 'kr', DKK: 'kr', PLN: 'zł', CZK: 'Kč', HUF: 'Ft',
}

/**
 * Returns the display symbol for a given ISO 4217 currency code.
 * Falls back to the code itself if no symbol is known.
 */
export function getCurrencySymbol(code: string): string {
  const upper = (code || DEFAULT_CURRENCY).toUpperCase()
  return CURRENCY_SYMBOL_MAP[upper] ?? upper
}

export type TenantDisplayPreferences = {
  dateFormat: DateFormatKey | string
  /** IANA timezone from tenant settings (for formatting UTC instants in local time). */
  timeZone: string
  /** ISO 4217 currency code (e.g. "INR", "USD"). */
  currency: string
  /** Display symbol derived from currency code (e.g. "₹", "$"). */
  currencySymbol: string
}

/**
 * Tenant date_format + tz + currency in one settings fetch.
 * Use for timestamps and amounts shown in the admin UI.
 */
export function useTenantDisplayPreferences(): TenantDisplayPreferences {
  const { effectiveTenant } = useEffectiveTenant()
  const [prefs, setPrefs] = useState<TenantDisplayPreferences>({
    dateFormat: DEFAULT_DATE_FORMAT,
    timeZone: DEFAULT_TIMEZONE,
    currency: DEFAULT_CURRENCY,
    currencySymbol: getCurrencySymbol(DEFAULT_CURRENCY),
  })

  useEffect(() => {
    if (!effectiveTenant) {
      setPrefs({ dateFormat: DEFAULT_DATE_FORMAT, timeZone: DEFAULT_TIMEZONE, currency: DEFAULT_CURRENCY, currencySymbol: getCurrencySymbol(DEFAULT_CURRENCY) })
      return
    }
    getTenantSettings(effectiveTenant)
      .then((s) => {
        const currency = s?.currency || DEFAULT_CURRENCY
        setPrefs({
          dateFormat: (s?.date_format as DateFormatKey) || DEFAULT_DATE_FORMAT,
          timeZone: (s?.tz && String(s.tz).trim()) || DEFAULT_TIMEZONE,
          currency,
          currencySymbol: getCurrencySymbol(currency),
        })
      })
      .catch(() =>
        setPrefs({ dateFormat: DEFAULT_DATE_FORMAT, timeZone: DEFAULT_TIMEZONE, currency: DEFAULT_CURRENCY, currencySymbol: getCurrencySymbol(DEFAULT_CURRENCY) }),
      )
  }, [effectiveTenant])

  return prefs
}

/**
 * Returns the tenant's date_format for display across the app.
 * Use with formatDateForDisplay(isoDate, dateFormat) so calendar dates respect tenant settings.
 * For `created_at` / `updated_at` (UTC ISO strings), prefer formatDateTimeForDisplay with useTenantDisplayPreferences().timeZone.
 */
export function useTenantDateFormat(): DateFormatKey | string {
  return useTenantDisplayPreferences().dateFormat
}

/** Returns just the currency symbol for the current tenant. */
export function useCurrencySymbol(): string {
  return useTenantDisplayPreferences().currencySymbol
}
