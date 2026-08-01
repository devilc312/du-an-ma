export type Role = 'user' | 'admin'
export type TodoPriority = 'low' | 'medium' | 'high' | 'urgent'
export type TodoStatus = 'pending' | 'in_progress' | 'completed' | 'archived'

export interface User {
  id: string
  email: string
  full_name: string
  timezone: string
  is_active: boolean
  roles: Role[]
  created_at: string
}

export interface AuthResponse { expires_in: number; csrf_token: string; user: User }
export interface Category { id: string; name: string; color: string }
export interface Tag { id: string; name: string }
export interface Todo {
  id: string
  title: string
  description: string | null
  status: TodoStatus
  priority: TodoPriority
  due_at: string | null
  reminder_at: string | null
  completed_at: string | null
  category: Category | null
  tags: Tag[]
  created_at: string
  updated_at: string
}
export interface TodoInput { title: string; description?: string | null; status?: TodoStatus; priority?: TodoPriority; due_at?: string | null; reminder_at?: string | null; category_id?: string | null; tags?: string[] }
export interface Paginated<T> { items: T[]; page: number; page_size: number; total: number; pages: number }
export interface DashboardStats { total: number; pending: number; in_progress: number; completed: number; archived: number; overdue: number; due_today: number }
export interface Notification { id: string; todo_id: string | null; kind: string; title: string; message: string; is_read: boolean; read_at: string | null; created_at: string }
export interface NotificationList { items: Notification[]; unread_count: number }
export interface AiSuggestion { summary: string; suggested_description: string; subtasks: string[]; priority: TodoPriority; tips: string[]; provider: string }
export interface ChatMessage { id: string; role: 'user' | 'assistant'; content: string; created_at: string }
export interface ChatResponse { conversation_id: string; answer: string; provider: string }
export interface Conversation { id: string; title: string; created_at: string; updated_at: string }
export interface ConversationDetail extends Conversation { messages: ChatMessage[] }
export type AdminUser = User
