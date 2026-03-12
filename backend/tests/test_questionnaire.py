"""Tests for custom questions / questionnaire feature."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


@pytest.fixture
async def auth_cookies(client: AsyncClient):
    """Login and return cookies."""
    mock_verify = AsyncMock(return_value=True)
    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800300001", "code": "123456",
        })
        return {"events_token": resp.cookies.get("events_token")}


@pytest.fixture
async def auth_cookies_2(client: AsyncClient):
    """Login as a second user."""
    mock_verify = AsyncMock(return_value=True)
    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800300002", "code": "654321",
        })
        return {"events_token": resp.cookies.get("events_token")}


@pytest.mark.asyncio
async def test_create_event_with_custom_questions(client: AsyncClient, auth_cookies):
    """Create event with custom questions attached."""
    resp = await client.post("/api/v1/events", json={
        "title": "Questionnaire Test Event",
        "event_type": "in_person",
        "start_time": "2026-12-01T10:00:00+08:00",
        "custom_questions": [
            {"question_text": "你的公司？", "question_type": "text", "is_required": True},
            {"question_text": "来源", "question_type": "select", "options": ["朋友", "搜索", "其他"], "is_required": False},
            {"question_text": "兴趣", "question_type": "multiselect", "options": ["AI", "Web3", "IoT"], "is_required": True},
        ],
    }, cookies=auth_cookies)

    assert resp.status_code == 201
    data = resp.json()["data"]
    slug = data["slug"]

    resp = await client.get(f"/api/v1/events/{slug}")
    event = resp.json()["data"]
    assert event["custom_questions"] is not None
    assert len(event["custom_questions"]) == 3
    assert event["custom_questions"][0]["question_text"] == "你的公司？"
    assert event["custom_questions"][0]["is_required"] is True
    assert event["custom_questions"][1]["options"] == ["朋友", "搜索", "其他"]
    assert event["custom_questions"][2]["question_type"] == "multiselect"


@pytest.mark.asyncio
async def test_register_missing_required_answer(client: AsyncClient, auth_cookies, auth_cookies_2):
    """Registration fails if required questions are unanswered."""
    resp = await client.post("/api/v1/events", json={
        "title": "Required Q Test",
        "event_type": "online",
        "start_time": "2026-12-15T10:00:00+08:00",
        "custom_questions": [
            {"question_text": "必填问题", "question_type": "text", "is_required": True},
        ],
    }, cookies=auth_cookies)

    assert resp.status_code == 201
    event_data = resp.json()["data"]
    slug = event_data["slug"]
    event_id = event_data["id"]

    with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as mock_pub:
        mock_pub.return_value = None
        await client.post(f"/api/v1/events/{event_id}/publish", cookies=auth_cookies)

    resp = await client.post(f"/api/v1/events/{slug}/register", json={}, cookies=auth_cookies_2)
    assert resp.status_code == 422
    assert "必填问题" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_register_with_answers(client: AsyncClient, auth_cookies, auth_cookies_2):
    """Registration succeeds with all required answers provided."""
    resp = await client.post("/api/v1/events", json={
        "title": "Full Q Test",
        "event_type": "online",
        "start_time": "2026-12-20T10:00:00+08:00",
        "require_approval": False,
        "custom_questions": [
            {"question_text": "公司", "question_type": "text", "is_required": True},
            {"question_text": "来源", "question_type": "select", "options": ["朋友", "搜索"], "is_required": False},
        ],
    }, cookies=auth_cookies)

    assert resp.status_code == 201
    event_data = resp.json()["data"]
    slug = event_data["slug"]
    event_id = event_data["id"]

    resp = await client.get(f"/api/v1/events/{slug}")
    questions = resp.json()["data"]["custom_questions"]
    q_company_id = questions[0]["id"]
    q_source_id = questions[1]["id"]

    with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as mock_pub:
        mock_pub.return_value = None
        await client.post(f"/api/v1/events/{event_id}/publish", cookies=auth_cookies)

    resp = await client.post(f"/api/v1/events/{slug}/register", json={
        "custom_answers": {
            q_company_id: "虾聊科技",
            q_source_id: "朋友",
        },
    }, cookies=auth_cookies_2)
    assert resp.status_code == 201
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_answer_stats_api(client: AsyncClient, auth_cookies, auth_cookies_2):
    """Answer statistics API returns correct counts."""
    resp = await client.post("/api/v1/events", json={
        "title": "Stats Test",
        "event_type": "online",
        "start_time": "2026-12-25T10:00:00+08:00",
        "require_approval": False,
        "custom_questions": [
            {"question_text": "来源", "question_type": "select", "options": ["A", "B", "C"], "is_required": False},
        ],
    }, cookies=auth_cookies)

    event_data = resp.json()["data"]
    slug = event_data["slug"]
    event_id = event_data["id"]

    resp = await client.get(f"/api/v1/events/{slug}")
    q_id = resp.json()["data"]["custom_questions"][0]["id"]

    with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as mock_pub:
        mock_pub.return_value = None
        await client.post(f"/api/v1/events/{event_id}/publish", cookies=auth_cookies)

    await client.post(f"/api/v1/events/{slug}/register", json={
        "custom_answers": {q_id: "A"},
    }, cookies=auth_cookies_2)

    resp = await client.get(f"/api/v1/host/events/{event_id}/answer-stats", cookies=auth_cookies)
    assert resp.status_code == 200
    stats_data = resp.json()["data"]
    assert len(stats_data) == 1
    assert stats_data[0]["question_text"] == "来源"
    assert stats_data[0]["stats"]["A"] == 1
    assert stats_data[0]["total_answers"] == 1


@pytest.mark.asyncio
async def test_filter_by_answer_api(client: AsyncClient, auth_cookies, auth_cookies_2):
    """Filter registrations by answer value."""
    resp = await client.post("/api/v1/events", json={
        "title": "Filter Test",
        "event_type": "online",
        "start_time": "2026-12-28T10:00:00+08:00",
        "require_approval": False,
        "custom_questions": [
            {"question_text": "城市", "question_type": "text", "is_required": False},
        ],
    }, cookies=auth_cookies)

    event_data = resp.json()["data"]
    slug = event_data["slug"]
    event_id = event_data["id"]

    resp = await client.get(f"/api/v1/events/{slug}")
    q_id = resp.json()["data"]["custom_questions"][0]["id"]

    with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as mock_pub:
        mock_pub.return_value = None
        await client.post(f"/api/v1/events/{event_id}/publish", cookies=auth_cookies)

    await client.post(f"/api/v1/events/{slug}/register", json={
        "custom_answers": {q_id: "上海"},
    }, cookies=auth_cookies_2)

    resp = await client.get(
        f"/api/v1/host/events/{event_id}/registrations/filter-by-answer?question_id={q_id}&answer_value=上海",
        cookies=auth_cookies,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["data"][0]["custom_answers"][q_id] == "上海"

    resp = await client.get(
        f"/api/v1/host/events/{event_id}/registrations/filter-by-answer?question_id={q_id}&answer_value=北京",
        cookies=auth_cookies,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
