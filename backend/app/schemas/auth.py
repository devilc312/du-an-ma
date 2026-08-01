from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import NonBlankStr, StrongPassword, TimezoneName


class UserRegister(BaseModel):
    email: EmailStr
    password: StrongPassword = Field(min_length=8, max_length=128)
    full_name: NonBlankStr = Field(min_length=2, max_length=120)
    timezone: TimezoneName = "Asia/Ho_Chi_Minh"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class UserUpdate(BaseModel):
    full_name: NonBlankStr | None = Field(default=None, min_length=2, max_length=120)
    timezone: TimezoneName | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    timezone: str
    is_active: bool
    roles: list[str] = Field(default_factory=list)
    created_at: datetime


class AuthResponse(BaseModel):
    expires_in: int
    csrf_token: str
    user: UserRead


class RoleUpdate(BaseModel):
    roles: list[str] = Field(min_length=1)


class ActiveUpdate(BaseModel):
    is_active: bool
