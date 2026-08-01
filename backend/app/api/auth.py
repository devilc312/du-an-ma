from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    clear_auth_cookies,
    create_csrf_token,
    hash_password,
    set_auth_cookies,
    verify_csrf,
    verify_password,
)
from app.models import User
from app.schemas import AuthResponse, LoginRequest, UserRead, UserRegister, UserUpdate
from app.services.auth import (
    default_user_role,
    issue_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.services.notifications import check_rate_limit

router = APIRouter(prefix="/auth", tags=["Authentication"])


def to_user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        timezone=user.timezone,
        is_active=user.is_active,
        roles=user.role_names,
        created_at=user.created_at,
    )


def build_auth_response(response: Response, user: User, tokens) -> AuthResponse:
    csrf_token = create_csrf_token()
    set_auth_cookies(
        response,
        tokens.access_token,
        tokens.refresh_token,
        csrf_token,
        tokens.expires_in,
    )
    return AuthResponse(
        expires_in=tokens.expires_in,
        csrf_token=csrf_token,
        user=to_user_read(user),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegister,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    client = request.client.host if request.client else "unknown"
    if not await check_rate_limit(f"register:{client}", 10, 3600):
        raise HTTPException(status_code=429, detail="Bạn đã thử quá nhiều lần")
    email = payload.email.lower()
    if await db.scalar(select(func.count()).select_from(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email đã được sử dụng")
    role = await default_user_role(db)
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        timezone=payload.timezone,
        roles=[role],
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email đã được sử dụng") from exc
    await db.refresh(user, attribute_names=["roles"])
    tokens = await issue_tokens(db, user)
    return build_auth_response(response, user, tokens)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    client = request.client.host if request.client else "unknown"
    if not await check_rate_limit(f"login:{client}:{payload.email.lower()}", 10, 900):
        raise HTTPException(status_code=429, detail="Đăng nhập bị tạm khóa, vui lòng thử lại sau")
    user = (await db.scalars(select(User).where(User.email == payload.email.lower()))).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không đúng",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa")
    tokens = await issue_tokens(db, user)
    return build_auth_response(response, user, tokens)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    verify_csrf(request)
    client = request.client.host if request.client else "unknown"
    if not await check_rate_limit(f"refresh:{client}", 60, 900):
        raise HTTPException(status_code=429, detail="Làm mới phiên quá nhanh")
    raw_token = request.cookies.get(settings.refresh_cookie_name)
    if not raw_token:
        raise HTTPException(status_code=401, detail="Không có refresh token")
    try:
        user, tokens = await rotate_refresh_token(db, raw_token)
    except HTTPException:
        clear_auth_cookies(response)
        raise
    return build_auth_response(response, user, tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> Response:
    verify_csrf(request)
    await revoke_refresh_token(db, request.cookies.get(settings.refresh_cookie_name))
    clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(get_current_user)) -> UserRead:
    return to_user_read(user)


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    user.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(user, attribute_names=["roles"])
    return to_user_read(user)
