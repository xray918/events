"""Tests for the verification code service (Redis-backed)."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.verification import (
    generate_code,
    store_code,
    verify_code,
    can_send,
    CODE_EXPIRE_SECONDS,
    RESEND_COOLDOWN_SECONDS,
    MAX_ATTEMPTS,
)


def test_generate_code_length():
    code = generate_code()
    assert len(code) == 6
    assert code.isdigit()


def test_generate_code_range():
    for _ in range(100):
        code = generate_code()
        assert 100000 <= int(code) <= 999999


@pytest.fixture
def mock_redis():
    store = {}

    async def mock_get(key):
        return store.get(key)

    async def mock_set(key, value, ex=None):
        store[key] = value

    async def mock_delete(key):
        store.pop(key, None)

    async def mock_ttl(key):
        return 250 if key in store else -2

    r = AsyncMock()
    r.get = AsyncMock(side_effect=mock_get)
    r.set = AsyncMock(side_effect=mock_set)
    r.delete = AsyncMock(side_effect=mock_delete)
    r.ttl = AsyncMock(side_effect=mock_ttl)

    r._store = store
    return r


@pytest.mark.asyncio
async def test_store_and_verify_code(mock_redis):
    with patch("app.services.verification.get_redis", return_value=mock_redis):
        await store_code("13900000001", "123456")
        result = await verify_code("13900000001", "123456")
        assert result is True

        result = await verify_code("13900000001", "123456")
        assert result is False


@pytest.mark.asyncio
async def test_verify_wrong_code(mock_redis):
    with patch("app.services.verification.get_redis", return_value=mock_redis):
        await store_code("13900000002", "654321")
        result = await verify_code("13900000002", "000000")
        assert result is False

        result = await verify_code("13900000002", "654321")
        assert result is True


@pytest.mark.asyncio
async def test_verify_expired_code(mock_redis):
    with patch("app.services.verification.get_redis", return_value=mock_redis):
        result = await verify_code("13900000003", "123456")
        assert result is False


@pytest.mark.asyncio
async def test_max_attempts_exceeded(mock_redis):
    with patch("app.services.verification.get_redis", return_value=mock_redis):
        await store_code("13900000004", "111111")

        for _ in range(MAX_ATTEMPTS):
            await verify_code("13900000004", "000000")

        result = await verify_code("13900000004", "111111")
        assert result is False


@pytest.mark.asyncio
async def test_can_send_first_time(mock_redis):
    with patch("app.services.verification.get_redis", return_value=mock_redis):
        result = await can_send("13900000005")
        assert result is True


@pytest.mark.asyncio
async def test_can_send_within_cooldown(mock_redis):
    """When TTL is high (just stored), elapsed < RESEND_COOLDOWN → cannot send."""
    with patch("app.services.verification.get_redis", return_value=mock_redis):
        await store_code("13900000006", "999999")
        mock_redis.ttl = AsyncMock(return_value=CODE_EXPIRE_SECONDS - 10)
        result = await can_send("13900000006")
        assert result is False


@pytest.mark.asyncio
async def test_can_send_after_cooldown(mock_redis):
    """When TTL is low (enough time passed), elapsed >= RESEND_COOLDOWN → can send."""
    with patch("app.services.verification.get_redis", return_value=mock_redis):
        await store_code("13900000007", "888888")
        mock_redis.ttl = AsyncMock(return_value=CODE_EXPIRE_SECONDS - RESEND_COOLDOWN_SECONDS)
        result = await can_send("13900000007")
        assert result is True
