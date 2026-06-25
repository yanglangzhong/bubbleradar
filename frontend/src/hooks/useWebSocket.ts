import { useEffect, useRef, useState, useCallback } from 'react'
import type { DashboardData } from '@/types'

export type WebSocketMessage =
  | { type: 'snapshot'; data: DashboardData }
  | { type: 'update'; data: DashboardData }
  | { type: 'pong' }

interface UseDashboardWebSocketOptions {
  onSnapshot?: (data: DashboardData) => void
  onUpdate?: (data: DashboardData) => void
  reconnect?: boolean
}

function getWebSocketUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return `${protocol}//${host}/ws/dashboard`
}

export function useDashboardWebSocket(options: UseDashboardWebSocketOptions = {}) {
  const { onSnapshot, onUpdate, reconnect = true } = options
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptsRef = useRef(0)

  const cleanup = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    if (wsRef.current) {
      wsRef.current.onopen = null
      wsRef.current.onmessage = null
      wsRef.current.onclose = null
      wsRef.current.onerror = null
      if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
        wsRef.current.close()
      }
      wsRef.current = null
    }
  }, [])

  const connect = useCallback(() => {
    cleanup()
    setError(null)

    try {
      const url = getWebSocketUrl()
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        setError(null)
        reconnectAttemptsRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage
          if (message.type === 'snapshot') {
            onSnapshot?.(message.data)
          } else if (message.type === 'update') {
            onUpdate?.(message.data)
          }
        } catch {
          // ignore malformed messages
        }
      }

      ws.onclose = () => {
        setConnected(false)
        if (reconnect) {
          reconnectAttemptsRef.current += 1
          const delay = Math.min(1000 * 2 ** reconnectAttemptsRef.current, 30000)
          reconnectTimerRef.current = setTimeout(connect, delay)
        }
      }

      ws.onerror = () => {
        setError('实时连接异常，正在尝试重连…')
        setConnected(false)
      }
    } catch (err) {
      setError('无法建立实时连接')
    }
  }, [cleanup, reconnect, onSnapshot, onUpdate])

  const sendPing = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send('ping')
    }
  }, [])

  useEffect(() => {
    connect()
    const heartbeat = setInterval(sendPing, 30000)
    return () => {
      clearInterval(heartbeat)
      cleanup()
    }
  }, [connect, cleanup, sendPing])

  return { connected, error }
}
