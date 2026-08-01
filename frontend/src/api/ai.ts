import { api } from './client'
import type { AiSuggestion, ChatResponse, Conversation, ConversationDetail, Notification, NotificationList } from '../types'

export const notificationsApi = {
  async list(params?: { limit?: number; unread_only?: boolean }) { return (await api.get<NotificationList>('/notifications', { params })).data },
  async ticket() { return (await api.post<{ ticket: string; expires_in: number }>('/notifications/ws-ticket')).data },
  async markRead(id: string) { return (await api.patch<Notification>(`/notifications/${id}/read`)).data },
  async markAllRead() { await api.post('/notifications/read-all') },
  async remove(id: string) { await api.delete(`/notifications/${id}`) },
}

export const aiApi = {
  async suggest(input: { title: string; description?: string | null; due_at?: string | null }) { return (await api.post<AiSuggestion>('/ai/suggest', input)).data },
  async chat(message: string, conversation_id?: string) { return (await api.post<ChatResponse>('/ai/chat', { message, conversation_id })).data },
  async conversations() { return (await api.get<Conversation[]>('/ai/conversations')).data },
  async conversation(id: string) { return (await api.get<ConversationDetail>(`/ai/conversations/${id}`)).data },
  async removeConversation(id: string) { await api.delete(`/ai/conversations/${id}`) },
}
