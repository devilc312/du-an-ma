import { api } from './client'
import type { Category, DashboardStats, Paginated, Todo, TodoInput, TodoPriority, TodoStatus } from '../types'

export interface TodoQuery {
  page?: number
  page_size?: number
  status?: TodoStatus | ''
  search?: string
  priority?: TodoPriority | ''
  category_id?: string
  due_after?: string
  due_before?: string
  sort?: string
  order?: string
}

function compactParams(params: TodoQuery): Record<string, string | number> {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ''),
  ) as Record<string, string | number>
}

export const todosApi = {
  async list(params: TodoQuery = {}) { return (await api.get<Paginated<Todo>>('/todos', { params: compactParams(params) })).data },
  async stats() { return (await api.get<DashboardStats>('/todos/stats')).data },
  async create(input: TodoInput) { return (await api.post<Todo>('/todos', input)).data },
  async update(id: string, input: Partial<TodoInput>) { return (await api.patch<Todo>(`/todos/${id}`, input)).data },
  async remove(id: string) { await api.delete(`/todos/${id}`) },
}

export const categoriesApi = {
  async list() { return (await api.get<Category[]>('/categories')).data },
  async create(input: Pick<Category, 'name' | 'color'>) { return (await api.post<Category>('/categories', input)).data },
  async update(id: string, input: Partial<Pick<Category, 'name' | 'color'>>) { return (await api.patch<Category>(`/categories/${id}`, input)).data },
  async remove(id: string) { await api.delete(`/categories/${id}`) },
}
