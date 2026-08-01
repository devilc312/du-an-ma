import { beforeEach, describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import type { ReactNode } from 'react'
import { useNotificationSocket } from '../hooks/useNotificationSocket'
import { notificationsApi } from '../api/ai'

vi.mock('../api/ai', () => ({
  notificationsApi: { ticket: vi.fn() },
}))

class MockSocket {
  static instances: MockSocket[] = []
  onmessage: ((event: MessageEvent) => void) | null = null
  onclose: (() => void) | null = null
  constructor(public url: string) { MockSocket.instances.push(this) }
  close() {}
}

describe('useNotificationSocket', () => {
  beforeEach(() => {
    MockSocket.instances = []
    vi.mocked(notificationsApi.ticket).mockResolvedValue({ ticket: 'one-time', expires_in: 30 })
    vi.stubGlobal('WebSocket', MockSocket)
  })

  it('requests a one-time ticket and deduplicates notifications', async () => {
    const client = new QueryClient()
    client.setQueryData(['notifications'], { items: [], unread_count: 0 })
    const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>

    renderHook(() => useNotificationSocket(), { wrapper })
    await act(async () => { await Promise.resolve(); await Promise.resolve() })

    expect(notificationsApi.ticket).toHaveBeenCalledOnce()
    expect(MockSocket.instances[0].url).toContain('ticket=one-time')
    const payload = { type: 'notification', data: { id: 'n1', todo_id: null, kind: 'info', title: 'T', message: 'M', is_read: false, read_at: null, created_at: new Date().toISOString() } }
    act(() => {
      MockSocket.instances[0].onmessage?.({ data: JSON.stringify(payload) } as MessageEvent)
      MockSocket.instances[0].onmessage?.({ data: JSON.stringify(payload) } as MessageEvent)
    })
    expect(client.getQueryData<{ items: unknown[]; unread_count: number }>(['notifications'])).toMatchObject({ unread_count: 1 })
  })
})
