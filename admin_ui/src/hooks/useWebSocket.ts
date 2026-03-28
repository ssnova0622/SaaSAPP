import { useEffect, useRef, useState } from 'react'
import { getUploadBaseURL } from '@api/config'

export type WsEvent = {
  type: string
  [k: string]: any
}

export function useWebSocket(tenant: string | null) {
  const [lastEvent, setLastEvent] = useState<WsEvent | null>(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!tenant) return

    const url = new URL(getUploadBaseURL())
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    url.pathname = `/ws/${tenant}`

    let retry = 0
    let stopped = false

    function connect() {
      if (stopped) return
      const ws = new WebSocket(url.toString())
      wsRef.current = ws

      ws.onopen = () => { setConnected(true); retry = 0 }
      ws.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data)
          setLastEvent(data)
        } catch { /* ignore */ }
      }
      ws.onclose = () => {
        setConnected(false)
        wsRef.current = null
        if (!stopped) {
          retry = Math.min(10000, (retry || 1000) * 2)
          setTimeout(connect, retry)
        }
      }
      ws.onerror = () => {
        ws.close()
      }
    }

    connect()
    return () => { stopped = true; wsRef.current?.close() }
  }, [tenant])

  return { connected, lastEvent }
}
