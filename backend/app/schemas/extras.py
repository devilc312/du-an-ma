from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import Priority
from app.schemas.common import AwareDateTime, NonBlankStr


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    todo_id: UUID | None
    title: str
    message: str
    kind: str
    is_read: bool
    created_at: datetime
    read_at: datetime | None


class NotificationList(BaseModel):
    items: list[NotificationRead]
    unread_count: int


class WebSocketTicketResponse(BaseModel):
    ticket: str
    expires_in: int


class AISuggestRequest(BaseModel):
    title: NonBlankStr = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    due_at: AwareDateTime = None


class AISuggestResponse(BaseModel):
    summary: str = Field(min_length=1, max_length=500)
    suggested_description: str = Field(min_length=1, max_length=5000)
    subtasks: list[str] = Field(max_length=20)
    priority: Priority
    tips: list[str] = Field(max_length=20)
    provider: str


class AIChatRequest(BaseModel):
    message: NonBlankStr = Field(min_length=1, max_length=4000)
    conversation_id: UUID | None = None


class AIChatResponse(BaseModel):
    conversation_id: UUID
    answer: str
    provider: str


class AIMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    created_at: datetime


class AIConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class AIConversationDetail(AIConversationRead):
    messages: list[AIMessageRead]
