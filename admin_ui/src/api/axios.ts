import axios from 'axios'
import { getApiBaseURL } from './config'

export const api = axios.create({ baseURL: getApiBaseURL() })

// Simple token store (can be improved to HTTP-only cookie later)
export const tokenStore = {
  get(): string | null {
    return localStorage.getItem('auth_token')
  },
  set(token: string) {
    localStorage.setItem('auth_token', token)
  },
  clear() {
    localStorage.removeItem('auth_token')
  }
}

api.interceptors.request.use((config) => {
  const token = tokenStore.get()
  if (token) {
    config.headers = config.headers || {}
    config.headers['Authorization'] = `Bearer ${token}`
  }
  // Attach client version/hash for traceability
  try {
    const ver = import.meta.env?.VITE_APP_VERSION || import.meta.env?.VITE_COMMIT || 'dev'
    config.headers = config.headers || {}
    config.headers['X-Client-Version'] = String(ver)
    config.headers['X-Requested-With'] = 'XMLHttpRequest'
  } catch { /* ignore */ }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401) {
      tokenStore.clear()
      try {
        if (window.location.pathname !== '/login') {
          window.location.assign('/login')
        }
      } catch {
        // ignore
      }
    }
    // One-shot retry for GET when offline → on reconnect
    try {
      const cfg: any = err?.config || {}
      const isGet = String(cfg?.method || 'get').toLowerCase() === 'get'
      const alreadyRetried = !!cfg.__retried
      const offline = typeof navigator !== 'undefined' && navigator && (navigator as any).onLine === false
      if (offline && isGet && !alreadyRetried) {
        return new Promise((resolve) => {
          const handler = () => {
            try { window.removeEventListener('online', handler as any) } catch { /* ignore */ }
            const retryCfg = { ...cfg, __retried: true }
            resolve(api.request(retryCfg))
          }
          try { window.addEventListener('online', handler as any, { once: true }) } catch { resolve(Promise.reject(err)) }
        })
      }
    } catch { /* ignore */ }

    // Broadcast a lightweight error event for unified banners if desired
    try {
      const detail = {
        status: err?.response?.status,
        message: err?.response?.data?.detail || err?.message || 'Request failed'
      }
      window.dispatchEvent(new CustomEvent('api-error', { detail }))
    } catch { /* ignore */ }
    return Promise.reject(err)
  }
)
