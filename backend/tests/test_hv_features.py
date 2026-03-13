"""Tests for high-value features: clone, co-hosts, attendees preview, feedback, registration notification."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


async def _login_and_create_event(client: AsyncClient, phone: str = "13800300001"):
    """Helper: login, create event, return (cookies, event_data)."""
    mock_verify = AsyncMock(return_value=True)
    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": phone, "code": "123456",
        })
        token = resp.cookies.get("events_token")
        cookies = {"events_token": token}

        resp = await client.post("/api/v1/events", json={
            "title": "HV Test Event",
            "description": "Testing high-value features",
            "event_type": "online",
            "start_time": "2026-10-01T10:00:00+08:00",
            "capacity": 100,
        }, cookies=cookies)
        assert resp.status_code == 201
        return cookies, resp.json()["data"]


async def _publish_event(client: AsyncClient, event_id: str, cookies: dict):
    with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as mock_pub:
        mock_pub.return_value = None
        resp = await client.post(f"/api/v1/events/{event_id}/publish", cookies=cookies)
        assert resp.status_code == 200
        return resp.json()


# ---------------------------------------------------------------------------
# Clone Event
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_clone_event(client: AsyncClient):
    cookies, event = await _login_and_create_event(client, "13800300010")
    event_id = event["id"]

    resp = await client.post(f"/api/v1/events/{event_id}/clone", cookies=cookies)
    assert resp.status_code == 201
    clone = resp.json()["data"]
    assert clone["title"] == event["title"]
    assert clone["slug"] != event["slug"]
    assert clone["status"] == "draft"
    assert clone["id"] != event["id"]


@pytest.mark.asyncio
async def test_clone_event_unauthorized(client: AsyncClient):
    cookies1, event = await _login_and_create_event(client, "13800300011")
    event_id = event["id"]

    mock_verify = AsyncMock(return_value=True)
    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800300012", "code": "123456",
        })
        other_cookies = {"events_token": resp.cookies.get("events_token")}

    resp = await client.post(f"/api/v1/events/{event_id}/clone", cookies=other_cookies)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_clone_unauthenticated(client: AsyncClient):
    resp = await client.post("/api/v1/events/00000000-0000-0000-0000-000000000000/clone")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Co-Hosts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cohost_management(client: AsyncClient):
    cookies, event = await _login_and_create_event(client, "13800300020")
    event_id = event["id"]

    mock_verify = AsyncMock(return_value=True)
    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800300021", "code": "123456",
        })
        cohost_token = resp.cookies.get("events_token")  # noqa: F841

    resp = await client.post(f"/api/v1/host/events/{event_id}/cohosts", json={
        "phone": "13800300021",
    }, cookies=cookies)
    assert resp.status_code == 200
    cohost = resp.json()["data"]
    assert cohost["nickname"] is not None

    resp = await client.get(f"/api/v1/host/events/{event_id}/cohosts", cookies=cookies)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1

    resp = await client.delete(
        f"/api/v1/host/events/{event_id}/cohosts/{cohost['id']}",
        cookies=cookies,
    )
    assert resp.status_code == 200

    resp = await client.get(f"/api/v1/host/events/{event_id}/cohosts", cookies=cookies)
    assert len(resp.json()["data"]) == 0


@pytest.mark.asyncio
async def test_cohost_duplicate(client: AsyncClient):
    cookies, event = await _login_and_create_event(client, "13800300022")
    event_id = event["id"]

    mock_verify = AsyncMock(return_value=True)
    with patch("app.api.v1.auth.verify_code", mock_verify):
        await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800300023", "code": "123456",
        })

    resp = await client.post(f"/api/v1/host/events/{event_id}/cohosts", json={
        "phone": "13800300023",
    }, cookies=cookies)
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/host/events/{event_id}/cohosts", json={
        "phone": "13800300023",
    }, cookies=cookies)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_cohost_nonexistent_user(client: AsyncClient):
    cookies, event = await _login_and_create_event(client, "13800300024")
    event_id = event["id"]

    resp = await client.post(f"/api/v1/host/events/{event_id}/cohosts", json={
        "phone": "19999999999",
    }, cookies=cookies)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Attendees Preview
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_attendees_preview_in_event_detail(client: AsyncClient):
    cookies, event = await _login_and_create_event(client, "13800300030")
    event_id = event["id"]
    slug = event["slug"]

    await _publish_event(client, event_id, cookies)

    mock_verify = AsyncMock(return_value=True)
    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800300031", "code": "123456",
        })
        reg_cookies = {"events_token": resp.cookies.get("events_token")}

    with patch("app.api.v1.events._notify_registrant_confirmation", new_callable=AsyncMock):
        resp = await client.post(f"/api/v1/events/{slug}/register", cookies=reg_cookies)
        assert resp.status_code == 201

    resp = await client.get(f"/api/v1/events/{slug}")
    data = resp.json()["data"]
    assert "attendees_preview" in data
    assert data["registration_count"] >= 1


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_feedback_requires_completed(client: AsyncClient):
    cookies, event = await _login_and_create_event(client, "13800300040")
    event_id = event["id"]
    slug = event["slug"]

    await _publish_event(client, event_id, cookies)

    resp = await client.post(f"/api/v1/events/{slug}/feedback", json={
        "rating": 5, "comment": "Great!",
    }, cookies=cookies)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_feedback_get_empty(client: AsyncClient):
    cookies, event = await _login_and_create_event(client, "13800300041")
    slug = event["slug"]

    resp = await client.get(f"/api/v1/events/{slug}/feedback")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["count"] == 0
    assert data["avg_rating"] == 0


@pytest.mark.asyncio
async def test_feedback_invalid_rating(client: AsyncClient):
    cookies, event = await _login_and_create_event(client, "13800300042")
    slug = event["slug"]

    resp = await client.post(f"/api/v1/events/{slug}/feedback", json={
        "rating": 0,
    }, cookies=cookies)
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_feedback_unauthenticated(client: AsyncClient):
    resp = await client.post("/api/v1/events/some-slug/feedback", json={
        "rating": 5,
    })
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Registration Confirmation Notification
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_registration_sends_confirmation(client: AsyncClient):
    cookies, event = await _login_and_create_event(client, "13800300050")
    event_id = event["id"]
    slug = event["slug"]

    await _publish_event(client, event_id, cookies)

    mock_verify = AsyncMock(return_value=True)
    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800300051", "code": "123456",
        })
        reg_cookies = {"events_token": resp.cookies.get("events_token")}

    with patch("app.api.v1.events._notify_registrant_confirmation", new_callable=AsyncMock) as mock_notify:
        resp = await client.post(f"/api/v1/events/{slug}/register", cookies=reg_cookies)
        assert resp.status_code == 201
        mock_notify.assert_called_once()


# ---------------------------------------------------------------------------
# Cohosts in event detail
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cohosts_in_event_detail(client: AsyncClient):
    cookies, event = await _login_and_create_event(client, "13800300060")
    event_id = event["id"]
    slug = event["slug"]

    mock_verify = AsyncMock(return_value=True)
    with patch("app.api.v1.auth.verify_code", mock_verify):
        await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800300061", "code": "123456",
        })

    await client.post(f"/api/v1/host/events/{event_id}/cohosts", json={
        "phone": "13800300061",
    }, cookies=cookies)

    await _publish_event(client, event_id, cookies)

    resp = await client.get(f"/api/v1/events/{slug}")
    data = resp.json()["data"]
    assert "cohosts" in data
    assert isinstance(data["cohosts"], list)
    assert len(data["cohosts"]) >= 1
