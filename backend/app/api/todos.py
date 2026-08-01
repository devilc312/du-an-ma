import math
from datetime import UTC, datetime, time
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Category, Priority, Tag, Todo, TodoStatus, User
from app.schemas import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    DashboardStats,
    TodoCreate,
    TodoList,
    TodoRead,
    TodoUpdate,
)

router = APIRouter(prefix="/todos", tags=["Todos"])
categories_router = APIRouter(prefix="/categories", tags=["Categories"])


async def owned_todo(db: AsyncSession, user_id: UUID, todo_id: UUID) -> Todo:
    todo = (
        await db.scalars(
            select(Todo)
            .options(selectinload(Todo.category), selectinload(Todo.tags))
            .where(Todo.id == todo_id, Todo.user_id == user_id)
        )
    ).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Không tìm thấy công việc")
    return todo


async def owned_category(db: AsyncSession, user_id: UUID, category_id: UUID) -> Category:
    category = (
        await db.scalars(
            select(Category).where(Category.id == category_id, Category.user_id == user_id)
        )
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Không tìm thấy danh mục")
    return category


async def resolve_tags(db: AsyncSession, user_id: UUID, names: list[str]) -> list[Tag]:
    normalized = list(dict.fromkeys(name.strip().lower() for name in names if name.strip()))
    if not normalized:
        return []
    existing = list(
        await db.scalars(select(Tag).where(Tag.user_id == user_id, Tag.name.in_(normalized)))
    )
    existing_names = {tag.name for tag in existing}
    new = [Tag(user_id=user_id, name=name) for name in normalized if name not in existing_names]
    db.add_all(new)
    return [*existing, *new]


@router.get("", response_model=TodoList)
async def list_todos(
    search: str | None = None,
    todo_status: TodoStatus | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    category_id: UUID | None = None,
    due_after: datetime | None = None,
    due_before: datetime | None = None,
    sort: str = Query(default="updated_at", pattern="^(created_at|updated_at|due_at|priority|title)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TodoList:
    filters = [Todo.user_id == user.id]
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        filters.append(or_(Todo.title.ilike(pattern), Todo.description.ilike(pattern)))
    if todo_status:
        filters.append(Todo.status == todo_status)
    if priority:
        filters.append(Todo.priority == priority)
    if category_id:
        filters.append(Todo.category_id == category_id)
    if due_after:
        filters.append(Todo.due_at >= due_after)
    if due_before:
        filters.append(Todo.due_at <= due_before)
    total = await db.scalar(select(func.count()).select_from(Todo).where(*filters)) or 0
    sort_column = {
        "created_at": Todo.created_at,
        "updated_at": Todo.updated_at,
        "due_at": Todo.due_at,
        "priority": Todo.priority,
        "title": Todo.title,
    }[sort]
    ordering = sort_column.asc() if order == "asc" else sort_column.desc()
    items = list(
        await db.scalars(
            select(Todo)
            .options(selectinload(Todo.category), selectinload(Todo.tags))
            .where(*filters)
            .order_by(ordering.nullslast(), Todo.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return TodoList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.post("", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
async def create_todo(
    payload: TodoCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Todo:
    data = payload.model_dump(exclude={"tags"})
    if data.get("category_id"):
        await owned_category(db, user.id, data["category_id"])
    todo = Todo(user_id=user.id, **data)
    todo.tags = await resolve_tags(db, user.id, payload.tags)
    if todo.status == TodoStatus.completed:
        todo.completed_at = datetime.now(UTC)
    db.add(todo)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Tag hoặc công việc bị trùng") from exc
    return await owned_todo(db, user.id, todo.id)


@router.get("/stats", response_model=DashboardStats)
async def stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    now = datetime.now(UTC)
    timezone = ZoneInfo(user.timezone)
    local_date = now.astimezone(timezone).date()
    day_start = datetime.combine(local_date, time.min, tzinfo=timezone).astimezone(UTC)
    day_end = datetime.combine(local_date, time.max, tzinfo=timezone).astimezone(UTC)
    row = (
        await db.execute(
            select(
                func.count(Todo.id),
                func.sum(case((Todo.status == TodoStatus.pending, 1), else_=0)),
                func.sum(case((Todo.status == TodoStatus.in_progress, 1), else_=0)),
                func.sum(case((Todo.status == TodoStatus.completed, 1), else_=0)),
                func.sum(case((Todo.status == TodoStatus.archived, 1), else_=0)),
                func.sum(
                    case(
                        (
                            (Todo.due_at < now)
                            & Todo.status.not_in([TodoStatus.completed, TodoStatus.archived]),
                            1,
                        ),
                        else_=0,
                    )
                ),
                func.sum(case((Todo.due_at.between(day_start, day_end), 1), else_=0)),
            ).where(Todo.user_id == user.id)
        )
    ).one()
    return DashboardStats(
        total=row[0] or 0,
        pending=row[1] or 0,
        in_progress=row[2] or 0,
        completed=row[3] or 0,
        archived=row[4] or 0,
        overdue=row[5] or 0,
        due_today=row[6] or 0,
    )


@router.get("/{todo_id}", response_model=TodoRead)
async def get_todo(
    todo_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Todo:
    return await owned_todo(db, user.id, todo_id)


@router.patch("/{todo_id}", response_model=TodoRead)
async def update_todo(
    todo_id: UUID,
    payload: TodoUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Todo:
    todo = await owned_todo(db, user.id, todo_id)
    data = payload.model_dump(exclude_unset=True, exclude={"tags"})
    if "category_id" in data and data["category_id"]:
        await owned_category(db, user.id, data["category_id"])
    old_status = todo.status
    for key, value in data.items():
        setattr(todo, key, value)
    if payload.tags is not None:
        todo.tags = await resolve_tags(db, user.id, payload.tags)
    if todo.status == TodoStatus.completed and old_status != TodoStatus.completed:
        todo.completed_at = datetime.now(UTC)
    elif todo.status != TodoStatus.completed:
        todo.completed_at = None
    if "reminder_at" in data or "due_at" in data:
        todo.reminder_sent_at = None
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Dữ liệu cập nhật bị trùng") from exc
    return await owned_todo(db, user.id, todo.id)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_todo(
    todo_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    todo = await owned_todo(db, user.id, todo_id)
    await db.delete(todo)
    await db.commit()


@categories_router.get("", response_model=list[CategoryRead])
async def list_categories(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Category]:
    return list(
        await db.scalars(
            select(Category).where(Category.user_id == user.id).order_by(Category.name)
        )
    )


@categories_router.post("", response_model=CategoryRead, status_code=201)
async def create_category(
    payload: CategoryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Category:
    category = Category(user_id=user.id, **payload.model_dump())
    db.add(category)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Danh mục đã tồn tại") from exc
    await db.refresh(category)
    return category


@categories_router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Category:
    category = await owned_category(db, user.id, category_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Danh mục đã tồn tại") from exc
    await db.refresh(category)
    return category


@categories_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    category = await owned_category(db, user.id, category_id)
    await db.delete(category)
    await db.commit()
