"""Notification API — blast messages, triggered by host or staff agent."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user, get_claimed_agent
from app.core.security import utc_now
from app.db import get_db
from app.models.clawdchat import Agent, User
from app.models.event import Event, EventBlast, EventBlastLog, EventRegistration, EventStaff
from app.services.notify import send_blast_to_registration

router = APIRouter()


def _format_event_time(event: Event) -> str:
    """Format event start_time for SMS template (e.g. '3月20日 14:00')."""
    if not event.start_time:
        return "待定"
    import zoneinfo
    tz = zoneinfo.ZoneInfo(event.timezone or "Asia/Shanghai")
    local = event.start_time.astimezone(tz)
    return f"{local.month}月{local.day}日 {local.strftime('%H:%M')}"


class BlastRequest(BaseModel):
    subject: str
    content: str
    channels: list[str] = ["sms", "a2a"]
    target_status: Optional[str] = "approved"


@router.post("/events/{event_id}/blast")
async def send_blast(
    event_id: UUID,
    body: BlastRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a blast message to all approved registrations (host action)."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="活动不存在")
    if event.host_id != user.id:
        raise HTTPException(status_code=403, detail="无权操作此活动")

    blast = EventBlast(
        event_id=event_id,
        subject=body.subject,
        content=body.content,
        channels=body.channels,
        blast_type="custom",
        created_by=user.id,
        sent_at=utc_now(),
    )
    db.add(blast)
    await db.flush()

    where = [EventRegistration.event_id == event_id]
    if body.target_status:
        where.append(EventRegistration.status == body.target_status)

    regs_q = await db.execute(
        select(EventRegistration)
        .options(selectinload(EventRegistration.user))
        .where(*where)
    )
    regs = regs_q.unique().scalars().all()

    event_time = _format_event_time(event)
    event_location = event.location_name or event.location_address or "线上"

    sent_count = 0
    failed_count = 0
    for reg in regs:
        results = await send_blast_to_registration(
            reg, body.subject, body.content, body.channels, db,
            event_time=event_time, event_location=event_location,
        )
        log_status = "sent" if any(r.get("success") for r in results.values()) else "failed"

        for channel, r in results.items():
            db.add(EventBlastLog(
                blast_id=blast.id,
                registration_id=reg.id,
                channel=channel,
                status="sent" if r.get("success") else "failed",
                error=r.get("error"),
                sent_at=utc_now() if r.get("success") else None,
            ))

        if log_status == "sent":
            sent_count += 1
        else:
            failed_count += 1

    return {
        "success": True,
        "data": {
            "blast_id": str(blast.id),
            "total_recipients": len(regs),
            "sent": sent_count,
            "failed": failed_count,
        },
    }


@router.post("/staff/events/{event_id}/notify")
async def staff_send_notification(
    event_id: UUID,
    body: BlastRequest,
    agent: Agent = Depends(get_claimed_agent),
    db: AsyncSession = Depends(get_db),
):
    """Send notification via staff agent."""
    staff = await db.execute(
        select(EventStaff).where(EventStaff.event_id == event_id, EventStaff.agent_id == agent.id)
    )
    if not staff.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="你不是此活动的 Staff Agent")

    ev_result = await db.execute(select(Event).where(Event.id == event_id))
    event = ev_result.scalar_one()

    blast = EventBlast(
        event_id=event_id,
        subject=body.subject,
        content=body.content,
        channels=body.channels,
        blast_type="custom",
        sent_at=utc_now(),
    )
    db.add(blast)
    await db.flush()

    where = [EventRegistration.event_id == event_id]
    if body.target_status:
        where.append(EventRegistration.status == body.target_status)

    regs_q = await db.execute(select(EventRegistration).where(*where))
    regs = regs_q.scalars().all()

    event_time = _format_event_time(event)
    event_location = event.location_name or event.location_address or "线上"

    sent = 0
    for reg in regs:
        results = await send_blast_to_registration(
            reg, body.subject, body.content, body.channels, db,
            event_time=event_time, event_location=event_location,
        )
        if any(r.get("success") for r in results.values()):
            sent += 1

    return {
        "success": True,
        "data": {"sent": sent, "total": len(regs)},
    }
