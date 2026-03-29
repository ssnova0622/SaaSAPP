/** Turn FastAPI / Axios error payloads into a single user-visible string. */
export function formatApiDetail(err: unknown): string {
  const e = err as { response?: { data?: { detail?: unknown } }; message?: string }
  const d = e?.response?.data?.detail
  if (d == null) return e?.message || 'Request failed'
  if (typeof d === 'string') return d
  if (Array.isArray(d)) {
    return d
      .map((x: unknown) => (typeof x === 'object' && x && 'msg' in x ? String((x as { msg: string }).msg) : String(x)))
      .filter(Boolean)
      .join('; ')
  }
  if (typeof d === 'object' && d !== null) {
    try {
      return JSON.stringify(d)
    } catch {
      return String(d)
    }
  }
  return String(d)
}
