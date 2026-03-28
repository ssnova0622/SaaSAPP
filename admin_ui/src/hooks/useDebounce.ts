import { useEffect, useState } from 'react'

/**
 * Returns a debounced value that updates after `ms` delay when the source value changes.
 * Use for inline search: bind input to value, use debouncedValue in API calls.
 */
export function useDebounce<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState<T>(value)

  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])

  return debounced
}
