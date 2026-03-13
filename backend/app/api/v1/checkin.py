"""Check-in API — QR code scanning and attendance."""

import io
from uuid import UUID

import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import get_current_user
from app.core.security import utc_now
from app.db import get_db
from app.models.clawdchat import User
from app.models.event import Event, EventRegistration

router = APIRouter()


@router.get("/qr/{qr_token}")
async def get_qr_code(qr_token: str, db: AsyncSession = Depends(get_db)):
    """Generate QR code image for a registration."""
    result = await db.execute(
        select(EventRegistration).where(EventRegistration.qr_code_token == qr_token)
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="无效的签到码")

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


@router.get("/verify/{qr_token}")
async def verify_qr_token(qr_token: str, db: AsyncSession = Depends(get_db)):
    """Verify a QR token and return registration info (for scanner preview)."""
    result = await db.execute(
        select(EventRegistration)
        .options(
            selectinload(EventRegistration.user),
            selectinload(EventRegistration.event),
        )
        .where(EventRegistration.qr_code_token == qr_token)
    )
    reg = result.unique().scalars().first()
    if not reg:
        raise HTTPException(status_code=404, detail="无效的签到码")

    return {
        "success": True,
        "data": {
            "registration_id": str(reg.id),
            "event_title": reg.event.title if reg.event else None,
            "user_nickname": reg.user.nickname if reg.user else None,
            "status": reg.status,
            "already_checked_in": reg.checked_in_at is not None,
            "checked_in_at": reg.checked_in_at.isoformat() if reg.checked_in_at else None,
            "allow_self_checkin": reg.event.allow_self_checkin if reg.event else True,
        },
    }


class CheckinRequest(BaseModel):
    qr_token: str


@router.post("/scan")
async def checkin_by_scan(
    body: CheckinRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check in a guest by scanning their QR code (host action)."""
    result = await db.execute(
        select(EventRegistration)
        .options(selectinload(EventRegistration.event))
        .where(EventRegistration.qr_code_token == body.qr_token)
    )
    reg = result.unique().scalars().first()
    if not reg:
        raise HTTPException(status_code=404, detail="无效的签到码")

    if reg.event and reg.event.host_id != user.id:
        raise HTTPException(status_code=403, detail="你不是此活动的主办方")

    if reg.status != "approved":
        raise HTTPException(status_code=400, detail=f"报名状态为 {reg.status}，无法签到")

    if reg.checked_in_at:
        return {
            "success": True,
            "data": {
                "already_checked_in": True,
                "checked_in_at": reg.checked_in_at.isoformat(),
                "message": "此参会者已签到",
            },
        }

    reg.checked_in_at = utc_now()

    return {
        "success": True,
        "data": {
            "already_checked_in": False,
            "checked_in_at": reg.checked_in_at.isoformat(),
            "message": "签到成功！",
        },
    }


@router.post("/self/{qr_token}")
async def self_checkin(
    qr_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Self check-in by QR token (attendee scans event check-in page)."""
    result = await db.execute(
        select(EventRegistration)
        .options(selectinload(EventRegistration.event))
        .where(EventRegistration.qr_code_token == qr_token)
    )
    reg = result.unique().scalars().first()
    if not reg:
        raise HTTPException(status_code=404, detail="无效的签到码")

    if reg.event and not reg.event.allow_self_checkin:
        raise HTTPException(status_code=403, detail="此活动不允许自助签到，请找工作人员扫码签到")

    if reg.status != "approved":
        raise HTTPException(status_code=400, detail="报名尚未通过审批")

    if reg.checked_in_at:
        return {"success": True, "data": {"message": "你已签到", "checked_in_at": reg.checked_in_at.isoformat()}}

    reg.checked_in_at = utc_now()
    return {"success": True, "data": {"message": "签到成功！", "checked_in_at": reg.checked_in_at.isoformat()}}
