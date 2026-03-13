"""Host management API — event owner endpoints."""

import csv
import io
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.core.security import utc_now
from app.db import get_db
from app.models.clawdchat import Agent, User
from app.models.event import Event, EventRegistration, EventStaff, EventWinner
from app.services.notify import notify_registration_approved

router = APIRouter()


async def _require_host(user: User, event_id: UUID, db: AsyncSession) -> Event:
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="活动不存在")
    if event.host_id != user.id:
        raise HTTPException(status_code=403, detail="无权管理此活动")
    return event


# ---------------------------------------------------------------------------
# Registration management
# ---------------------------------------------------------------------------

@router.get("/events/{event_id}/registrations")
async def list_registrations(
    event_id: UUID,
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List registrations for host's event."""
    await _require_host(user, event_id, db)

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
        "data": [_reg_to_dict(r) for r in regs],
    }


def _reg_to_dict(r: EventRegistration) -> dict:
    return {
        "id": str(r.id),
        "user": {
            "id": str(r.user.id),
            "nickname": r.user.nickname,
            "phone": r.phone,
            "email": r.user.email,
        } if r.user else None,
        "agent": {
            "id": str(r.agent.id),
            "name": r.agent.name,
            "display_name": r.agent.display_label,
        } if r.agent else None,
        "status": r.status,
        "registered_via": r.registered_via,
        "custom_answers": r.custom_answers,
        "qr_code_token": r.qr_code_token,
        "registered_at": r.registered_at.isoformat(),
        "approved_at": r.approved_at.isoformat() if r.approved_at else None,
        "checked_in_at": r.checked_in_at.isoformat() if r.checked_in_at else None,
    }


# ---------------------------------------------------------------------------
# Approve / Decline by host
# ---------------------------------------------------------------------------

@router.post("/events/{event_id}/registrations/{reg_id}/approve")
async def approve_registration(
    event_id: UUID,
    reg_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event = await _require_host(user, event_id, db)
    result = await db.execute(
        select(EventRegistration).where(
            EventRegistration.id == reg_id,
            EventRegistration.event_id == event_id,
        )
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="报名记录不存在")

    reg.status = "approved"
    reg.approved_by = user.id
    reg.approved_at = utc_now()

    try:
        await notify_registration_approved(reg, event.title, db)
    except Exception:
        import logging
        logging.getLogger(__name__).warning(f"Notification failed for reg {reg_id}")

    return {"success": True, "data": {"id": str(reg.id), "status": "approved"}}


@router.post("/events/{event_id}/registrations/{reg_id}/decline")
async def decline_registration(
    event_id: UUID,
    reg_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_host(user, event_id, db)
    result = await db.execute(
        select(EventRegistration).where(
            EventRegistration.id == reg_id,
            EventRegistration.event_id == event_id,
        )
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="报名记录不存在")

    reg.status = "declined"
    reg.approved_by = user.id
    return {"success": True, "data": {"id": str(reg.id), "status": "declined"}}


@router.post("/events/{event_id}/registrations/batch-approve")
async def batch_approve(
    event_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve all pending registrations."""
    event = await _require_host(user, event_id, db)

    pending_q = await db.execute(
        select(EventRegistration).where(
            EventRegistration.event_id == event_id,
            EventRegistration.status.in_(["pending", "waitlisted"]),
        )
    )
    pending_regs = pending_q.scalars().all()

    for reg in pending_regs:
        reg.status = "approved"
        reg.approved_by = user.id
        reg.approved_at = utc_now()

    await db.flush()

    import logging
    logger = logging.getLogger(__name__)
    for reg in pending_regs:
        try:
            await notify_registration_approved(reg, event.title, db)
        except Exception:
            logger.warning(f"Batch notification failed for reg {reg.id}")

    return {"success": True, "data": {"approved_count": len(pending_regs)}}


# ---------------------------------------------------------------------------
# Staff agent assignment
# ---------------------------------------------------------------------------

class StaffAssignRequest(BaseModel):
    agent_name: str
    role: str = "staff"
    permissions: list[str] = ["all"]


@router.post("/events/{event_id}/staff")
async def assign_staff(
    event_id: UUID,
    body: StaffAssignRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Assign a staff agent to an event."""
    await _require_host(user, event_id, db)

    agent_result = await db.execute(
        select(Agent).where(Agent.name == body.agent_name, Agent.is_active == True)
    )
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{body.agent_name}' 不存在")

    existing = await db.execute(
        select(EventStaff).where(
            EventStaff.event_id == event_id,
            EventStaff.agent_id == agent.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="该 Agent 已是此活动的 Staff")

    staff = EventStaff(
        event_id=event_id,
        agent_id=agent.id,
        role=body.role,
        permissions=body.permissions,
        assigned_by=user.id,
    )
    db.add(staff)
    await db.flush()

    return {
        "success": True,
        "data": {
            "id": str(staff.id),
            "agent_name": agent.name,
            "role": staff.role,
        },
    }


@router.get("/events/{event_id}/staff")
async def list_staff(
    event_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_host(user, event_id, db)
    result = await db.execute(
        select(EventStaff)
        .options(selectinload(EventStaff.agent))
        .where(EventStaff.event_id == event_id)
    )
    staff_list = result.unique().scalars().all()
    return {
        "success": True,
        "data": [
            {
                "id": str(s.id),
                "agent_name": s.agent.name if s.agent else None,
                "agent_display_name": s.agent.display_label if s.agent else None,
                "role": s.role,
                "permissions": s.permissions,
            }
            for s in staff_list
        ],
    }


@router.delete("/events/{event_id}/staff/{staff_id}")
async def remove_staff(
    event_id: UUID,
    staff_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_host(user, event_id, db)
    result = await db.execute(
        select(EventStaff).where(EventStaff.id == staff_id, EventStaff.event_id == event_id)
    )
    staff = result.scalar_one_or_none()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff 不存在")
    await db.delete(staff)
    return {"success": True, "message": "已移除"}


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

@router.get("/events/{event_id}/registrations/export")
async def export_registrations_csv(
    event_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export registrations as CSV."""
    event = await _require_host(user, event_id, db)

    q = (
        select(EventRegistration)
        .options(selectinload(EventRegistration.user), selectinload(EventRegistration.agent))
        .where(EventRegistration.event_id == event_id)
        .order_by(EventRegistration.registered_at.asc())
    )
    result = await db.execute(q)
    regs = result.unique().scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["姓名", "手机号", "邮箱", "Agent", "状态", "报名方式", "报名时间", "签到时间"])

    for r in regs:
        writer.writerow([
            r.user.nickname if r.user else "",
            r.phone or "",
            r.user.email if r.user else "",
            r.agent.name if r.agent else "",
            r.status,
            r.registered_via,
            r.registered_at.isoformat() if r.registered_at else "",
            r.checked_in_at.isoformat() if r.checked_in_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=registrations-{event.id}.csv"},
    )


# ---------------------------------------------------------------------------
# Answer statistics & filtering
# ---------------------------------------------------------------------------

@router.get("/events/{event_id}/answer-stats")
async def answer_statistics(
    event_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate answer statistics per question (counts per answer value).

    Returns {question_id: {answer_value: count, ...}, ...}
    """
    from app.models.event import EventCustomQuestion

    await _require_host(user, event_id, db)

    q_result = await db.execute(
        select(EventCustomQuestion).where(EventCustomQuestion.event_id == event_id)
    )
    questions = q_result.scalars().all()
    question_map = {str(q.id): q for q in questions}

    reg_result = await db.execute(
        select(EventRegistration)
        .where(
            EventRegistration.event_id == event_id,
            EventRegistration.status.notin_(["cancelled"]),
        )
    )
    regs = reg_result.scalars().all()

    stats: dict[str, dict[str, int]] = {}
    for qid in question_map:
        stats[qid] = {}

    for reg in regs:
        answers = reg.custom_answers or {}
        for qid, value in answers.items():
            if qid not in stats:
                stats[qid] = {}
            if isinstance(value, list):
                for v in value:
                    stats[qid][str(v)] = stats[qid].get(str(v), 0) + 1
            else:
                sv = str(value)
                stats[qid][sv] = stats[qid].get(sv, 0) + 1

    result = []
    for qid, q in question_map.items():
        result.append({
            "question_id": qid,
            "question_text": q.question_text,
            "question_type": q.question_type,
            "options": q.options,
            "stats": stats.get(qid, {}),
            "total_answers": sum(stats.get(qid, {}).values()),
        })

    return {"success": True, "data": result}


@router.get("/events/{event_id}/registrations/filter-by-answer")
async def filter_registrations_by_answer(
    event_id: UUID,
    question_id: str = Query(...),
    answer_value: str = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Filter registrations by a specific answer value."""
    await _require_host(user, event_id, db)

    reg_result = await db.execute(
        select(EventRegistration)
        .options(selectinload(EventRegistration.user), selectinload(EventRegistration.agent))
        .where(
            EventRegistration.event_id == event_id,
            EventRegistration.status.notin_(["cancelled"]),
        )
        .order_by(EventRegistration.registered_at.desc())
    )
    all_regs = reg_result.unique().scalars().all()

    filtered = []
    for reg in all_regs:
        answers = reg.custom_answers or {}
        val = answers.get(question_id)
        if val is None:
            continue
        if isinstance(val, list):
            if answer_value in val:
                filtered.append(reg)
        elif str(val) == answer_value:
            filtered.append(reg)

    return {
        "success": True,
        "total": len(filtered),
        "data": [_reg_to_dict(r) for r in filtered],
    }


# ---------------------------------------------------------------------------
# Winners management (host-facing)
# ---------------------------------------------------------------------------

class HostWinnerCreate(BaseModel):
    registration_id: UUID
    rank: Optional[int] = None
    prize_name: Optional[str] = None
    prize_description: Optional[str] = None


class HostWinnersRequest(BaseModel):
    winners: list[HostWinnerCreate]
    notify: bool = True


@router.post("/events/{event_id}/winners")
async def host_confirm_winners(
    event_id: UUID,
    body: HostWinnersRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Host confirms winners and optionally sends notifications."""
    event = await _require_host(user, event_id, db)

    created = []
    for w in body.winners:
        winner = EventWinner(
            event_id=event_id,
            registration_id=w.registration_id,
            rank=w.rank,
            prize_name=w.prize_name,
            prize_description=w.prize_description,
            confirmed_by=user.id,
        )
        db.add(winner)
        created.append(winner)

    await db.flush()

    notify_results = []
    if body.notify:
        from app.services.notify import notify_winner

        for w in created:
            reg_result = await db.execute(
                select(EventRegistration)
                .options(selectinload(EventRegistration.user))
                .where(EventRegistration.id == w.registration_id)
            )
            reg = reg_result.scalar_one_or_none()
            if reg:
                nr = await notify_winner(reg, event.title, w.prize_name or "奖品", db)
                w.notified_at = utc_now()
                notify_results.append({"registration_id": str(w.registration_id), **nr})

    await db.commit()

    return {
        "success": True,
        "data": {
            "winners_count": len(created),
            "notify_results": notify_results,
        },
    }


@router.get("/events/{event_id}/winners")
async def list_winners(
    event_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List confirmed winners for an event."""
    await _require_host(user, event_id, db)

    q = (
        select(EventWinner)
        .where(EventWinner.event_id == event_id)
        .order_by(EventWinner.rank.asc().nullslast())
    )
    result = await db.execute(q)
    winners = result.scalars().all()

    winner_data = []
    for w in winners:
        reg_result = await db.execute(
            select(EventRegistration)
            .options(selectinload(EventRegistration.user), selectinload(EventRegistration.agent))
            .where(EventRegistration.id == w.registration_id)
        )
        reg = reg_result.scalar_one_or_none()

        winner_data.append({
            "id": str(w.id),
            "rank": w.rank,
            "prize_name": w.prize_name,
            "prize_description": w.prize_description,
            "notified_at": w.notified_at.isoformat() if w.notified_at else None,
            "user": {
                "id": str(reg.user.id) if reg and reg.user else None,
                "nickname": reg.user.nickname if reg and reg.user else None,
            } if reg else None,
            "agent": {
                "name": reg.agent.name if reg and reg.agent else None,
            } if reg and reg.agent else None,
        })

    return {"success": True, "data": winner_data}
