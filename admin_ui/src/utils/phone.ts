// Simple E.164 phone validation and normalization helpers

/** Canonical API shape: `{ code: "+91", number: "..." }` (legacy key `mobile_number` still accepted). */
export type PhoneNumberJson = {
  code?: string
  number?: string
  mobile_number?: string
}

/** Build E.164 from structured `phone_number` (or empty string). */
export function e164FromPhoneNumber(pn: PhoneNumberJson | null | undefined): string {
  if (!pn || typeof pn !== 'object') return ''
  const code = String(pn.code || '').trim()
  const rawNum = pn.number ?? pn.mobile_number
  const num = String(rawNum ?? '').replace(/\D/g, '')
  const cc = code.replace(/\D/g, '')
  if (!cc || !num) return ''
  return `+${cc}${num}`
}

export type HasPhoneFields = {
  phone?: string | null
  phone_number?: PhoneNumberJson | null
}

/** Prefer flat `phone` when present; otherwise derive from `phone_number`. */
export function displayE164FromEntity(entity: HasPhoneFields | null | undefined): string {
  if (!entity) return ''
  const flat = entity.phone != null && String(entity.phone).trim() ? String(entity.phone).trim() : ''
  if (flat) return flat
  return e164FromPhoneNumber(entity.phone_number)
}

/** Format structured or flat phone for table labels (E.164 cleanup). */
export function formatEntityPhoneForDisplay(entity: HasPhoneFields | null | undefined): string {
  return formatPhoneForDisplay(displayE164FromEntity(entity))
}

/**
 * Validate a phone number in E.164 format (leading + optional) with 7-15 digits.
 * Accepts values with optional "whatsapp:" prefix and normalizes before testing.
 */
export function isValidE164(input: string | null | undefined): boolean {
  if (!input) return false
  let v = String(input).trim()
  if (!v) return false
  if (v.toLowerCase().startsWith('whatsapp:')) v = v.slice('whatsapp:'.length)
  return /^\+?[1-9]\d{6,14}$/.test(v)
}

/** Remove an optional whatsapp: prefix and trim spaces. */
export function normalizePhone(input: string | null | undefined): string {
  if (!input) return ''
  let v = String(input).trim()
  if (v.toLowerCase().startsWith('whatsapp:')) v = v.slice('whatsapp:'.length)
  return v
}

/** Parse a comma or newline separated list into normalized phones, preserving order. */
export function parsePhoneList(raw: string): string[] {
  return (raw || '')
    .split(/\n|,/)
    .map(s => normalizePhone(s))
    .filter(Boolean)
}

/** Return invalid phones from a list. */
export function findInvalidPhones(list: string[]): string[] {
  return list.filter(p => !isValidE164(p))
}

/**
 * Format phone for display: strip erroneous "IN" (ISO code) used as country prefix
 * and ensure E.164-like display. Use across Customer, Appointments, etc.
 */
export function formatPhoneForDisplay(phone: string | null | undefined): string {
  if (!phone) return ''
  let v = String(phone).trim()
  if (/^\+?IN\s*/i.test(v)) v = v.replace(/^\+?IN\s*/i, '+91')
  if (/^IN\s*(\d)/i.test(v)) v = '+91' + v.replace(/^IN\s*/i, '')
  return v
}

/** True if value is plausible E.164 or national digits (server applies tenant country when no +). */
export function isValidPhoneInput(input: string | null | undefined): boolean {
  if (!input || !String(input).trim()) return false
  let v = String(input).trim()
  if (v.toLowerCase().startsWith('whatsapp:')) v = v.slice('whatsapp:'.length)
  const digits = v.replace(/\D/g, '')
  if (digits.length < 7 || digits.length > 15) return false
  if (v.startsWith('+')) return /^\+[1-9]\d{6,14}$/.test(v.replace(/\s/g, ''))
  return /^[0-9]{7,15}$/.test(digits)
}

/** Build E.164-style string for API when user entered national digits only. */
export function combineDialAndMobile(dialCode: string, nationalDigits: string): string {
  const d = String(dialCode || '').trim()
  const n = String(nationalDigits || '').replace(/\D/g, '')
  const cc = d.startsWith('+') ? d.replace(/\D/g, '') : d.replace(/\D/g, '')
  if (!n) return ''
  return `+${cc}${n}`
}
