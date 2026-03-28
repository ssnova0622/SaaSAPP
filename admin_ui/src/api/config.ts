/**
 * Central API base URL config. Use everywhere instead of repeating env checks.
 */
const defaultBase = 'http://127.0.0.1:8000/v1'

function readBase(): string {
  try {
    const e = (import.meta as any).env
    const base = (e?.VITE_API_BASE || e?.VITE_API_BASE_URL || defaultBase) as string
    return (base || defaultBase).replace(/\/$/, '') || defaultBase
  } catch {
    return defaultBase
  }
}

/** Base URL for API requests (includes /v1). Used by axios and for report/download links. */
export function getApiBaseURL(): string {
  return readBase()
}

/** Base URL without /v1 suffix (e.g. for uploads or WS). */
export function getUploadBaseURL(): string {
  return getApiBaseURL().replace(/\/v1$/, '')
}

/** Resolve a path that may be /v1/uploads/... to the correct origin (uploads often served without /v1). */
export function resolveUploadUrl(pathOrUrl: string): string {
  if (pathOrUrl.startsWith('/v1/uploads')) {
    return getUploadBaseURL() + pathOrUrl.replace(/^\/v1/, '')
  }
  if (pathOrUrl.startsWith('http')) return pathOrUrl
  return getApiBaseURL() + (pathOrUrl.startsWith('/') ? pathOrUrl : '/' + pathOrUrl)
}
