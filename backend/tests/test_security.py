from uuid import uuid4

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_round_trip() -> None:
    hashed = hash_password("StrongPass123")
    assert hashed != "StrongPass123"
    assert verify_password("StrongPass123", hashed)
    assert not verify_password("WrongPass123", hashed)


def test_access_token_round_trip() -> None:
    user_id = uuid4()
    token, expires_in = create_access_token(user_id)
    assert decode_access_token(token) == user_id
    assert expires_in > 0
