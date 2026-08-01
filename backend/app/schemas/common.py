import re
from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator


def non_blank(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Giá trị không được chỉ chứa khoảng trắng")
    return normalized


def optional_non_blank(value: str | None) -> str | None:
    return non_blank(value) if value is not None else None


def aware_datetime(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        raise ValueError("Ngày giờ phải kèm múi giờ")
    return value


def valid_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise ValueError("Múi giờ IANA không hợp lệ") from exc
    return value


def strong_password(value: str) -> str:
    if not re.search(r"[A-Z]", value) or not re.search(r"[a-z]", value) or not re.search(
        r"\d", value
    ):
        raise ValueError("Mật khẩu cần chữ hoa, chữ thường và chữ số")
    return value


NonBlankStr = Annotated[str, AfterValidator(non_blank)]
OptionalNonBlankStr = Annotated[str | None, AfterValidator(optional_non_blank)]
AwareDateTime = Annotated[datetime | None, AfterValidator(aware_datetime)]
TimezoneName = Annotated[str, AfterValidator(valid_timezone)]
StrongPassword = Annotated[str, AfterValidator(strong_password)]
