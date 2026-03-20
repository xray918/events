"""Dual-channel notification service — SMS for humans, A2A for agents."""

import logging
import zoneinfo
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.clawdchat import Agent, User
from app.models.event import Event, EventRegistration
from app.services.sms import send_sms

logger = logging.getLogger(__name__)


def _format_event_time(event: Event) -> str:
    if not event.start_time:
        return "待定"
    tz = zoneinfo.ZoneInfo(event.timezone or "Asia/Shanghai")
    local = event.start_time.astimezone(tz)
    return f"{local.month}月{local.day}日 {local.strftime('%H:%M')}"


async def notify_registration_approved(
    reg: EventRegistration,
    event: Event,
    db: AsyncSession,
):
    """Notify a registrant that their registration was approved."""
    if reg.phone and settings.sms_blast_template_code:
        await send_sms(
            phone=reg.phone,
            template_code=settings.sms_blast_template_code,
            template_params={
                "event": event.title or "",
                "time": _format_event_time(event),
                "location": event.location_name or event.location_address or "线上",
            },
        )

    if reg.user_id:
        await _notify_user_agents_via_a2a(
            user_id=reg.user_id,
            message=f"你报名的活动「{event.title}」已通过审批！记得准时参加。",
            db=db,
        )


async def notify_winner(
    reg: EventRegistration,
    event_title: str,
    prize_name: str,
    db: AsyncSession,
) -> dict:
    """Notify a winner via both channels. Returns send results."""
    results = {}

    if reg.phone and settings.sms_winner_template_code:
        sms_result = await send_sms(
            phone=reg.phone,
            template_code=settings.sms_winner_template_code,
            template_params={"event": event_title[:20], "prize": prize_name[:10]},
        )
        results["sms"] = sms_result
    elif reg.phone:
        results["sms"] = {"success": False, "error": "Winner SMS template not configured"}

    if reg.user_id:
        a2a_result = await _notify_user_agents_via_a2a(
            user_id=reg.user_id,
            message=f"🏆 恭喜！你在活动「{event_title}」中获奖：{prize_name}！请联系主办方领奖。",
            db=db,
        )
        results["a2a"] = a2a_result

    return results


import re

_PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


def _clean_phone(phone: str) -> str:
    """Strip non-digits and validate Chinese mobile number format."""
    digits = re.sub(r"\D", "", phone.strip())
    return digits if _PHONE_RE.match(digits) else ""


async def send_blast_to_registration(
    reg: EventRegistration,
    subject: str,
    content: str,
    channels: list[str],
    db: AsyncSession,
    *,
    sms_template_code: str = "",
    sms_params: Optional[dict[str, str]] = None,
) -> dict:
    """Send a blast message to a single registration."""
    results = {}

    if "sms" in channels and reg.phone:
        phone = _clean_phone(reg.phone)
        if not phone:
            results["sms"] = {"success": False, "error": "Invalid phone number"}
        elif not sms_template_code:
            results["sms"] = {"success": False, "error": "SMS template not configured"}
        else:
            sms_result = await send_sms(
                phone=phone,
                template_code=sms_template_code,
                template_params=sms_params or {},
            )
            results["sms"] = sms_result

    if "a2a" in channels and reg.user_id:
        a2a_result = await _notify_user_agents_via_a2a(
            user_id=reg.user_id,
            message=f"[{subject}] {content}",
            db=db,
        )
        results["a2a"] = a2a_result

    return results


async def _notify_user_agents_via_a2a(
    user_id: UUID,
    message: str,
    db: AsyncSession,
) -> dict:
    """Send A2A message to ALL agents owned by a user via EventsBot."""
    if not settings.events_bot_api_key:
        logger.warning("EventsBot API key not configured, skipping A2A notification")
        return {"success": False, "error": "EventsBot not configured"}

    result = await db.execute(
        select(Agent).where(Agent.owner_id == user_id, Agent.is_active == True)
    )
    agents = result.scalars().all()

    if not agents:
        return {"success": True, "sent": 0}

    sent = 0
    errors = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        for agent in agents:
            try:
                resp = await client.post(
                    f"{settings.clawdchat_api_base.rstrip('/api/v1')}/a2a/{agent.name}",
                    json={
                        "jsonrpc": "2.0",
                        "method": "message/send",
                        "params": {
                            "message": {
                                "role": "user",
                                "parts": [{"type": "text", "text": message}],
                            }
                        },
                    },
                    headers={"Authorization": f"Bearer {settings.events_bot_api_key}"},
                )
                if resp.status_code == 200:
                    sent += 1
                else:
                    errors.append(f"{agent.name}: HTTP {resp.status_code}")
            except Exception as e:
                errors.append(f"{agent.name}: {e}")

    return {"success": True, "sent": sent, "total": len(agents), "errors": errors}
