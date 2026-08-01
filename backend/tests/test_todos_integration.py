import pytest
from httpx import AsyncClient


async def register(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123",
            "full_name": "Todo User",
            "timezone": "Asia/Ho_Chi_Minh",
        },
    )
    assert response.status_code == 201
    return response.json()["csrf_token"]


@pytest.mark.asyncio
async def test_todo_category_stats_and_websocket_ticket(client: AsyncClient) -> None:
    csrf = await register(client, "todo-user@example.com")
    headers = {"X-CSRF-Token": csrf}

    category = await client.post(
        "/api/v1/categories",
        json={"name": "Công việc", "color": "#6366f1"},
        headers=headers,
    )
    assert category.status_code == 201
    category_id = category.json()["id"]

    todo = await client.post(
        "/api/v1/todos",
        json={
            "title": "Hoàn thiện dự án",
            "priority": "urgent",
            "category_id": category_id,
            "tags": ["Python", "python"],
            "due_at": "2026-08-02T12:00:00+07:00",
            "reminder_at": "2026-08-02T11:00:00+07:00",
        },
        headers=headers,
    )
    assert todo.status_code == 201
    assert todo.json()["category"]["id"] == category_id
    assert [tag["name"] for tag in todo.json()["tags"]] == ["python"]

    unfiltered = await client.get("/api/v1/todos")
    assert unfiltered.status_code == 200
    assert unfiltered.json()["total"] == 1

    empty_status = await client.get("/api/v1/todos", params={"status": ""})
    assert empty_status.status_code == 422

    stats = await client.get("/api/v1/todos/stats")
    assert stats.status_code == 200
    assert stats.json()["total"] == 1
    assert "archived" in stats.json()

    ticket = await client.post("/api/v1/notifications/ws-ticket", headers=headers)
    assert ticket.status_code == 200
    assert ticket.json()["expires_in"] > 0

    deleted = await client.delete(f"/api/v1/categories/{category_id}", headers=headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_todo_validation_rejects_naive_and_late_reminder(client: AsyncClient) -> None:
    csrf = await register(client, "validation@example.com")
    response = await client.post(
        "/api/v1/todos",
        json={
            "title": "Invalid schedule",
            "due_at": "2026-08-02T12:00:00",
            "reminder_at": "2026-08-02T13:00:00",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 422
