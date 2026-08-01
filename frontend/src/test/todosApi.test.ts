import { describe, expect, it, vi } from 'vitest'
import { todosApi } from '../api/todos'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: { get: vi.fn() },
}))

describe('todosApi.list', () => {
  it('omits empty enum and search filters', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0, page: 1, page_size: 8, pages: 0 } })

    await todosApi.list({ page: 1, status: '', priority: '', search: '' })

    expect(api.get).toHaveBeenCalledWith('/todos', { params: { page: 1 } })
  })
})
