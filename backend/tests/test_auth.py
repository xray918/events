"""Auth API tests — phone login, verification flow, session, Google OAuth."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_send_code_invalid_phone(client: AsyncClient):
    resp = await client.post("/api/v1/auth/phone/send-code", json={"phone": "12345"})
    assert resp.status_code == 400
    assert "有效的手机号" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_send_code_missing_phone(client: AsyncClient):
    resp = await client.post("/api/v1/auth/phone/send-code", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_invalid_phone(client: AsyncClient):
    resp = await client.post("/api/v1/auth/phone/login", json={"phone": "12345", "code": "123456"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login_missing_code(client: AsyncClient):
    resp = await client.post("/api/v1/auth/phone/login", json={"phone": "13900139000"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_wrong_code(client: AsyncClient):
    """Valid phone but wrong verification code should fail."""
    mock_verify = AsyncMock(return_value=False)
    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={"phone": "13900139000", "code": "000000"})
        assert resp.status_code == 400
        assert "验证码" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_always_succeeds(client: AsyncClient):
    resp = await client.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_google_start_redirects(client: AsyncClient):
    resp = await client.get("/api/v1/auth/google/start", follow_redirects=False)
    assert resp.status_code in (302, 307)
    location = resp.headers.get("location", "")
    assert "accounts.google.com" in location or "google" in location.lower()


@pytest.mark.asyncio
async def test_google_callback_missing_code(client: AsyncClient):
    resp = await client.get("/api/v1/auth/google/callback?code=")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_send_code_and_login_flow(client: AsyncClient):
    """Full SMS flow with mocked SMS sending and Redis."""
    mock_sms = AsyncMock(return_value={"mock": True, "success": True})
    mock_can_send = AsyncMock(return_value=True)

    with patch("app.api.v1.auth.send_verification_code", mock_sms), \
         patch("app.api.v1.auth.can_send", mock_can_send), \
         patch("app.api.v1.auth.store_code", new_callable=AsyncMock) as mock_store, \
         patch("app.api.v1.auth.verify_code", new_callable=AsyncMock) as mock_verify:

        mock_verify.return_value = True

        resp = await client.post("/api/v1/auth/phone/send-code", json={"phone": "13800138000"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        mock_store.assert_called_once()

        resp = await client.post("/api/v1/auth/phone/login", json={"phone": "13800138000", "code": "123456"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "user" in data

        token = resp.cookies.get("events_token")
        assert token is not None

        resp = await client.get("/api/v1/auth/me", cookies={"events_token": token})
        assert resp.status_code == 200
        me = resp.json()
        assert me["success"] is True
        assert me["data"]["phone"] == "13800138000"


@pytest.mark.asyncio
async def test_send_code_rate_limited(client: AsyncClient):
    """Should return 429 when sending too frequently."""
    mock_can_send = AsyncMock(return_value=False)

    with patch("app.api.v1.auth.can_send", mock_can_send):
        resp = await client.post("/api/v1/auth/phone/send-code", json={"phone": "13900139001"})
        assert resp.status_code == 429
        assert "频繁" in resp.json()["detail"]
