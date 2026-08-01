import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

from anthropic import AsyncAnthropic
from pydantic import ValidationError

from app.core.config import settings
from app.schemas import AISuggestResponse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn là trợ lý Todo AI thân thiện. Hỗ trợ quản lý thời gian, chia nhỏ việc,
đặt ưu tiên và hướng dẫn sử dụng ứng dụng. Trả lời bằng tiếng Việt, ngắn gọn, thực tế.
Không tuyên bố đã sửa hoặc xóa dữ liệu. Không yêu cầu bí mật, mật khẩu hay API key."""


@dataclass
class AIResult:
    content: str
    provider: str


class AIService:
    def __init__(self) -> None:
        self.client = (
            AsyncAnthropic(api_key=settings.anthropic_api_key)
            if settings.anthropic_api_key
            else None
        )

    async def chat(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> AIResult:
        if self.client and settings.ai_enabled:
            try:
                async with asyncio.timeout(settings.ai_timeout_seconds):
                    response = await self.client.messages.create(
                        model=settings.anthropic_model,
                        max_tokens=900,
                        system=SYSTEM_PROMPT,
                        messages=[*(history or []), {"role": "user", "content": message}],
                    )
                content = "".join(
                    block.text for block in response.content if block.type == "text"
                ).strip()
                if content:
                    return AIResult(content=content, provider="anthropic")
            except Exception:
                logger.warning("Anthropic request failed; using fallback", exc_info=True)
        return AIResult(content=self._fallback_chat(message), provider="fallback")

    async def suggest(
        self,
        title: str,
        description: str | None,
        due_at: str | None,
    ) -> dict[str, Any]:
        if self.client and settings.ai_enabled:
            prompt = f"""Phân tích công việc sau và chỉ trả JSON hợp lệ với các khóa summary,
suggested_description, subtasks (mảng), priority (low|medium|high|urgent), tips (mảng).
Tiêu đề: {title}\nMô tả: {description or 'Chưa có'}\nHạn: {due_at or 'Chưa đặt'}"""
            result = await self.chat(prompt)
            if result.provider == "anthropic":
                try:
                    raw = result.content.strip()
                    if raw.startswith("```"):
                        raw = raw.removeprefix("```json").removeprefix("```")
                        raw = raw.removesuffix("```").strip()
                    data = json.loads(raw)
                    data["provider"] = result.provider
                    return AISuggestResponse.model_validate(data).model_dump(mode="json")
                except (json.JSONDecodeError, TypeError, ValidationError):
                    logger.warning("Anthropic suggestion output was invalid; using fallback")
        return AISuggestResponse.model_validate(
            {
                "summary": f"Lập kế hoạch cho: {title}",
                "suggested_description": description
                or f"Xác định kết quả cần đạt và tiêu chí hoàn thành cho {title}.",
                "subtasks": [
                    "Xác định kết quả mong muốn",
                    "Chuẩn bị tài nguyên",
                    "Thực hiện bước quan trọng nhất",
                    "Kiểm tra và hoàn tất",
                ],
                "priority": "high" if due_at else "medium",
                "tips": [
                    "Bắt đầu bằng một bước dưới 15 phút",
                    "Đặt nhắc hạn trước thời điểm cần hoàn tất",
                ],
                "provider": "fallback",
            }
        ).model_dump(mode="json")

    @staticmethod
    def _fallback_chat(message: str) -> str:
        lowered = message.lower()
        if "hướng dẫn" in lowered or "sử dụng" in lowered:
            return (
                "Bạn có thể tạo việc ở nút “Thêm công việc”, đặt ưu tiên và hạn, "
                "sau đó dùng bộ lọc. Chuông thông báo lưu các nhắc hạn; Trợ lý AI "
                "giúp chia nhỏ công việc."
            )
        if "ưu tiên" in lowered:
            return (
                "Hãy ưu tiên theo mức độ khẩn cấp và tác động: việc vừa khẩn vừa quan trọng "
                "làm trước, việc quan trọng chưa khẩn nên đặt lịch cụ thể."
            )
        return (
            "Hãy mô tả kết quả mong muốn, thời hạn và trở ngại. Tôi sẽ giúp chia việc "
            "thành các bước nhỏ, dễ bắt đầu."
        )


ai_service = AIService()
