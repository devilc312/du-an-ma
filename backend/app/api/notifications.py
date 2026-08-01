import asyncio
import json
import secrets
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.redis import redis_client
from app.models import Notification, User
from app.schemas import NotificationList, NotificationRead, WebSocketTicketResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])
ws_router = APIRouter(tags=["Realtime"])


@router.get("", response_model=NotificationList)
async def list_notifications(
    unread_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationList:
    query = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    items = list(await db.scalars(query.order_by(Notification.created_at.desc()).limit(limit)))
    count = await db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user.id,
            Notification.is_read.is_(False),
        )
    )
    return NotificationList(items=items, unread_count=count or 0)


@router.post("/ws-ticket", response_model=WebSocketTicketResponse)
async def create_ws_ticket(user: User = Depends(get_current_user)) -> WebSocketTicketResponse:
    ticket = secrets.token_urlsafe(32)
    key = f"ws-ticket:{ticket}"
    created = await redis_client.set(
        key,
        str(user.id),
        ex=settings.websocket_ticket_ttl_seconds,
        nx=True,
    )
    if not created:
        raise HTTPException(status_code=503, detail="Không thể tạo vé WebSocket")
    return WebSocketTicketResponse(
        ticket=ticket,
        expires_in=settings.websocket_ticket_ttl_seconds,
    )


@router.patch("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Notification:
    item = (
        await db.scalars(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user.id,
            )
        )
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo")
    item.is_read = True
    item.read_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(item)
    return item


@router.post("/read-all", status_code=204)
async def mark_all_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read.is_(False))
        .values(is_read=True, read_at=datetime.now(UTC))
    )
    await db.commit()


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    item = (
        await db.scalars(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user.id,
            )
        )
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo")
    await db.delete(item)
    await db.commit()


@ws_router.websocket("/ws/notifications")
async def notification_socket(websocket: WebSocket, ticket: str = Query(...)) -> None:
    user_id = await redis_client.getdel(f"ws-ticket:{ticket}")
    if not user_id:
        await websocket.close(code=4401)
        return
    async with AsyncSessionLocal() as db:
        user = (
            await db.scalars(
                select(User).where(User.id == UUID(user_id), User.is_active.is_(True))
            )
        ).first()
        if not user:
            await websocket.close(code=4401)
            return
    await websocket.accept()
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"notifications:{user_id}")
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=20)
            if message:
                await websocket.send_json(json.loads(message["data"]))
            else:
                await websocket.send_json({"type": "ping"})
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(f"notifications:{user_id}")
        await pubsub.aclose()
