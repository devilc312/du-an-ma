import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { notificationsApi } from '../api/ai'
import { categoriesApi, todosApi, type TodoQuery } from '../api/todos'
import { usersApi } from '../api/users'

export const queryKeys = {
  todos: (params: TodoQuery) => ['todos', params] as const,
  stats: ['todo-stats'] as const,
  categories: ['categories'] as const,
  notifications: ['notifications'] as const,
  adminUsers: ['admin-users'] as const,
}

export function useTodos(params: TodoQuery) {
  return useQuery({
    queryKey: queryKeys.todos(params),
    queryFn: () => todosApi.list(params),
    placeholderData: previous => previous,
  })
}

export function useTodoStats() {
  return useQuery({ queryKey: queryKeys.stats, queryFn: todosApi.stats })
}

export function useCategories() {
  return useQuery({ queryKey: queryKeys.categories, queryFn: categoriesApi.list })
}

export function useTodoMutations() {
  const queryClient = useQueryClient()
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['todos'] })
    void queryClient.invalidateQueries({ queryKey: queryKeys.stats })
  }
  const create = useMutation({ mutationFn: todosApi.create, onSuccess: invalidate })
  const update = useMutation({
    mutationFn: ({ id, input }: { id: string; input: Parameters<typeof todosApi.update>[1] }) => todosApi.update(id, input),
    onSuccess: invalidate,
  })
  const remove = useMutation({ mutationFn: todosApi.remove, onSuccess: invalidate })
  return { create, update, remove }
}

export function useCategoryMutations() {
  const queryClient = useQueryClient()
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.categories })
    void queryClient.invalidateQueries({ queryKey: ['todos'] })
  }
  const create = useMutation({ mutationFn: categoriesApi.create, onSuccess: invalidate })
  const update = useMutation({
    mutationFn: ({ id, input }: { id: string; input: Parameters<typeof categoriesApi.update>[1] }) => categoriesApi.update(id, input),
    onSuccess: invalidate,
  })
  const remove = useMutation({ mutationFn: categoriesApi.remove, onSuccess: invalidate })
  return { create, update, remove }
}

export function useNotifications() {
  return useQuery({
    queryKey: queryKeys.notifications,
    queryFn: () => notificationsApi.list({ limit: 50 }),
    refetchInterval: 30_000,
  })
}

export function useAdminUsers(enabled: boolean, search = '') {
  return useQuery({
    queryKey: [...queryKeys.adminUsers, search],
    queryFn: () => usersApi.list(search),
    enabled,
  })
}
