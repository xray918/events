"""Events API tests — CRUD, dual auth, Circle integration."""

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from app.api.v1.events import _mask_address


# ---------------------------------------------------------------------------
# Address masking unit tests
# ---------------------------------------------------------------------------

class TestMaskAddress:
    """Verify _mask_address returns truncated address for detailed inputs
    and unchanged address for short/generic inputs."""

    def test_masks_street_number(self):
        result = _mask_address("上海市浦东新区张杨路500号5楼")
        assert result != "上海市浦东新区张杨路500号5楼"
        assert "附近" in result

    def test_keeps_short_address_unchanged(self):
        assert _mask_address("浦东新区") == "浦东新区"

    def test_keeps_empty_unchanged(self):
        assert _mask_address("") == ""

    def test_masks_building_unit(self):
        result = _mask_address("北京市海淀区中关村大街1号创业大厦3栋")
        assert result != "北京市海淀区中关村大街1号创业大厦3栋"

    def test_truncates_long_address_without_markers(self):
        long_addr = "这是一个没有任何标记的很长的地址描述文本超过十五个字符"
        result = _mask_address(long_addr)
        assert result.endswith("...")
        assert len(result) < len(long_addr)


# ---------------------------------------------------------------------------
# Unauthenticated access
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_events_returns_success(client: AsyncClient):
    resp = await client.get("/api/v1/events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert "total" in data


@pytest.mark.asyncio
async def test_list_events_with_pagination(client: AsyncClient):
    resp = await client.get("/api/v1/events?skip=0&limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_nonexistent_event(client: AsyncClient):
    resp = await client.get("/api/v1/events/nonexistent-slug-xyz-abc")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_event_unauthenticated(client: AsyncClient):
    resp = await client.post("/api/v1/events", json={
        "title": "Test Event",
        "start_time": "2026-05-01T09:00:00+08:00",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_unauthenticated(client: AsyncClient):
    resp = await client.post("/api/v1/events/some-slug/register")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_my_registrations_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/registrations/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_publish_event_unauthenticated(client: AsyncClient):
    resp = await client.post("/api/v1/events/some-fake-id/publish")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_cancel_event_unauthenticated(client: AsyncClient):
    resp = await client.post("/api/v1/events/some-fake-id/cancel")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Authenticated full flow (with mocked auth)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_event_lifecycle(client: AsyncClient):
    """Login → Create → Publish (with Circle) → Register → Cancel."""
    mock_verify = AsyncMock(return_value=True)
    mock_sms = AsyncMock(return_value={"mock": True})
    mock_can_send = AsyncMock(return_value=True)
    mock_store = AsyncMock()

    with patch("app.api.v1.auth.verify_code", mock_verify), \
         patch("app.api.v1.auth.send_verification_code", mock_sms), \
         patch("app.api.v1.auth.can_send", mock_can_send), \
         patch("app.api.v1.auth.store_code", mock_store):

        # 1. Login
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800000001",
            "code": "123456",
        })
        assert resp.status_code == 200
        token = resp.cookies.get("events_token")
        assert token is not None
        cookies = {"events_token": token}

        # 2. Create event (draft)
        resp = await client.post("/api/v1/events", json={
            "title": "Test Lifecycle Event",
            "description": "Full lifecycle test",
            "event_type": "online",
            "start_time": "2026-07-01T10:00:00+08:00",
            "capacity": 100,
            "require_approval": False,
        }, cookies=cookies)
        assert resp.status_code == 201
        event_data = resp.json()
        assert event_data["success"] is True
        event_id = event_data["data"]["id"]
        slug = event_data["data"]["slug"]

        # 3. Verify it appears in event list
        resp = await client.get("/api/v1/events")
        assert resp.status_code == 200

        # 4. Get event detail
        resp = await client.get(f"/api/v1/events/{slug}")
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Test Lifecycle Event"

        # 5. Publish (mock ClawdChat Circle creation)
        with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as mock_publish:
            from uuid import uuid4
            mock_circle_id = uuid4()
            mock_publish.return_value = mock_circle_id

            resp = await client.post(f"/api/v1/events/{event_id}/publish", cookies=cookies)
            assert resp.status_code == 200
            assert resp.json()["success"] is True
            assert resp.json()["data"]["circle_id"] == str(mock_circle_id)
            mock_publish.assert_called_once()

        # 6. Register
        resp = await client.post(f"/api/v1/events/{slug}/register", json={
            "phone": "13800000001",
        }, cookies=cookies)
        assert resp.status_code == 201
        reg = resp.json()
        assert reg["success"] is True

        # 7. Check registration
        resp = await client.get(f"/api/v1/events/{slug}/registration", cookies=cookies)
        assert resp.status_code == 200
        assert resp.json()["registered"] is True

        # 8. My registrations
        resp = await client.get("/api/v1/registrations/me", cookies=cookies)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

        # 9. Cancel registration
        resp = await client.delete(f"/api/v1/events/{slug}/registration", cookies=cookies)
        assert resp.status_code == 200

        # 10. Cancel event
        resp = await client.post(f"/api/v1/events/{event_id}/cancel", cookies=cookies)
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_publish_nonexistent_event(client: AsyncClient):
    """Publishing a nonexistent event should 404."""
    mock_verify = AsyncMock(return_value=True)

    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800000002",
            "code": "123456",
        })
        token = resp.cookies.get("events_token")

        resp = await client.post(
            "/api/v1/events/00000000-0000-0000-0000-000000000000/publish",
            cookies={"events_token": token},
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_event_unauthorized(client: AsyncClient):
    """Cannot update an event you don't own."""
    mock_verify = AsyncMock(return_value=True)

    with patch("app.api.v1.auth.verify_code", mock_verify):
        # Create event as user A
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800000003",
            "code": "123456",
        })
        token_a = resp.cookies.get("events_token")

        resp = await client.post("/api/v1/events", json={
            "title": "Owner A Event",
            "start_time": "2026-08-01T10:00:00+08:00",
        }, cookies={"events_token": token_a})
        event_id = resp.json()["data"]["id"]

        # Login as user B
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800000004",
            "code": "654321",
        })
        token_b = resp.cookies.get("events_token")

        # Try to update as user B
        resp = await client.put(f"/api/v1/events/{event_id}", json={
            "title": "Hijacked Event",
        }, cookies={"events_token": token_b})
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_address_masked_only_when_actually_masked(client: AsyncClient):
    """address_masked should be True only when the address was shortened by masking."""
    mock_verify = AsyncMock(return_value=True)

    with patch("app.api.v1.auth.verify_code", mock_verify):
        # Host creates events
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800000010",
            "code": "123456",
        })
        host_cookies = {"events_token": resp.cookies.get("events_token")}

        resp = await client.post("/api/v1/events", json={
            "title": "Address Masking Test Detailed",
            "start_time": "2026-10-01T10:00:00+08:00",
            "event_type": "in_person",
            "location_name": "测试场地",
            "location_address": "上海市浦东新区张杨路500号5楼",
            "require_approval": True,
        }, cookies=host_cookies)
        assert resp.status_code == 201
        slug_detailed = resp.json()["data"]["slug"]

        resp = await client.post("/api/v1/events", json={
            "title": "Address Masking Test Short",
            "start_time": "2026-10-01T10:00:00+08:00",
            "event_type": "in_person",
            "location_name": "测试场地",
            "location_address": "浦东新区",
            "require_approval": True,
        }, cookies=host_cookies)
        assert resp.status_code == 201
        slug_short = resp.json()["data"]["slug"]

        # Login as a different user (not the host, not approved)
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800000099",
            "code": "123456",
        })
        visitor_cookies = {"events_token": resp.cookies.get("events_token")}

        # Visitor sees detailed address masked
        resp = await client.get(f"/api/v1/events/{slug_detailed}", cookies=visitor_cookies)
        data = resp.json()["data"]
        assert data["address_masked"] is True
        assert "500号" not in (data["location_address"] or "")

        # Visitor sees short address NOT marked as masked
        resp = await client.get(f"/api/v1/events/{slug_short}", cookies=visitor_cookies)
        data = resp.json()["data"]
        assert data["address_masked"] is False
        assert data["location_address"] == "浦东新区"


@pytest.mark.asyncio
async def test_publish_already_published(client: AsyncClient):
    """Cannot publish an event that's already published."""
    mock_verify = AsyncMock(return_value=True)

    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800000005",
            "code": "123456",
        })
        token = resp.cookies.get("events_token")
        cookies = {"events_token": token}

        resp = await client.post("/api/v1/events", json={
            "title": "Double Publish Test",
            "start_time": "2026-09-01T10:00:00+08:00",
        }, cookies=cookies)
        event_id = resp.json()["data"]["id"]

        with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as mock_pub:
            mock_pub.return_value = None
            resp = await client.post(f"/api/v1/events/{event_id}/publish", cookies=cookies)
            assert resp.status_code == 200

            resp = await client.post(f"/api/v1/events/{event_id}/publish", cookies=cookies)
            assert resp.status_code == 400
            assert "不能发布" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Check-in & allow_self_checkin tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_checkin_flow_with_self_checkin_control(client: AsyncClient):
    """Create event with allow_self_checkin=False → register → self-checkin rejected → host scan OK."""
    mock_verify = AsyncMock(return_value=True)

    with patch("app.api.v1.auth.verify_code", mock_verify):
        # Host login
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800000020",
            "code": "123456",
        })
        host_cookies = {"events_token": resp.cookies.get("events_token")}

        # Create event: self-checkin disabled
        resp = await client.post("/api/v1/events", json={
            "title": "No Self Checkin Event",
            "start_time": "2026-11-01T10:00:00+08:00",
            "allow_self_checkin": False,
        }, cookies=host_cookies)
        assert resp.status_code == 201
        event_data = resp.json()["data"]
        event_id = event_data["id"]
        slug = event_data["slug"]
        assert event_data["allow_self_checkin"] is False

        # Publish
        with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as m:
            m.return_value = None
            resp = await client.post(f"/api/v1/events/{event_id}/publish", cookies=host_cookies)
            assert resp.status_code == 200

        # Register
        resp = await client.post(f"/api/v1/events/{slug}/register", json={
            "phone": "13800000020",
        }, cookies=host_cookies)
        assert resp.status_code == 201
        qr_token = resp.json()["data"]["qr_code_token"]

        # Verify endpoint returns allow_self_checkin
        resp = await client.get(f"/api/v1/checkin/verify/{qr_token}")
        assert resp.status_code == 200
        assert resp.json()["data"]["allow_self_checkin"] is False

        # Self-checkin should be rejected
        resp = await client.post(f"/api/v1/checkin/self/{qr_token}")
        assert resp.status_code == 403
        assert "不允许自助签到" in resp.json()["detail"]

        # Host scan should work
        resp = await client.post("/api/v1/checkin/scan", json={
            "qr_token": qr_token,
        }, cookies=host_cookies)
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert "签到成功" in resp.json()["data"]["message"]


@pytest.mark.asyncio
async def test_self_checkin_allowed_by_default(client: AsyncClient):
    """Default event (allow_self_checkin=True) allows self check-in."""
    mock_verify = AsyncMock(return_value=True)

    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800000021",
            "code": "123456",
        })
        host_cookies = {"events_token": resp.cookies.get("events_token")}

        resp = await client.post("/api/v1/events", json={
            "title": "Default Self Checkin Event",
            "start_time": "2026-11-02T10:00:00+08:00",
        }, cookies=host_cookies)
        assert resp.status_code == 201
        assert resp.json()["data"]["allow_self_checkin"] is True
        event_id = resp.json()["data"]["id"]
        slug = resp.json()["data"]["slug"]

        with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as m:
            m.return_value = None
            await client.post(f"/api/v1/events/{event_id}/publish", cookies=host_cookies)

        resp = await client.post(f"/api/v1/events/{slug}/register", json={
            "phone": "13800000021",
        }, cookies=host_cookies)
        assert resp.status_code == 201
        qr_token = resp.json()["data"]["qr_code_token"]

        # Self-checkin should work
        resp = await client.post(f"/api/v1/checkin/self/{qr_token}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_checkin_scan_unauthorized_user(client: AsyncClient):
    """Non-host/non-cohost cannot scan to check in."""
    mock_verify = AsyncMock(return_value=True)

    with patch("app.api.v1.auth.verify_code", mock_verify):
        # Host creates event
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800000022",
            "code": "123456",
        })
        host_cookies = {"events_token": resp.cookies.get("events_token")}

        resp = await client.post("/api/v1/events", json={
            "title": "Scan Auth Test",
            "start_time": "2026-11-03T10:00:00+08:00",
        }, cookies=host_cookies)
        event_id = resp.json()["data"]["id"]
        slug = resp.json()["data"]["slug"]

        with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as m:
            m.return_value = None
            await client.post(f"/api/v1/events/{event_id}/publish", cookies=host_cookies)

        resp = await client.post(f"/api/v1/events/{slug}/register", json={
            "phone": "13800000022",
        }, cookies=host_cookies)
        qr_token = resp.json()["data"]["qr_code_token"]

        # Random user tries to scan
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800000099",
            "code": "123456",
        })
        random_cookies = {"events_token": resp.cookies.get("events_token")}

        resp = await client.post("/api/v1/checkin/scan", json={
            "qr_token": qr_token,
        }, cookies=random_cookies)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Shared check-in key tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_checkin_key_flow(client: AsyncClient):
    """Generate key → scan-by-key succeeds → revoke key → scan-by-key fails."""
    mock_verify = AsyncMock(return_value=True)

    with patch("app.api.v1.auth.verify_code", mock_verify):
        # Host login
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800000030",
            "code": "123456",
        })
        host_cookies = {"events_token": resp.cookies.get("events_token")}

        # Create + publish event
        resp = await client.post("/api/v1/events", json={
            "title": "Checkin Key Test Event",
            "start_time": "2026-12-01T10:00:00+08:00",
        }, cookies=host_cookies)
        assert resp.status_code == 201
        event_id = resp.json()["data"]["id"]
        slug = resp.json()["data"]["slug"]

        with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as m:
            m.return_value = None
            await client.post(f"/api/v1/events/{event_id}/publish", cookies=host_cookies)

        # Register
        resp = await client.post(f"/api/v1/events/{slug}/register", json={
            "phone": "13800000030",
        }, cookies=host_cookies)
        assert resp.status_code == 201
        qr_token = resp.json()["data"]["qr_code_token"]

        # No key yet
        resp = await client.get(
            f"/api/v1/host/events/{event_id}/checkin-key", cookies=host_cookies
        )
        assert resp.json()["data"]["checkin_key"] is None

        # Generate key
        resp = await client.post(
            f"/api/v1/host/events/{event_id}/checkin-key", cookies=host_cookies
        )
        assert resp.status_code == 200
        key = resp.json()["data"]["checkin_key"]
        assert key is not None

        # scan-by-key (no login needed)
        resp = await client.post("/api/v1/checkin/scan-by-key", json={
            "qr_token": qr_token,
            "checkin_key": key,
        })
        assert resp.status_code == 200
        assert "签到成功" in resp.json()["data"]["message"]

        # Revoke key
        resp = await client.delete(
            f"/api/v1/host/events/{event_id}/checkin-key", cookies=host_cookies
        )
        assert resp.status_code == 200

        # scan-by-key should now fail
        resp = await client.post("/api/v1/checkin/scan-by-key", json={
            "qr_token": qr_token,
            "checkin_key": key,
        })
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_scan_by_key_wrong_event(client: AsyncClient):
    """scan-by-key rejects QR codes from a different event."""
    mock_verify = AsyncMock(return_value=True)

    with patch("app.api.v1.auth.verify_code", mock_verify):
        resp = await client.post("/api/v1/auth/phone/login", json={
            "phone": "13800000031",
            "code": "123456",
        })
        host_cookies = {"events_token": resp.cookies.get("events_token")}

        # Event A with key
        resp = await client.post("/api/v1/events", json={
            "title": "Key Event A",
            "start_time": "2026-12-02T10:00:00+08:00",
        }, cookies=host_cookies)
        event_a_id = resp.json()["data"]["id"]

        with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as m:
            m.return_value = None
            await client.post(f"/api/v1/events/{event_a_id}/publish", cookies=host_cookies)

        resp = await client.post(
            f"/api/v1/host/events/{event_a_id}/checkin-key", cookies=host_cookies
        )
        key_a = resp.json()["data"]["checkin_key"]

        # Event B with a registration
        resp = await client.post("/api/v1/events", json={
            "title": "Key Event B",
            "start_time": "2026-12-03T10:00:00+08:00",
        }, cookies=host_cookies)
        event_b_id = resp.json()["data"]["id"]
        slug_b = resp.json()["data"]["slug"]

        with patch("app.api.v1.events._create_event_circle", new_callable=AsyncMock) as m:
            m.return_value = None
            await client.post(f"/api/v1/events/{event_b_id}/publish", cookies=host_cookies)

        resp = await client.post(f"/api/v1/events/{slug_b}/register", json={
            "phone": "13800000031",
        }, cookies=host_cookies)
        qr_token_b = resp.json()["data"]["qr_code_token"]

        # Try to use event A's key to scan event B's code
        resp = await client.post("/api/v1/checkin/scan-by-key", json={
            "qr_token": qr_token_b,
            "checkin_key": key_a,
        })
        assert resp.status_code == 400
        assert "不属于当前活动" in resp.json()["detail"]
