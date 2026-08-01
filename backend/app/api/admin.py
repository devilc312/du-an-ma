from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import to_user_read
from app.api.deps import require_role
from app.core.database import get_db
from app.models import AuditLog, Role, User
from app.schemas import ActiveUpdate, RoleUpdate, UserRead
from app.services.auth import cleanup_user_tokens

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=list[UserRead])
async def list_users(
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[UserRead]:
    query = select(User).order_by(User.created_at.desc()).limit(limit)
    if search:
        query = query.where(User.email.ilike(f"%{search}%") | User.full_name.ilike(f"%{search}%"))
    users = list(await db.scalars(query))
    return [to_user_read(user) for user in users]


@router.get("/roles", response_model=list[str])
async def list_roles(_: User = Depends(require_role("admin")), db: AsyncSession = Depends(get_db)) -> list[str]:
    return list(await db.scalars(select(Role.name).order_by(Role.name)))


@router.put("/users/{user_id}/roles", response_model=UserRead)
async def set_roles(
    user_id: UUID,
    payload: RoleUpdate,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    user = (await db.scalars(select(User).where(User.id == user_id).with_for_update())).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
    roles = list(await db.scalars(select(Role).where(Role.name.in_(set(payload.roles)))))
    if len(roles) != len(set(payload.roles)):
        raise HTTPException(status_code=400, detail="Có vai trò không hợp lệ")
    removing_admin = user.has_role("admin") and all(role.name != "admin" for role in roles)
    if removing_admin:
        admin_count = await db.scalar(
            select(func.count()).select_from(User).join(User.roles).where(Role.name == "admin", User.is_active.is_(True))
        )
        if (admin_count or 0) <= 1:
            raise HTTPException(status_code=409, detail="Không thể gỡ quản trị viên hoạt động cuối cùng")
    user.roles = roles
    db.add(AuditLog(actor_id=admin.id, action="roles.updated", target_type="user", target_id=str(user.id), details={"roles": payload.roles}))
    await db.commit()
    await db.refresh(user, attribute_names=["roles"])
    return to_user_read(user)


@router.patch("/users/{user_id}/active", response_model=UserRead)
async def set_active(
    user_id: UUID,
    payload: ActiveUpdate,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    user = (await db.scalars(select(User).where(User.id == user_id).with_for_update())).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(status_code=409, detail="Không thể tự khóa tài khoản đang sử dụng")
    if user.has_role("admin") and not payload.is_active:
        active_admins = await db.scalar(
            select(func.count()).select_from(User).join(User.roles).where(Role.name == "admin", User.is_active.is_(True))
        )
        if (active_admins or 0) <= 1:
            raise HTTPException(status_code=409, detail="Không thể khóa quản trị viên hoạt động cuối cùng")
    user.is_active = payload.is_active
    user.updated_at = datetime.now(UTC)
    db.add(AuditLog(actor_id=admin.id, action="user.active.updated", target_type="user", target_id=str(user.id), details={"is_active": payload.is_active}))
    await db.commit()
    if not payload.is_active:
        await cleanup_user_tokens(db, user.id)
    await db.refresh(user, attribute_names=["roles"])
    return to_user_read(user)
