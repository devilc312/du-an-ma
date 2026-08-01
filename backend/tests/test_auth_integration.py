import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cookie_auth_csrf_refresh_and_logout(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "cookie-user@example.com",
            "password": "StrongPass123",
            "full_name": "Cookie User",
            "timezone": "Asia/Ho_Chi_Minh",
        },
    )
    assert response.status_code == 201
    assert "todo_access_token" in response.cookies
    assert "todo_refresh_token" in response.cookies
    csrf = response.json()["csrf_token"]
    assert "access_token" not in response.json()
    assert "refresh_token" not in response.json()

    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "cookie-user@example.com"

    rejected = await client.patch("/api/v1/auth/me", json={"full_name": "Rejected User"})
    assert rejected.status_code == 403

    updated = await client.patch(
        "/api/v1/auth/me",
        json={"full_name": "Updated User"},
        headers={"X-CSRF-Token": csrf},
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Updated User"

    old_refresh = client.cookies["todo_refresh_token"]
    refreshed = await client.post(
        "/api/v1/auth/refresh",
        headers={"X-CSRF-Token": csrf},
    )
    assert refreshed.status_code == 200
    assert client.cookies["todo_refresh_token"] != old_refresh
    csrf = refreshed.json()["csrf_token"]

    logged_out = await client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf},
    )
    assert logged_out.status_code == 204
    assert "todo_access_token" not in client.cookies
    assert "todo_refresh_token" not in client.cookies


@pytest.mark.asyncio
async def test_register_rejects_blank_name(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "blank@example.com",
            "password": "StrongPass123",
            "full_name": "   ",
        },
    )
    assert response.status_code == 422
