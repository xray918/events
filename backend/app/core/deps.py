"""Authentication dependencies — dual auth: Human JWT + Agent API Key."""

from typing import Optional
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.clawdchat import Agent, User
from app.models.event import EventStaff
from app.core.security import hash_api_key, verify_token


# ---------------------------------------------------------------------------
# Agent auth (Bearer API Key — same as ClawdChat)
# ---------------------------------------------------------------------------

async def get_current_agent(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证头",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证格式错误，应为 'Bearer YOUR_API_KEY'",
        )

    api_key_hashed = hash_api_key(parts[1])
    result = await db.execute(
        select(Agent)
        .options(selectinload(Agent.owner))
        .where(Agent.api_key_hash == api_key_hashed)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 API Key")
    if not agent.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该账号已被禁用")
    return agent


async def get_claimed_agent(
    agent: Agent = Depends(get_current_agent),
) -> Agent:
    if not agent.is_claimed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent 尚未被认领，请先在虾聊完成认领",
            headers={"X-Hint": "需要在 clawdchat.cn 认领此 Agent"},
        )
    return agent


async def get_optional_agent(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[Agent]:
    if not authorization:
        return None
    try:
        return await get_current_agent(authorization, db)
    except HTTPException:
        return None


# ---------------------------------------------------------------------------
# Human user auth (JWT Cookie)
# ---------------------------------------------------------------------------

async def get_current_user(
    events_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not events_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
        )

    payload = verify_token(events_token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的 token")

    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


async def get_optional_user(
    events_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not events_token:
        return None
    try:
        return await get_current_user(events_token, db)
    except HTTPException:
        return None


# ---------------------------------------------------------------------------
# Combined: at least one identity required
# ---------------------------------------------------------------------------

async def get_registrant(
    agent: Optional[Agent] = Depends(get_optional_agent),
    user: Optional[User] = Depends(get_optional_user),
) -> tuple[Optional[Agent], Optional[User]]:
    """Return (agent, user). At least one must be present."""
    if not agent and not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录或使用 Agent API Key 认证",
        )
    return agent, user


# ---------------------------------------------------------------------------
# Staff agent: must be assigned to the event
# ---------------------------------------------------------------------------

async def get_staff_agent_for_event(
    event_id: UUID,
    agent: Agent = Depends(get_claimed_agent),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    result = await db.execute(
        select(EventStaff).where(
            EventStaff.event_id == event_id,
            EventStaff.agent_id == agent.id,
        )
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="你不是此活动的 Staff Agent",
        )
    return agent
