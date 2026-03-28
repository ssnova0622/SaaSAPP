/**
 * Format an ISO date string (YYYY-MM-DD or ISO datetime with T) for display using the tenant's date_format.
 * Supports: DD-MM-YYYY, DD/MM/YYYY, MM/DD/YYYY, YYYY-MM-DD
 */
export type DateFormatKey = 'DD-MM-YYYY' | 'DD/MM/YYYY' | 'MM/DD/YYYY' | 'YYYY-MM-DD'

export function formatDateForDisplay(
  isoDate: string | null | undefined,
  dateFormat: DateFormatKey | string | null | undefined
): string {
  if (!isoDate) return ''
  const raw = isoDate.trim()
  if (!raw) return ''
  // Accept ISO datetime (e.g. 2025-02-28T10:30:00) — use date part only
  const d = raw.includes('T') ? raw.split('T')[0].trim() : raw
  const parts = d.split('-')
  if (parts.length !== 3) return d
  const [y, m, day] = parts
  const fmt = (dateFormat || 'DD-MM-YYYY').toUpperCase().replace(/\s/g, '')
  if (fmt === 'DD-MM-YYYY') return `${day}-${m}-${y}`
  if (fmt === 'DD/MM/YYYY') return `${day}/${m}/${y}`
  if (fmt === 'MM/DD/YYYY') return `${m}/${day}/${y}`
  if (fmt === 'YYYY-MM-DD') return d
  return d
}
