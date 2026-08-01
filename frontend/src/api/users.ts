import { api } from './client'
import type { Role, User } from '../types'

export const usersApi = {
  async updateProfile(input: Partial<Pick<User, 'full_name' | 'timezone'>>) { return (await api.patch<User>('/auth/me', input)).data },
  async list(search = '') { return (await api.get<User[]>('/admin/users', { params: search ? { search } : undefined })).data },
  async setRoles(id: string, roles: Role[]) { return (await api.put<User>(`/admin/users/${id}/roles`, { roles })).data },
  async setActive(id: string, is_active: boolean) { return (await api.patch<User>(`/admin/users/${id}/active`, { is_active })).data },
}
