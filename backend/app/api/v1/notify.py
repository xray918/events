"""Notification API — blast messages, triggered by host or staff agent."""

import zoneinfo
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.deps import get_current_user, get_claimed_agent
from app.core.security import utc_now
from app.db import get_db
from app.models.clawdchat import Agent, User
from app.models.event import Event, EventBlast, EventBlastLog, EventRegistration, EventStaff
from app.services.notify import send_blast_to_registration
from app.services.sms import send_sms

router = APIRouter()


# ---------------------------------------------------------------------------
# SMS template registry — add new templates here
# ---------------------------------------------------------------------------

SMS_TEMPLATES: dict[str, dict] = {
    "registration_success": {
        "label": "报名成功",
        "config_key": "sms_blast_template_code",
        "variables": ["event", "time", "location"],
        "preview": "【灵犀一动】虾聊恭喜您成功报名「${event}」。时间：${time}；地点：${location}；请准时到场。",
    },
    # "address_change": {
    #     "label": "地点变更",
    #     "config_key": "sms_address_change_template_code",
    #     "variables": ["event", "location"],
    #     "preview": "...",
    # },
    # "checkin_reminder": {
    #     "label": "签到提醒",
    #     "config_key": "sms_checkin_reminder_template_code",
    #     "variables": ["event", "time", "location"],
    #     "preview": "...",
    # },
}


def _get_template_code(template_type: str) -> Optional[str]:
    tpl = SMS_TEMPLATES.get(template_type)
    if not tpl:
        return None
    return getattr(settings, tpl["config_key"], "") or None


def _format_event_time(event: Event) -> str:
    """Format event start_time for SMS template (e.g. '3月20日 14:00')."""
    if not event.start_time:
        return "待定"
    tz = zoneinfo.ZoneInfo(event.timezone or "Asia/Shanghai")
    local = event.start_time.astimezone(tz)
    return f"{local.month}月{local.day}日 {local.strftime('%H:%M')}"


class BlastRequest(BaseModel):
    subject: str = ""
    content: str = ""
    channels: list[str] = ["sms", "a2a"]
    target_status: Optional[str] = "approved"
    sms_template_type: str = "registration_success"
    sms_params: Optional[dict[str, str]] = None


class BlastTestRequest(BaseModel):
    phones: list[str] = Field(..., min_length=1, max_length=3)
    sms_template_type: str = "registration_success"
    sms_params: Optional[dict[str, str]] = None


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

    template_code, sms_params = _resolve_sms_params(event, body.sms_template_type, body.sms_params)

    sent_count = 0
    failed_count = 0
    for reg in regs:
        results = await send_blast_to_registration(
            reg, body.subject or event.title, body.content, body.channels, db,
            sms_template_code=template_code, sms_params=sms_params,
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

    template_code, sms_params = _resolve_sms_params(event, body.sms_template_type, body.sms_params)

    sent = 0
    for reg in regs:
        results = await send_blast_to_registration(
            reg, body.subject or event.title, body.content, body.channels, db,
            sms_template_code=template_code, sms_params=sms_params,
        )
        if any(r.get("success") for r in results.values()):
            sent += 1

    return {
        "success": True,
        "data": {"sent": sent, "total": len(regs)},
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event_defaults(event: Event) -> dict[str, str]:
    """Default values for all known template variables, derived from the event."""
    return {
        "event": event.title or "",
        "time": _format_event_time(event),
        "location": event.location_name or event.location_address or "线上",
    }


def _resolve_sms_params(
    event: Event,
    template_type: str,
    overrides: Optional[dict[str, str]] = None,
) -> tuple[str, dict[str, str]]:
    """Return (template_code, params_dict) with user overrides applied."""
    template_code = _get_template_code(template_type)
    tpl = SMS_TEMPLATES.get(template_type, {})
    variables = tpl.get("variables", [])

    defaults = _event_defaults(event)
    params = {}
    for var in variables:
        val = (overrides or {}).get(var) or defaults.get(var, "")
        params[var] = val
    return template_code or "", params


# ---------------------------------------------------------------------------
# Test SMS (send to specific phone numbers before blasting)
# ---------------------------------------------------------------------------

@router.post("/events/{event_id}/blast/test")
async def blast_test_sms(
    event_id: UUID,
    body: BlastTestRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send test SMS to 1-3 phone numbers before blasting all registrants."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="活动不存在")
    if event.host_id != user.id:
        raise HTTPException(status_code=403, detail="无权操作此活动")

    template_code, sms_params = _resolve_sms_params(event, body.sms_template_type, body.sms_params)
    if not template_code:
        raise HTTPException(status_code=400, detail="该类型短信模板未配置")

    results = []
    for phone in body.phones:
        phone = phone.strip()
        if not phone:
            continue
        r = await send_sms(
            phone=phone,
            template_code=template_code,
            template_params=sms_params,
        )
        results.append({"phone": phone, **r})

    return {"success": True, "data": results}


@router.get("/sms-templates")
async def list_sms_templates():
    """Return available SMS template types for the blast UI."""
    items = []
    for key, tpl in SMS_TEMPLATES.items():
        code = getattr(settings, tpl["config_key"], "") or ""
        items.append({
            "type": key,
            "label": tpl["label"],
            "variables": tpl["variables"],
            "preview": tpl["preview"],
            "configured": bool(code),
        })
    return {"success": True, "data": items}
