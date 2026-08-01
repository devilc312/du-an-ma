from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import Priority, TodoStatus
from app.schemas.common import AwareDateTime, NonBlankStr


class CategoryCreate(BaseModel):
    name: NonBlankStr = Field(min_length=1, max_length=80)
    color: str = Field(default="#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")


class CategoryUpdate(BaseModel):
    name: NonBlankStr | None = Field(default=None, min_length=1, max_length=80)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class CategoryRead(CategoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class TagRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str


class TodoValues(BaseModel):
    @field_validator("tags", check_fields=False)
    @classmethod
    def normalize_tags(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        normalized = [value.strip().lower() for value in values if value.strip()]
        if any(len(value) > 40 for value in normalized):
            raise ValueError("Tag tối đa 40 ký tự")
        return list(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def validate_schedule(self) -> "TodoValues":
        due_at = getattr(self, "due_at", None)
        reminder_at = getattr(self, "reminder_at", None)
        if due_at and reminder_at and reminder_at > due_at:
            raise ValueError("Thời gian nhắc phải trước hoặc bằng hạn hoàn thành")
        return self


class TodoCreate(TodoValues):
    title: NonBlankStr = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TodoStatus = TodoStatus.pending
    priority: Priority = Priority.medium
    due_at: AwareDateTime = None
    reminder_at: AwareDateTime = None
    category_id: UUID | None = None
    tags: list[str] = Field(default_factory=list, max_length=10)


class TodoUpdate(TodoValues):
    title: NonBlankStr | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TodoStatus | None = None
    priority: Priority | None = None
    due_at: AwareDateTime = None
    reminder_at: AwareDateTime = None
    category_id: UUID | None = None
    tags: list[str] | None = Field(default=None, max_length=10)


class TodoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    status: TodoStatus
    priority: Priority
    due_at: datetime | None
    reminder_at: datetime | None
    completed_at: datetime | None
    category: CategoryRead | None
    tags: list[TagRead]
    created_at: datetime
    updated_at: datetime


class TodoList(BaseModel):
    items: list[TodoRead]
    total: int
    page: int
    page_size: int
    pages: int


class DashboardStats(BaseModel):
    total: int
    pending: int
    in_progress: int
    completed: int
    archived: int
    overdue: int
    due_today: int
