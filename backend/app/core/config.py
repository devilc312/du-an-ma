from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SECRET = "development-secret-change-me-please-32-chars"
DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = "ChangeMe123!"
DEFAULT_DATABASE_URL = "postgresql+asyncpg://todo:todo@localhost:5432/todo"


class Settings(BaseSettings):
    app_name: str = "Todo AI"
    environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = DEFAULT_SECRET
    access_token_expire_minutes: int = Field(default=15, ge=1, le=1440)
    refresh_token_expire_days: int = Field(default=30, ge=1, le=365)
    refresh_token_retention_days: int = Field(default=7, ge=0, le=90)
    database_url: str = DEFAULT_DATABASE_URL
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    default_timezone: str = "Asia/Ho_Chi_Minh"
    admin_email: str = DEFAULT_ADMIN_EMAIL
    admin_password: str = DEFAULT_ADMIN_PASSWORD
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"
    ai_enabled: bool = True
    ai_timeout_seconds: float = Field(default=20.0, ge=1, le=120)
    reminder_window_minutes: int = Field(default=15, ge=1, le=1440)
    access_cookie_name: str = "todo_access_token"
    refresh_cookie_name: str = "todo_refresh_token"
    csrf_cookie_name: str = "todo_csrf_token"
    csrf_header_name: str = "X-CSRF-Token"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_domain: str | None = None
    websocket_ticket_ttl_seconds: int = Field(default=30, ge=5, le=300)

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("SECRET_KEY must have at least 32 characters")
        return value

    @field_validator("api_v1_prefix")
    @classmethod
    def normalize_api_prefix(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("/"):
            value = f"/{value}"
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true when COOKIE_SAMESITE=none")
        if self.environment == "production":
            unsafe = []
            if self.secret_key == DEFAULT_SECRET:
                unsafe.append("SECRET_KEY")
            if self.admin_email == DEFAULT_ADMIN_EMAIL:
                unsafe.append("ADMIN_EMAIL")
            if self.admin_password == DEFAULT_ADMIN_PASSWORD:
                unsafe.append("ADMIN_PASSWORD")
            if self.database_url == DEFAULT_DATABASE_URL or ":todo@" in self.database_url:
                unsafe.append("DATABASE_URL")
            if not self.cookie_secure:
                unsafe.append("COOKIE_SECURE")
            if unsafe:
                raise ValueError(
                    "Unsafe production settings: " + ", ".join(sorted(set(unsafe)))
                )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip().rstrip("/") for origin in self.cors_origins.split(",")]
        origins = list(dict.fromkeys(origin for origin in origins if origin))
        if "*" in origins:
            raise ValueError("CORS_ORIGINS cannot contain '*' when credentials are enabled")
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
