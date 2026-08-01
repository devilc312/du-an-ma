import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import redis_client
from app.models import Notification, Todo, TodoStatus
from app.services.notifications import publish_notification

logger = logging.getLogger(__name__)


async def process_reminders() -> int:
    lock = redis_client.lock("worker:reminders", timeout=55, blocking_timeout=1)
    if not await lock.acquire():
        return 0
    payloads: list[tuple[str, dict[str, Any]]] = []
    try:
        now = datetime.now(UTC)
        window = now + timedelta(minutes=settings.reminder_window_minutes)
        async with AsyncSessionLocal() as db:
            todos = list(
                await db.scalars(
                    select(Todo)
                    .where(
                        Todo.status.not_in([TodoStatus.completed, TodoStatus.archived]),
                        Todo.reminder_sent_at.is_(None),
                        or_(
                            Todo.reminder_at.between(now, window),
                            (Todo.reminder_at.is_(None) & Todo.due_at.between(now, window)),
                        ),
                    )
                    .with_for_update(skip_locked=True)
                )
            )
            for todo in todos:
                notification = Notification(
                    user_id=todo.user_id,
                    todo_id=todo.id,
                    title="Công việc sắp đến hạn",
                    message=f"“{todo.title}” sắp đến thời hạn. Hãy kiểm tra tiến độ.",
                    kind="reminder",
                )
                db.add(notification)
                await db.flush()
                todo.reminder_sent_at = now
                payloads.append(
                    (
                        str(todo.user_id),
                        {
                            "type": "notification",
                            "data": {
                                "id": str(notification.id),
                                "todo_id": str(todo.id),
                                "title": notification.title,
                                "message": notification.message,
                                "kind": notification.kind,
                                "is_read": False,
                                "created_at": notification.created_at.isoformat(),
                            },
                        },
                    )
                )
            await db.commit()
        for user_id, payload in payloads:
            try:
                await publish_notification(user_id, payload)
            except Exception:
                logger.exception("Failed to publish committed reminder notification")
    finally:
        try:
            await lock.release()
        except Exception:
            logger.warning("Reminder lock was already released", exc_info=True)
    return len(payloads)


async def run() -> None:
    logger.info("Reminder worker started")
    try:
        while True:
            try:
                count = await process_reminders()
                if count:
                    logger.info("Published %s reminders", count)
            except Exception:
                logger.exception("Reminder iteration failed")
            await asyncio.sleep(30)
    finally:
        await redis_client.aclose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
