from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_token
from app.models import RefreshToken, Role, User


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    expires_in: int


async def cleanup_expired_tokens(db: AsyncSession, user_id: UUID | None = None) -> None:
    cutoff = datetime.now(UTC) - timedelta(days=settings.refresh_token_retention_days)
    filters = [
        or_(
            RefreshToken.expires_at <= datetime.now(UTC),
            RefreshToken.revoked_at.is_not(None) & (RefreshToken.revoked_at <= cutoff),
        )
    ]
    if user_id is not None:
        filters.append(RefreshToken.user_id == user_id)
    await db.execute(delete(RefreshToken).where(*filters))


async def issue_tokens(db: AsyncSession, user: User) -> IssuedTokens:
    await cleanup_expired_tokens(db, user.id)
    access, expires_in = create_access_token(user.id)
    raw_refresh, token_hash = create_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    await db.commit()
    return IssuedTokens(access, raw_refresh, expires_in)


async def rotate_refresh_token(db: AsyncSession, raw_token: str) -> tuple[User, IssuedTokens]:
    token = (
        await db.scalars(
            select(RefreshToken)
            .where(RefreshToken.token_hash == hash_token(raw_token))
            .with_for_update()
        )
    ).first()
    now = datetime.now(UTC)
    if not token or token.revoked_at or token.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token không hợp lệ",
        )
    token.revoked_at = now
    user = (await db.scalars(select(User).where(User.id == token.user_id))).first()
    if not user or not user.is_active:
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản không hoạt động",
        )
    access, expires_in = create_access_token(user.id)
    raw_refresh, new_hash = create_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=new_hash,
            expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    await cleanup_expired_tokens(db, user.id)
    await db.commit()
    return user, IssuedTokens(access, raw_refresh, expires_in)


async def revoke_refresh_token(db: AsyncSession, raw_token: str | None) -> None:
    if not raw_token:
        return
    token = (
        await db.scalars(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw_token))
        )
    ).first()
    if token and not token.revoked_at:
        token.revoked_at = datetime.now(UTC)
        await db.commit()


async def cleanup_user_tokens(db: AsyncSession, user_id: UUID) -> None:
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
    await db.commit()


async def default_user_role(db: AsyncSession) -> Role:
    role = (await db.scalars(select(Role).where(Role.name == "user"))).first()
    if not role:
        role = Role(name="user", description="Người dùng tiêu chuẩn")
        db.add(role)
        await db.flush()
    return role
