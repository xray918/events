"""Staff Agent API — digital employee endpoints for event management."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_claimed_agent
from app.core.security import utc_now
from app.db import get_db
from app.models.clawdchat import Agent
from app.models.event import (
    Event,
    EventRegistration,
    EventStaff,
    EventRanking,
    EventWinner,
)

router = APIRouter()


async def _require_staff(agent: Agent, event_id: UUID, db: AsyncSession) -> EventStaff:
    result = await db.execute(
        select(EventStaff).where(
            EventStaff.event_id == event_id,
            EventStaff.agent_id == agent.id,
        )
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=403, detail="你不是此活动的 Staff Agent")
    return staff


# ---------------------------------------------------------------------------
# Registrations management
# ---------------------------------------------------------------------------

@router.get("/events/{event_id}/registrations")
async def list_registrations(
    event_id: UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    agent: Agent = Depends(get_claimed_agent),
    db: AsyncSession = Depends(get_db),
):
    """List registrations for an event (Staff Agent only)."""
    await _require_staff(agent, event_id, db)

    where = [EventRegistration.event_id == event_id]
    if status_filter:
        where.append(EventRegistration.status == status_filter)

    count_q = select(func.count()).select_from(EventRegistration).where(*where)
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(EventRegistration)
        .options(selectinload(EventRegistration.user), selectinload(EventRegistration.agent))
        .where(*where)
        .order_by(EventRegistration.registered_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(q)
    regs = result.unique().scalars().all()

    return {
        "success": True,
        "total": total,
        "data": [
            {
                "id": str(r.id),
                "user": {
                    "id": str(r.user.id) if r.user else None,
                    "nickname": r.user.nickname if r.user else None,
                    "phone": r.phone,
                } if r.user else None,
                "agent": {
                    "id": str(r.agent.id) if r.agent else None,
                    "name": r.agent.name if r.agent else None,
                    "display_name": r.agent.display_label if r.agent else None,
                } if r.agent else None,
                "status": r.status,
                "registered_via": r.registered_via,
                "custom_answers": r.custom_answers,
                "registered_at": r.registered_at.isoformat(),
                "checked_in_at": r.checked_in_at.isoformat() if r.checked_in_at else None,
            }
            for r in regs
        ],
    }


# ---------------------------------------------------------------------------
# Approve / Decline
# ---------------------------------------------------------------------------

class ApprovalRequest(BaseModel):
    reason: Optional[str] = None


@router.post("/events/{event_id}/registrations/{reg_id}/approve")
async def approve_registration(
    event_id: UUID,
    reg_id: UUID,
    body: ApprovalRequest = ApprovalRequest(),
    agent: Agent = Depends(get_claimed_agent),
    db: AsyncSession = Depends(get_db),
):
    """Approve a registration."""
    await _require_staff(agent, event_id, db)

    result = await db.execute(
        select(EventRegistration).where(
            EventRegistration.id == reg_id,
            EventRegistration.event_id == event_id,
        )
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="报名记录不存在")
    if reg.status not in ("pending", "waitlisted"):
        raise HTTPException(status_code=400, detail=f"当前状态 {reg.status} 不可审批")

    reg.status = "approved"
    reg.approved_by = agent.id
    reg.approved_at = utc_now()

    return {"success": True, "data": {"id": str(reg.id), "status": "approved"}}


@router.post("/events/{event_id}/registrations/{reg_id}/decline")
async def decline_registration(
    event_id: UUID,
    reg_id: UUID,
    body: ApprovalRequest = ApprovalRequest(),
    agent: Agent = Depends(get_claimed_agent),
    db: AsyncSession = Depends(get_db),
):
    """Decline a registration."""
    await _require_staff(agent, event_id, db)

    result = await db.execute(
        select(EventRegistration).where(
            EventRegistration.id == reg_id,
            EventRegistration.event_id == event_id,
        )
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="报名记录不存在")
    if reg.status == "declined":
        raise HTTPException(status_code=400, detail="已拒绝")

    reg.status = "declined"
    reg.approved_by = agent.id

    return {"success": True, "data": {"id": str(reg.id), "status": "declined"}}


# ---------------------------------------------------------------------------
# Batch approve
# ---------------------------------------------------------------------------

class BatchApproveRequest(BaseModel):
    registration_ids: Optional[list[UUID]] = None
    approve_all_pending: bool = False


@router.post("/events/{event_id}/registrations/batch-approve")
async def batch_approve(
    event_id: UUID,
    body: BatchApproveRequest,
    agent: Agent = Depends(get_claimed_agent),
    db: AsyncSession = Depends(get_db),
):
    """Batch approve registrations."""
    await _require_staff(agent, event_id, db)

    where = [
        EventRegistration.event_id == event_id,
        EventRegistration.status.in_(["pending", "waitlisted"]),
    ]
    if not body.approve_all_pending and body.registration_ids:
        where.append(EventRegistration.id.in_(body.registration_ids))

    stmt = (
        update(EventRegistration)
        .where(*where)
        .values(status="approved", approved_by=agent.id, approved_at=utc_now())
    )
    result = await db.execute(stmt)
    count = result.rowcount

    return {"success": True, "data": {"approved_count": count}}


# ---------------------------------------------------------------------------
# Event stats
# ---------------------------------------------------------------------------

@router.get("/events/{event_id}/stats")
async def event_stats(
    event_id: UUID,
    agent: Agent = Depends(get_claimed_agent),
    db: AsyncSession = Depends(get_db),
):
    """Get event statistics."""
    await _require_staff(agent, event_id, db)

    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="活动不存在")

    status_counts = {}
    for s in ["pending", "approved", "declined", "waitlisted", "cancelled"]:
        count_q = select(func.count()).select_from(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.status == s,
        )
        status_counts[s] = (await db.execute(count_q)).scalar() or 0

    checkin_q = select(func.count()).select_from(EventRegistration).where(
        EventRegistration.event_id == event_id,
        EventRegistration.checked_in_at.isnot(None),
    )
    checked_in = (await db.execute(checkin_q)).scalar() or 0

    return {
        "success": True,
        "data": {
            "event_id": str(event_id),
            "title": event.title,
            "capacity": event.capacity,
            "registrations": status_counts,
            "total_registered": status_counts["approved"] + status_counts["pending"],
            "checked_in": checked_in,
        },
    }


# ---------------------------------------------------------------------------
# Rankings
# ---------------------------------------------------------------------------

@router.get("/events/{event_id}/rankings")
async def get_rankings(
    event_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    agent: Agent = Depends(get_claimed_agent),
    db: AsyncSession = Depends(get_db),
):
    """Get agent interaction rankings for an event."""
    await _require_staff(agent, event_id, db)

    q = (
        select(EventRanking)
        .options(selectinload(EventRanking.agent))
        .where(EventRanking.event_id == event_id)
        .order_by(EventRanking.score.desc())
        .limit(limit)
    )
    result = await db.execute(q)
    rankings = result.unique().scalars().all()

    return {
        "success": True,
        "data": [
            {
                "rank": r.rank,
                "agent_name": r.agent.name if r.agent else "unknown",
                "agent_display_name": r.agent.display_label if r.agent else "unknown",
                "score": r.score,
                "likes_received": r.likes_received,
                "post_count": r.post_count,
                "comment_count": r.comment_count,
            }
            for r in rankings
        ],
    }


# ---------------------------------------------------------------------------
# Winners
# ---------------------------------------------------------------------------

class WinnerCreate(BaseModel):
    registration_id: UUID
    rank: Optional[int] = None
    prize_name: Optional[str] = None
    prize_description: Optional[str] = None


class WinnersRequest(BaseModel):
    winners: list[WinnerCreate]
    notify: bool = True


@router.post("/events/{event_id}/winners")
async def confirm_winners(
    event_id: UUID,
    body: WinnersRequest,
    agent: Agent = Depends(get_claimed_agent),
    db: AsyncSession = Depends(get_db),
):
    """Confirm winners for an event."""
    await _require_staff(agent, event_id, db)

    created = []
    for w in body.winners:
        winner = EventWinner(
            event_id=event_id,
            registration_id=w.registration_id,
            rank=w.rank,
            prize_name=w.prize_name,
            prize_description=w.prize_description,
            confirmed_by=agent.id,
        )
        db.add(winner)
        created.append(winner)

    await db.flush()

    # TODO: Phase 3 — trigger dual-channel notifications if body.notify

    return {
        "success": True,
        "data": {
            "winners_count": len(created),
            "winners": [
                {
                    "id": str(w.id),
                    "registration_id": str(w.registration_id),
                    "prize_name": w.prize_name,
                    "rank": w.rank,
                }
                for w in created
            ],
        },
    }
