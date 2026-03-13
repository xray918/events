"""Tests for the event theme system — preset selection, persistence, and retrieval."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_event_with_theme(client: AsyncClient):
    """Theme preset is saved during event creation and returned in detail."""
    mock_verify = AsyncMock(return_value=True)
    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800400001", "code": "123456",
        })
        cookies = {"events_token": resp.cookies.get("events_token")}

        resp = await client.post("/api/v1/events", json={
            "title": "Theme Test Event",
            "event_type": "online",
            "start_time": "2026-10-01T10:00:00+08:00",
            "theme": {"preset": "aurora"},
        }, cookies=cookies)
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["theme"]["preset"] == "aurora"
        slug = data["slug"]

        resp = await client.get(f"/api/v1/events/{slug}")
        assert resp.status_code == 200
        detail = resp.json()["data"]
        assert detail["theme"]["preset"] == "aurora"


@pytest.mark.asyncio
async def test_update_event_theme(client: AsyncClient):
    """Theme preset can be changed via PUT."""
    mock_verify = AsyncMock(return_value=True)
    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800400002", "code": "123456",
        })
        cookies = {"events_token": resp.cookies.get("events_token")}

        resp = await client.post("/api/v1/events", json={
            "title": "Theme Update Test",
            "event_type": "online",
            "start_time": "2026-10-01T10:00:00+08:00",
            "theme": {"preset": "ocean"},
        }, cookies=cookies)
        event_id = resp.json()["data"]["id"]
        slug = resp.json()["data"]["slug"]

        resp = await client.put(f"/api/v1/events/{event_id}", json={
            "title": "Theme Update Test",
            "event_type": "online",
            "start_time": "2026-10-01T10:00:00+08:00",
            "theme": {"preset": "neon"},
        }, cookies=cookies)
        assert resp.status_code == 200
        assert resp.json()["data"]["theme"]["preset"] == "neon"

        resp = await client.get(f"/api/v1/events/{slug}")
        assert resp.json()["data"]["theme"]["preset"] == "neon"


@pytest.mark.asyncio
async def test_create_event_empty_theme(client: AsyncClient):
    """Creating without theme or with empty theme object is fine."""
    mock_verify = AsyncMock(return_value=True)
    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800400003", "code": "123456",
        })
        cookies = {"events_token": resp.cookies.get("events_token")}

        resp = await client.post("/api/v1/events", json={
            "title": "No Theme Event",
            "event_type": "online",
            "start_time": "2026-10-01T10:00:00+08:00",
        }, cookies=cookies)
        assert resp.status_code == 201
        theme = resp.json()["data"]["theme"]
        assert theme == {} or theme is None or theme.get("preset") is None


@pytest.mark.asyncio
async def test_clone_preserves_theme(client: AsyncClient):
    """Cloned event should carry over the theme preset."""
    mock_verify = AsyncMock(return_value=True)
    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800400004", "code": "123456",
        })
        cookies = {"events_token": resp.cookies.get("events_token")}

        resp = await client.post("/api/v1/events", json={
            "title": "Clone Theme Source",
            "event_type": "online",
            "start_time": "2026-10-01T10:00:00+08:00",
            "theme": {"preset": "cosmic"},
        }, cookies=cookies)
        event_id = resp.json()["data"]["id"]

        resp = await client.post(f"/api/v1/events/{event_id}/clone", cookies=cookies)
        assert resp.status_code == 201
        clone_theme = resp.json()["data"]["theme"]
        assert clone_theme.get("preset") == "cosmic"
