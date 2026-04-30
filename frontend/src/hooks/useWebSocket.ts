import { useCallback, useEffect, useRef } from 'react'

type MessageHandler = (channel: string, data: unknown) => void

export function useWebSocket(onMessage: MessageHandler) {
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws`)
    wsRef.current = ws

    ws.onmessage = event => {
      try {
        const { channel, data } = JSON.parse(event.data)
        onMessageRef.current(channel, data)
      } catch {}
    }

    ws.onclose = () => { wsRef.current = null }

    return () => { ws.close() }
  }, [])

  const send = useCallback((msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg))
    }
  }, [])

  return { send }
}
