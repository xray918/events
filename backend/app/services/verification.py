"""Verification code storage and validation via Redis (multi-worker safe)."""

import json
import random
import logging

from app.db.redis import get_redis

logger = logging.getLogger(__name__)

CODE_EXPIRE_SECONDS = 5 * 60
RESEND_COOLDOWN_SECONDS = 60
MAX_ATTEMPTS = 5

_KEY_PREFIX = "events:vcode:"


def _key(phone: str) -> str:
    return f"{_KEY_PREFIX}{phone}"


def generate_code() -> str:
    return str(random.randint(100000, 999999))


async def store_code(phone: str, code: str) -> None:
    r = await get_redis()
    payload = json.dumps({"code": code, "attempts": 0})
    await r.set(_key(phone), payload, ex=CODE_EXPIRE_SECONDS)


async def verify_code(phone: str, code: str) -> bool:
    r = await get_redis()
    key = _key(phone)
    raw = await r.get(key)

    if raw is None:
        return False

    stored = json.loads(raw)

    if stored["attempts"] >= MAX_ATTEMPTS:
        await r.delete(key)
        return False

    stored["attempts"] += 1

    if stored["code"] == code:
        await r.delete(key)
        return True

    ttl = await r.ttl(key)
    if ttl > 0:
        await r.set(key, json.dumps(stored), ex=ttl)

    return False


async def can_send(phone: str) -> bool:
    r = await get_redis()
    ttl = await r.ttl(_key(phone))
    if ttl <= 0:
        return True
    elapsed = CODE_EXPIRE_SECONDS - ttl
    return elapsed >= RESEND_COOLDOWN_SECONDS
