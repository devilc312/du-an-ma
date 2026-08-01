import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

const API_URL = import.meta.env.VITE_API_URL ?? '/api/v1'
const CSRF_COOKIE = 'todo_csrf_token'

export const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

let refreshPromise: Promise<boolean> | null = null

function readCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const prefix = `${encodeURIComponent(name)}=`
  const value = document.cookie.split('; ').find(item => item.startsWith(prefix))
  return value ? decodeURIComponent(value.slice(prefix.length)) : null
}

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const method = config.method?.toUpperCase()
  if (method && !['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const csrf = readCookie(CSRF_COOKIE)
    if (csrf) config.headers['X-CSRF-Token'] = csrf
  }
  return config
})

async function refreshSession(): Promise<boolean> {
  if (!refreshPromise) {
    const csrf = readCookie(CSRF_COOKIE)
    refreshPromise = axios.post(
      `${API_URL}/auth/refresh`,
      undefined,
      { withCredentials: true, headers: csrf ? { 'X-CSRF-Token': csrf } : undefined },
    ).then(() => true).catch(() => false).finally(() => { refreshPromise = null })
  }
  return refreshPromise
}

api.interceptors.response.use((response) => response, async (error: AxiosError) => {
  const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined
  if (error.response?.status === 401 && original && !original._retry && !original.url?.includes('/auth/')) {
    original._retry = true
    if (await refreshSession()) return api(original)
  }
  return Promise.reject(error)
})

export function getErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError<{ detail?: string }>(error)) return error.response?.data?.detail ?? fallback
  return fallback
}
