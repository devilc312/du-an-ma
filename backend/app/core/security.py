import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import HTTPException, Request, Response, status
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(user_id: UUID) -> tuple[str, int]:
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expires_at = datetime.now(UTC) + expires_delta
    payload = {"sub": str(user_id), "type": "access", "exp": expires_at, "iat": datetime.now(UTC)}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM), int(
        expires_delta.total_seconds()
    )


def decode_access_token(token: str) -> UUID:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != "access" or not payload.get("sub"):
            raise credentials_error
        return UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError) as exc:
        raise credentials_error from exc


def create_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    return raw, hash_token(raw)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
    access_max_age: int,
) -> None:
    common = {
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "domain": settings.cookie_domain,
        "path": "/",
    }
    response.set_cookie(
        settings.access_cookie_name,
        access_token,
        max_age=access_max_age,
        httponly=True,
        **common,
    )
    response.set_cookie(
        settings.refresh_cookie_name,
        refresh_token,
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=True,
        **common,
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=False,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    for name in (
        settings.access_cookie_name,
        settings.refresh_cookie_name,
        settings.csrf_cookie_name,
    ):
        response.delete_cookie(
            name,
            path="/",
            domain=settings.cookie_domain,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
        )


def verify_csrf(request: Request) -> None:
    cookie = request.cookies.get(settings.csrf_cookie_name)
    header = request.headers.get(settings.csrf_header_name)
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise HTTPException(status_code=403, detail="CSRF token không hợp lệ")

    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") not in settings.cors_origin_list:
        raise HTTPException(status_code=403, detail="Nguồn yêu cầu không được phép")
