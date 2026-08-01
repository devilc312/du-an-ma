import { createContext } from 'react'
import type { LoginInput, RegisterInput } from '../api/auth'
import type { User } from '../types'

export type AuthContextValue = {
  user: User | null
  loading: boolean
  login: (input: LoginInput) => Promise<void>
  register: (input: RegisterInput) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
