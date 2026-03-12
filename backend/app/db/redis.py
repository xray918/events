"""Redis connection — shared async client for cross-worker state (verification codes, etc.)."""

import logging
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
        logger.info(f"Redis connected: {settings.redis_url}")
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
        logger.info("Redis connection closed")
