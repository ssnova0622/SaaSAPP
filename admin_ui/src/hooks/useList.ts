import { useState, useCallback, useEffect } from 'react'

export interface UseListOptions<T> {
  fetch: () => Promise<T[]>
  enabled?: boolean
  /** When these change, refresh is called (e.g. [tenant] so list refetches when tenant changes). */
  deps?: unknown[]
  onError?: (err: unknown) => void
}

export interface UseListResult<T> {
  items: T[]
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

/**
 * Generic list loading hook. Use for any page that loads a list from an API.
 * Keeps loading/error/items and provides refresh. Reduces duplicated logic.
 */
export function useList<T>(options: UseListOptions<T>): UseListResult<T> {
  const { fetch: fetchFn, enabled = true, deps = [], onError } = options
  const [items, setItems] = useState<T[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchFn()
      setItems(Array.isArray(data) ? data : [])
    } catch (err) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        'Failed to load'
      setError(typeof msg === 'string' ? msg : 'Failed to load')
      onError?.(err)
    } finally {
      setLoading(false)
    }
  }, [fetchFn, onError])

  useEffect(() => {
    if (enabled) {
      refresh()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, ...deps])

  return { items, loading, error, refresh }
}
