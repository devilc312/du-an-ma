import { api } from './client'
import type { AuthResponse, User } from '../types'

export interface LoginInput { email: string; password: string }
export interface RegisterInput extends LoginInput { full_name: string; timezone?: string }

export const authApi = {
  async login(input: LoginInput) { return (await api.post<AuthResponse>('/auth/login', input)).data },
  async register(input: RegisterInput) { return (await api.post<AuthResponse>('/auth/register', input)).data },
  async me() { return (await api.get<User>('/auth/me')).data },
  async logout() { await api.post('/auth/logout') },
}
