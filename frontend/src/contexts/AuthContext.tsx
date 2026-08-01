import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { authApi } from '../api/auth'
import { AuthContext, type AuthContextValue } from './auth-context'
import type { User } from '../types'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    authApi.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false))
  }, [])

  const value = useMemo<AuthContextValue>(() => ({
    user,
    loading,
    login: async (input) => { const result = await authApi.login(input); setUser(result.user) },
    register: async (input) => { const result = await authApi.register(input); setUser(result.user) },
    logout: async () => { try { await authApi.logout() } finally { setUser(null) } },
    refreshUser: async () => setUser(await authApi.me()),
  }), [user, loading])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
