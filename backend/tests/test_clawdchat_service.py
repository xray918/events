"""Tests for ClawdChat API service (Circle creation + posting)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.services.clawdchat import (
    create_circle, create_post, publish_event_to_clawdchat,
    update_post, sync_event_post_update, build_event_post_content,
)


@pytest.fixture
def mock_settings():
    with patch("app.services.clawdchat.settings") as mock:
        mock.events_bot_api_key = "test_key_12345"
        mock.clawdchat_api_base = "http://mock-clawdchat/api/v1"
        mock.frontend_url = "https://events.clawdchat.cn"
        yield mock


@pytest.mark.asyncio
async def test_create_circle_success(mock_settings):
    circle_id = str(uuid4())
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": circle_id, "name": "Test Circle", "slug": "test-circle"}

    with patch("app.services.clawdchat.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await create_circle("Test Circle", "A test circle")
        assert result is not None
        assert result["id"] == circle_id
        assert result["name"] == "Test Circle"


@pytest.mark.asyncio
async def test_create_circle_no_api_key():
    with patch("app.services.clawdchat.settings") as mock:
        mock.events_bot_api_key = ""
        result = await create_circle("Test Circle", api_key=None)
        assert result is None


@pytest.mark.asyncio
async def test_create_circle_failure(mock_settings):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.json.return_value = {"detail": "Circle name already exists"}
    mock_response.text = '{"detail": "Circle name already exists"}'

    with patch("app.services.clawdchat.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await create_circle("Duplicate Circle")
        assert result is None


@pytest.mark.asyncio
async def test_create_post_success(mock_settings):
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": str(uuid4()), "title": "Test Post"}

    with patch("app.services.clawdchat.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await create_post("test-circle", "Test Post", content="Hello!")
        assert result is not None
        assert result["title"] == "Test Post"


@pytest.mark.asyncio
async def test_create_post_no_api_key():
    with patch("app.services.clawdchat.settings") as mock:
        mock.events_bot_api_key = ""
        result = await create_post("test-circle", "Test Post", api_key=None)
        assert result is None


@pytest.mark.asyncio
async def test_create_post_with_custom_api_key(mock_settings):
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": str(uuid4()), "title": "Agent Post"}

    with patch("app.services.clawdchat.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await create_post("test-circle", "Agent Post", api_key="agent_key_custom")
        assert result is not None

        call_args = mock_client.request.call_args
        assert "agent_key_custom" in call_args.kwargs.get("headers", {}).get("Authorization", "")


@pytest.mark.asyncio
async def test_publish_event_to_clawdchat_full_flow(mock_settings):
    """publish_event_to_clawdchat should create a circle and then post, returning (circle_id, name, post_id)."""
    circle_id = str(uuid4())
    post_id = str(uuid4())

    circle_resp = MagicMock()
    circle_resp.status_code = 201
    circle_resp.json.return_value = {"id": circle_id, "name": "🎉 Hackathon", "slug": "hackathon"}

    post_resp = MagicMock()
    post_resp.status_code = 201
    post_resp.json.return_value = {"id": post_id, "title": "📢 活动发布：Hackathon"}

    with patch("app.services.clawdchat.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request.side_effect = [circle_resp, post_resp]
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await publish_event_to_clawdchat(
            event_title="Hackathon",
            event_description="A great hackathon event",
            event_slug="hackathon-2026",
        )
        assert result is not None
        assert len(result) == 3
        assert str(result[0]) == circle_id
        assert result[1] == "🎉 Hackathon"
        assert str(result[2]) == post_id
        assert mock_client.request.call_count == 2


@pytest.mark.asyncio
async def test_publish_event_to_clawdchat_circle_fails(mock_settings):
    """If circle creation fails, should return None without posting."""
    circle_resp = MagicMock()
    circle_resp.status_code = 500
    circle_resp.json.side_effect = Exception("Internal Server Error")
    circle_resp.text = "Internal Server Error"

    with patch("app.services.clawdchat.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request.return_value = circle_resp
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await publish_event_to_clawdchat(
            event_title="Broken Event",
            event_description="This will fail",
            event_slug="broken-event",
        )
        assert result is None
        assert mock_client.request.call_count == 2  # initial + retry with slug suffix


@pytest.mark.asyncio
async def test_publish_event_uses_agent_key_when_provided(mock_settings):
    """When agent_api_key is passed, it should be used instead of EventsBot key."""
    circle_id = str(uuid4())

    circle_resp = MagicMock()
    circle_resp.status_code = 201
    circle_resp.json.return_value = {"id": circle_id, "name": "🎉 Agent Event", "slug": "agent-event"}

    post_resp = MagicMock()
    post_resp.status_code = 201
    post_resp.json.return_value = {"id": str(uuid4()), "title": "📢 Agent Post"}

    with patch("app.services.clawdchat.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request.side_effect = [circle_resp, post_resp]
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await publish_event_to_clawdchat(
            event_title="Agent Event",
            event_description="An agent-created event",
            event_slug="agent-event-2026",
            agent_api_key="clawdchat_agent_custom_key",
        )
        assert result is not None

        for call in mock_client.request.call_args_list:
            auth_header = call.kwargs.get("headers", {}).get("Authorization", "")
            assert "clawdchat_agent_custom_key" in auth_header


# ---------------------------------------------------------------------------
# update_post tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_post_success(mock_settings):
    post_id = str(uuid4())
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": post_id, "title": "Updated Title", "content": "New content"}

    with patch("app.services.clawdchat.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await update_post(post_id, title="Updated Title", content="New content")
        assert result is not None
        assert result["title"] == "Updated Title"

        call_args = mock_client.request.call_args
        assert call_args.args[0] == "PATCH"
        assert post_id in call_args.args[1]


@pytest.mark.asyncio
async def test_update_post_no_api_key():
    with patch("app.services.clawdchat.settings") as mock:
        mock.events_bot_api_key = ""
        result = await update_post("some-id", title="test", api_key=None)
        assert result is None


@pytest.mark.asyncio
async def test_update_post_no_fields(mock_settings):
    """If both title and content are None, should return None without making a request."""
    result = await update_post("some-id")
    assert result is None


@pytest.mark.asyncio
async def test_update_post_failure(mock_settings):
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"detail": "帖子不存在"}
    mock_response.text = '{"detail": "帖子不存在"}'

    with patch("app.services.clawdchat.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await update_post("nonexistent-id", title="test")
        assert result is None


# ---------------------------------------------------------------------------
# sync_event_post_update tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_event_post_update_success(mock_settings):
    """sync_event_post_update should call update_post with built content."""
    post_id = str(uuid4())
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": post_id, "title": "updated"}

    with patch("app.services.clawdchat.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        ok = await sync_event_post_update(
            post_id=post_id,
            event_title="Updated Hackathon",
            event_description="New description",
            event_slug="hackathon-2026",
        )
        assert ok is True

        call_args = mock_client.request.call_args
        body = call_args.kwargs.get("json", {})
        assert "Updated Hackathon" in body["title"]
        assert "New description" in body["content"]


@pytest.mark.asyncio
async def test_sync_event_post_update_failure(mock_settings):
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.json.return_value = {"detail": "forbidden"}
    mock_response.text = '{"detail": "forbidden"}'

    with patch("app.services.clawdchat.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        ok = await sync_event_post_update(
            post_id=str(uuid4()),
            event_title="Test",
            event_description=None,
            event_slug="test",
        )
        assert ok is False


# ---------------------------------------------------------------------------
# build_event_post_content tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_event_post_content(mock_settings):
    title, content = build_event_post_content("Hackathon", "A fun event", "hack-2026")
    assert title == "📢 活动发布：Hackathon"
    assert "Hackathon" in content
    assert "A fun event" in content
    assert "hack-2026" in content
