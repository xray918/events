"""Registration API — supports both human users and agents."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.clawdchat import Agent, User
from app.models.event import Event, EventRegistration
from app.schemas.event import RegisterRequest
from app.core.deps import get_optional_agent, get_optional_user
from app.core.security import generate_qr_token, utc_now

router = APIRouter()


async def _get_registrant_identity(
    agent: Optional[Agent],
    user: Optional[User],
) -> tuple[User, Optional[Agent]]:
    """Resolve the actual user (owner) and optional agent for a registration."""
    if agent:
        if not agent.is_claimed or not agent.owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Agent 尚未认领，无法报名。请先在虾聊认领此 Agent。",
            )
        return agent.owner, agent
    elif user:
        return user, None
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录或使用 Agent API Key")


@router.get("/me")
async def my_registrations(
    agent: Optional[Agent] = Depends(get_optional_agent),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """List all my registrations."""
    if not agent and not user:
        raise HTTPException(status_code=401, detail="请先登录")

    owner_user_id = agent.owner_id if agent else user.id

    result = await db.execute(
        select(EventRegistration)
        .options(selectinload(EventRegistration.event))
        .where(EventRegistration.user_id == owner_user_id)
        .order_by(EventRegistration.registered_at.desc())
    )
    regs = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": str(r.id),
                "event_id": str(r.event_id),
                "event_title": r.event.title if r.event else None,
                "event_slug": r.event.slug if r.event else None,
                "status": r.status,
                "registered_via": r.registered_via,
                "qr_code_token": r.qr_code_token,
                "registered_at": r.registered_at.isoformat(),
                "checked_in_at": r.checked_in_at.isoformat() if r.checked_in_at else None,
            }
            for r in regs
        ],
    }
