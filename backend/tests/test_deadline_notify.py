"""Tests for registration deadline and host notification features."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


@pytest.fixture
async def host_cookies(client: AsyncClient):
    mock_verify = AsyncMock(return_value=True)
    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800400001", "code": "123456",
        })
        return {"events_token": resp.cookies.get("events_token")}


@pytest.fixture
async def user_cookies(client: AsyncClient):
    mock_verify = AsyncMock(return_value=True)
    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800400002", "code": "654321",
        })
        return {"events_token": resp.cookies.get("events_token")}


@pytest.mark.asyncio
async def test_create_event_with_deadline(client: AsyncClient, host_cookies):
    """Event can be created with registration_deadline."""
    resp = await client.post("/api/v1/events", json={
        "title": "Deadline Test",
        "event_type": "online",
        "start_time": "2026-12-01T10:00:00+08:00",
        "registration_deadline": "2026-11-28T23:59:00+08:00",
    }, cookies=host_cookies)

    assert resp.status_code == 201
    data = resp.json()["data"]
    slug = data["slug"]

    resp = await client.get(f"/api/v1/events/{slug}")
    event = resp.json()["data"]
    assert event["registration_deadline"] is not None
    assert "2026-11-28" in event["registration_deadline"]


@pytest.mark.asyncio
async def test_registration_rejected_after_deadline(client: AsyncClient, host_cookies, user_cookies):
    """Registration is blocked after the deadline passes."""
    resp = await client.post("/api/v1/events", json={
        "title": "Past Deadline Event",
        "event_type": "online",
        "start_time": "2026-12-01T10:00:00+08:00",
        "registration_deadline": "2020-01-01T00:00:00+08:00",
    }, cookies=host_cookies)

    assert resp.status_code == 201
    event_data = resp.json()["data"]
    slug = event_data["slug"]
    event_id = event_data["id"]

    with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as mock_pub:
        mock_pub.return_value = None
        await client.post(f"/api/v1/events/{event_id}/publish", cookies=host_cookies)

    resp = await client.post(f"/api/v1/events/{slug}/register", json={}, cookies=user_cookies)
    assert resp.status_code == 400
    assert "截止" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_registration_allowed_before_deadline(client: AsyncClient, host_cookies, user_cookies):
    """Registration succeeds when deadline is in the future."""
    resp = await client.post("/api/v1/events", json={
        "title": "Future Deadline Event",
        "event_type": "online",
        "start_time": "2030-12-01T10:00:00+08:00",
        "registration_deadline": "2030-11-30T23:59:00+08:00",
        "require_approval": False,
    }, cookies=host_cookies)

    assert resp.status_code == 201
    event_data = resp.json()["data"]
    slug = event_data["slug"]
    event_id = event_data["id"]

    with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as mock_pub:
        mock_pub.return_value = None
        await client.post(f"/api/v1/events/{event_id}/publish", cookies=host_cookies)

    resp = await client.post(f"/api/v1/events/{slug}/register", json={}, cookies=user_cookies)
    assert resp.status_code == 201
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_create_event_with_notify_on_register(client: AsyncClient, host_cookies):
    """Event can be created with notify_on_register flag."""
    resp = await client.post("/api/v1/events", json={
        "title": "Notify Test",
        "event_type": "online",
        "start_time": "2026-12-01T10:00:00+08:00",
        "notify_on_register": True,
    }, cookies=host_cookies)

    assert resp.status_code == 201
    data = resp.json()["data"]
    slug = data["slug"]

    resp = await client.get(f"/api/v1/events/{slug}")
    event = resp.json()["data"]
    assert event["notify_on_register"] is True


@pytest.mark.asyncio
async def test_host_notified_on_registration(client: AsyncClient, host_cookies, user_cookies):
    """When notify_on_register=True, host notification is called after registration."""
    resp = await client.post("/api/v1/events", json={
        "title": "Notify Flow Test",
        "event_type": "online",
        "start_time": "2030-06-01T10:00:00+08:00",
        "require_approval": False,
        "notify_on_register": True,
    }, cookies=host_cookies)

    event_data = resp.json()["data"]
    slug = event_data["slug"]
    event_id = event_data["id"]

    with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as mock_pub:
        mock_pub.return_value = None
        await client.post(f"/api/v1/events/{event_id}/publish", cookies=host_cookies)

    with patch("app.api.v1.events._notify_host_new_registration", new_callable=AsyncMock) as mock_notify:
        resp = await client.post(f"/api/v1/events/{slug}/register", json={}, cookies=user_cookies)
        assert resp.status_code == 201
        mock_notify.assert_called_once()
