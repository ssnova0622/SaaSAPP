// Simple E.164 phone validation and normalization helpers

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
