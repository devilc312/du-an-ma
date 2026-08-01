from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import AIConversation, AIMessage, User
from app.schemas import (
    AIChatRequest,
    AIChatResponse,
    AIConversationDetail,
    AIConversationRead,
    AISuggestRequest,
    AISuggestResponse,
)
from app.services.ai import ai_service
from app.services.notifications import check_rate_limit

router = APIRouter(prefix="/ai", tags=["AI Assistant"])


async def owned_conversation(
    db: AsyncSession,
    user_id: UUID,
    conversation_id: UUID,
) -> AIConversation:
    conversation = (
        await db.scalars(
            select(AIConversation)
            .options(selectinload(AIConversation.messages))
            .where(
                AIConversation.id == conversation_id,
                AIConversation.user_id == user_id,
            )
        )
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Không tìm thấy cuộc trò chuyện")
    return conversation


@router.get("/conversations", response_model=list[AIConversationRead])
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AIConversation]:
    return list(
        await db.scalars(
            select(AIConversation)
            .where(AIConversation.user_id == user.id)
            .order_by(AIConversation.updated_at.desc(), AIConversation.id.desc())
            .limit(100)
        )
    )


@router.get("/conversations/{conversation_id}", response_model=AIConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AIConversation:
    return await owned_conversation(db, user.id, conversation_id)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    conversation = await owned_conversation(db, user.id, conversation_id)
    await db.delete(conversation)
    await db.commit()


@router.post("/suggest", response_model=AISuggestResponse)
async def suggest(
    payload: AISuggestRequest,
    request: Request,
    user: User = Depends(get_current_user),
) -> AISuggestResponse:
    if not await check_rate_limit(f"ai:{user.id}", 30, 3600):
        raise HTTPException(status_code=429, detail="Bạn đã dùng AI quá nhanh, vui lòng thử lại sau")
    data = await ai_service.suggest(
        payload.title,
        payload.description,
        payload.due_at.isoformat() if payload.due_at else None,
    )
    return AISuggestResponse(**data)


@router.post("/chat", response_model=AIChatResponse)
async def chat(
    payload: AIChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AIChatResponse:
    if not await check_rate_limit(f"ai:{user.id}", 30, 3600):
        raise HTTPException(status_code=429, detail="Bạn đã dùng AI quá nhanh, vui lòng thử lại sau")
    if payload.conversation_id:
        conversation = await owned_conversation(db, user.id, payload.conversation_id)
    else:
        conversation = AIConversation(user_id=user.id, title=payload.message[:100])
        db.add(conversation)
        await db.flush()
    history = [
        {"role": message.role, "content": message.content}
        for message in conversation.messages[-10:]
    ]
    result = await ai_service.chat(payload.message, history)
    db.add_all(
        [
            AIMessage(conversation_id=conversation.id, role="user", content=payload.message),
            AIMessage(conversation_id=conversation.id, role="assistant", content=result.content),
        ]
    )
    conversation.updated_at = datetime.now(UTC)
    await db.commit()
    return AIChatResponse(
        conversation_id=conversation.id,
        answer=result.content,
        provider=result.provider,
    )
