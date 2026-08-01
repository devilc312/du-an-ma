import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { notificationsApi } from '../api/ai'
import type { Notification, NotificationList } from '../types'

export function useNotificationSocket() {
  const queryClient = useQueryClient()
  useEffect(() => {
    if (typeof WebSocket === 'undefined') return
    const endpoint = import.meta.env.VITE_WS_URL ?? `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/v1/ws/notifications`
    let socket: WebSocket | null = null
    let retry: number | undefined
    let stopped = false

    const connect = async () => {
      try {
        const { ticket } = await notificationsApi.ticket()
        if (stopped) return
        socket = new WebSocket(`${endpoint}?ticket=${encodeURIComponent(ticket)}`)
        socket.onmessage = (event) => {
          try {
            const payload = JSON.parse(event.data) as { type: string; data?: Notification }
            if (payload.type !== 'notification' || !payload.data) return
            queryClient.setQueryData<NotificationList>(['notifications'], (old) => {
              if (!old) return old
              if (old.items.some(item => item.id === payload.data!.id)) return old
              return { items: [payload.data!, ...old.items], unread_count: old.unread_count + 1 }
            })
          } catch { /* keep the socket alive after malformed payloads */ }
        }
        socket.onclose = () => { if (!stopped) retry = window.setTimeout(() => void connect(), 3000) }
      } catch {
        if (!stopped) retry = window.setTimeout(() => void connect(), 5000)
      }
    }

    void connect()
    return () => { stopped = true; if (retry) window.clearTimeout(retry); socket?.close() }
  }, [queryClient])
}
