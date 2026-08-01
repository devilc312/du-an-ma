import pytest
from pydantic import ValidationError

from app.schemas import UserRegister


def test_new_registration_schema_has_user_data_without_roles() -> None:
    payload = UserRegister(
        email="person@example.com",
        password="StrongPass123",
        full_name="Test Person",
        timezone="Asia/Ho_Chi_Minh",
    )
    assert payload.email == "person@example.com"
    assert not hasattr(payload, "roles")


def test_password_policy() -> None:
    with pytest.raises(ValidationError):
        UserRegister(
            email="person@example.com",
            password="weakpassword",
            full_name="Test Person",
        )
