"""Tests for new features: upload, AI description, poster, address privacy."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Upload API
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_image_unauthenticated(client: AsyncClient):
    resp = await client.post("/api/v1/upload/image")
    assert resp.status_code in (401, 422)


@pytest.mark.asyncio
async def test_upload_image_no_file(client: AsyncClient):
    mock_verify = AsyncMock(return_value=True)
    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800200001", "code": "123456",
        })
        token = resp.cookies.get("events_token")

        resp = await client.post("/api/v1/upload/image", cookies={"events_token": token})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# AI Description
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_description_unauthenticated(client: AsyncClient):
    resp = await client.post("/api/v1/events/generate-description", json={
        "title": "Test Event"
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_generate_description_success(client: AsyncClient):
    mock_verify = AsyncMock(return_value=True)
    mock_llm = AsyncMock(return_value="## Test Event\n\nA great event!")

    with patch("app.api.v1.auth.verify_code", mock_verify), \
         patch("app.api.v1.events.generate_event_description", mock_llm):

        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800200002", "code": "123456",
        })
        token = resp.cookies.get("events_token")

        resp = await client.post("/api/v1/events/generate-description", json={
            "title": "AI 创新峰会",
            "event_type": "hybrid",
            "location": "上海",
        }, cookies={"events_token": token})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "## Test Event" in data["description"]
        mock_llm.assert_called_once()


# ---------------------------------------------------------------------------
# Poster
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_poster_nonexistent_event(client: AsyncClient):
    resp = await client.get("/api/v1/events/nonexistent-poster-test/poster")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_poster_returns_png(client: AsyncClient):
    """Create event and get its poster (should return PNG image)."""
    mock_verify = AsyncMock(return_value=True)

    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800200003", "code": "123456",
        })
        token = resp.cookies.get("events_token")
        cookies = {"events_token": token}

        resp = await client.post("/api/v1/events", json={
            "title": "Poster Test Event",
            "description": "Testing poster generation",
            "event_type": "online",
            "start_time": "2026-10-01T10:00:00+08:00",
        }, cookies=cookies)
        assert resp.status_code == 201
        slug = resp.json()["data"]["slug"]

        with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as mock_pub:
            mock_pub.return_value = None
            resp = await client.post(f"/api/v1/events/{resp.json()['data']['id']}/publish", cookies=cookies)
            assert resp.status_code == 200

        resp = await client.get(f"/api/v1/events/{slug}/poster")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert len(resp.content) > 1000


# ---------------------------------------------------------------------------
# Address Privacy
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_address_masked_for_require_approval_event(client: AsyncClient):
    """Events with require_approval should mask address for unauthenticated users."""
    mock_verify = AsyncMock(return_value=True)

    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800200004", "code": "123456",
        })
        token = resp.cookies.get("events_token")
        cookies = {"events_token": token}

        resp = await client.post("/api/v1/events", json={
            "title": "Private Address Event",
            "event_type": "in_person",
            "location_name": "虾聊总部",
            "location_address": "上海市浦东新区张江高科技园区碧波路690号5栋3楼",
            "start_time": "2026-11-01T10:00:00+08:00",
            "require_approval": True,
        }, cookies=cookies)
        assert resp.status_code == 201
        slug = resp.json()["data"]["slug"]
        event_id = resp.json()["data"]["id"]

        with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as mock_pub:
            mock_pub.return_value = None
            await client.post(f"/api/v1/events/{event_id}/publish", cookies=cookies)

        # Login as a different user (not the host)
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800200099", "code": "999999",
        })
        other_token = resp.cookies.get("events_token")

        resp = await client.get(f"/api/v1/events/{slug}", cookies={"events_token": other_token})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["address_masked"] is True
        assert "5栋3楼" not in data["location_address"]

        # Host should see full address
        resp = await client.get(f"/api/v1/events/{slug}", cookies=cookies)
        data = resp.json()["data"]
        assert data["address_masked"] is False
        assert "5栋3楼" in data["location_address"]


@pytest.mark.asyncio
async def test_address_not_masked_when_no_approval(client: AsyncClient):
    """Events without require_approval should show full address."""
    mock_verify = AsyncMock(return_value=True)

    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800200005", "code": "123456",
        })
        token = resp.cookies.get("events_token")
        cookies = {"events_token": token}

        resp = await client.post("/api/v1/events", json={
            "title": "Public Address Event",
            "event_type": "in_person",
            "location_name": "虾聊",
            "location_address": "上海市浦东新区张江高科技园区690号",
            "start_time": "2026-12-01T10:00:00+08:00",
            "require_approval": False,
        }, cookies=cookies)
        assert resp.status_code == 201
        slug = resp.json()["data"]["slug"]

        resp = await client.get(f"/api/v1/events/{slug}")
        data = resp.json()["data"]
        assert data["address_masked"] is False
        assert "690号" in data["location_address"]


# ---------------------------------------------------------------------------
# LLM Service Unit Test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_llm_service_with_mock():
    from app.services.llm import generate_event_description

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "## AI Generated\n\nHello!"}}]
    }

    with patch("app.services.llm.settings") as mock_settings, \
         patch("app.services.llm.httpx.AsyncClient") as MockClient:
        mock_settings.openrouter_api_key = "test-key"
        mock_settings.openrouter_api_base = "http://mock-api"
        mock_settings.openrouter_model = "test-model"

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await generate_event_description("Test Event")
        assert result is not None
        assert "AI Generated" in result


@pytest.mark.asyncio
async def test_llm_service_no_key():
    from app.services.llm import generate_event_description

    with patch("app.services.llm.settings") as mock_settings:
        mock_settings.openrouter_api_key = ""
        result = await generate_event_description("Test Event")
        assert result is None
