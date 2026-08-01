from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token, verify_csrf
from app.models import User

bearer = HTTPBearer(auto_error=False)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_request_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> tuple[str | None, bool]:
    if credentials is not None:
        return credentials.credentials, False
    return request.cookies.get(settings.access_cookie_name), True


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    token, cookie_auth = get_request_token(request, credentials)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bạn chưa đăng nhập")
    if cookie_auth and request.method not in SAFE_METHODS:
        verify_csrf(request)
    user_id = decode_access_token(token)
    user = (await db.scalars(select(User).where(User.id == user_id))).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản không tồn tại hoặc đã bị khóa",
        )
    return user


def require_role(role: str) -> Callable:
    async def checker(user: User = Depends(get_current_user)) -> User:
        if not user.has_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện thao tác này",
            )
        return user

    return checker
