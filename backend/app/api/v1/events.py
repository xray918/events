"""Events CRUD API."""

import re
import unicodedata
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models.clawdchat import Agent, User
from app.models.event import (
    Event, EventCustomQuestion, EventRegistration, EventStaff,
    EventWinner, EventRanking, EventBlast, EventBlastLog, EventCoHost,
)
from app.schemas.event import EventCreate, EventUpdate, EventResponse, EventListResponse, RegisterRequest
from app.core.deps import get_current_user, get_optional_agent, get_optional_user
from app.core.security import generate_qr_token, utc_now
from app.services.clawdchat import publish_event_to_clawdchat as _publish_to_clawdchat
from app.services.llm import generate_event_description

router = APIRouter()


async def _create_event_circle(event_title, event_description, event_slug, agent_api_key=None):
    return await _publish_to_clawdchat(event_title, event_description, event_slug, agent_api_key)


async def _notify_registrant_confirmation(reg, event_title: str, reg_status: str, db):
    """Send confirmation to the registrant via SMS + A2A after successful registration."""
    from app.services.sms import send_sms
    from app.core.config import settings

    status_msg = {
        "approved": "报名成功",
        "pending": "报名已提交，等待审批",
        "waitlisted": "已加入候补",
    }.get(reg_status, "报名已提交")

    if reg.phone:
        try:
            await send_sms(
                phone=reg.phone,
                template_code=settings.sms_template_code,
                template_params={"event": event_title[:20], "status": status_msg[:10]},
            )
        except Exception:
            pass

    if reg.user_id:
        from app.services.notify import _notify_user_agents_via_a2a
        try:
            await _notify_user_agents_via_a2a(
                user_id=reg.user_id,
                message=f"你已报名活动「{event_title}」，状态：{status_msg}。",
                db=db,
            )
        except Exception:
            pass


async def _notify_host_new_registration(event, registrant, reg_status: str):
    """Post a notification to the event's Circle (if exists) about a new registration."""
    from app.services.clawdchat import create_post
    from app.core.config import settings

    if not event.circle_id:
        return

    api_key = settings.events_bot_api_key
    if not api_key:
        return

    status_label = {"approved": "已通过", "pending": "待审批", "waitlisted": "候补"}.get(reg_status, reg_status)
    name = registrant.nickname or "匿名用户"

    manage_url = f"{settings.frontend_url}/manage/{event.id}"
    content = (
        f"📋 **新报名通知**\n\n"
        f"**{name}** 报名了「{event.title}」\n"
        f"状态：{status_label}\n\n"
        f"👉 [前往管理]({manage_url})"
    )

    await create_post(
        circle_name=f"🎉 {event.title}",
        title=f"📋 新报名：{name}",
        content=content,
        url=manage_url,
        api_key=api_key,
    )


def _slugify(title: str) -> str:
    """Generate URL-friendly slug from title."""
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s\u4e00-\u9fff-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = slug.strip("-")
    if not slug:
        import secrets
        slug = secrets.token_urlsafe(8)
    return slug[:180]


async def _ensure_unique_slug(db: AsyncSession, slug: str) -> str:
    base = slug
    counter = 1
    while True:
        exists = await db.execute(select(Event.id).where(Event.slug == slug))
        if not exists.scalar_one_or_none():
            return slug
        slug = f"{base}-{counter}"
        counter += 1


def _mask_address(address: str) -> str:
    """Return approximate address: keep up to district/park level, hide street number."""
    if not address:
        return address
    for sep in ["号", "栋", "楼", "室", "层", "单元", "座"]:
        idx = address.find(sep)
        if idx > 0:
            cut = address[:idx]
            last_marker = max(cut.rfind("路"), cut.rfind("街"), cut.rfind("道"), cut.rfind("园"), cut.rfind("区"))
            if last_marker > 0:
                return address[: last_marker + 1] + "附近"
            return cut + "..."
    if len(address) > 15:
        return address[:15] + "..."
    return address


def _build_event_response(event: Event, mask_address: bool = False) -> dict:
    host_info = None
    if event.host:
        host_info = {
            "id": str(event.host.id),
            "nickname": event.host.nickname,
            "avatar_url": event.host.avatar_url,
        }

    questions = None
    if event.custom_questions:
        questions = [
            {
                "id": str(q.id),
                "question_text": q.question_text,
                "question_type": q.question_type,
                "options": q.options,
                "is_required": q.is_required,
            }
            for q in event.custom_questions
        ]

    reg_count = 0
    attendees_preview = []
    if event.registrations:
        approved_regs = [r for r in event.registrations if r.status == "approved"]
        pending_regs = [r for r in event.registrations if r.status == "pending"]
        reg_count = len(approved_regs) + len(pending_regs)
        for r in approved_regs[:12]:
            if r.user:
                attendees_preview.append({
                    "nickname": r.user.nickname,
                    "avatar_url": r.user.avatar_url,
                })

    loc_address = event.location_address
    address_masked = False
    if mask_address and loc_address:
        loc_address = _mask_address(loc_address)
        address_masked = True

    cohosts_info = None
    if event.cohosts:
        cohosts_info = [
            {
                "id": str(ch.user.id),
                "nickname": ch.user.nickname,
                "avatar_url": ch.user.avatar_url,
            }
            for ch in event.cohosts if ch.user
        ]

    return {
        "id": event.id,
        "title": event.title,
        "slug": event.slug,
        "description": event.description,
        "cover_image_url": event.cover_image_url,
        "event_type": event.event_type,
        "location_name": event.location_name,
        "location_address": loc_address,
        "address_masked": address_masked,
        "online_url": event.online_url,
        "start_time": event.start_time,
        "end_time": event.end_time,
        "timezone": event.timezone,
        "capacity": event.capacity,
        "registration_deadline": event.registration_deadline,
        "visibility": event.visibility,
        "require_approval": event.require_approval,
        "notify_on_register": event.notify_on_register,
        "status": event.status,
        "theme": event.theme,
        "host": host_info,
        "cohosts": cohosts_info,
        "circle_id": event.circle_id,
        "custom_questions": questions,
        "registration_count": reg_count,
        "attendees_preview": attendees_preview,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
    }


# ---------------------------------------------------------------------------
# List events (public)
# ---------------------------------------------------------------------------

@router.get("")
async def list_events(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Browse upcoming events."""
    where_clauses = [Event.visibility == "public"]
    if status_filter:
        where_clauses.append(Event.status == status_filter)
    else:
        where_clauses.append(Event.status == "published")

    count_q = select(func.count()).select_from(Event).where(*where_clauses)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    query = (
        select(Event)
        .options(
            selectinload(Event.host),
            selectinload(Event.registrations),
        )
        .where(*where_clauses)
        .order_by(Event.start_time.asc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    events = result.unique().scalars().all()

    data = [_build_event_response(e) for e in events]
    return {"success": True, "data": data, "total": total}


# ---------------------------------------------------------------------------
# My hosted events (all statuses, for the event creator)
# ---------------------------------------------------------------------------

@router.get("/mine")
async def list_my_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all events created by the current user (all statuses)."""
    where_clauses = [Event.host_id == user.id]

    count_q = select(func.count()).select_from(Event).where(*where_clauses)
    total = (await db.execute(count_q)).scalar() or 0

    query = (
        select(Event)
        .options(selectinload(Event.host), selectinload(Event.registrations))
        .where(*where_clauses)
        .order_by(Event.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    events = result.unique().scalars().all()

    return {"success": True, "data": [_build_event_response(e) for e in events], "total": total}


# ---------------------------------------------------------------------------
# Past events (completed / cancelled)
# ---------------------------------------------------------------------------

@router.get("/past/list")
async def list_past_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Browse past (completed/cancelled) events."""
    where_clauses = [
        Event.visibility == "public",
        Event.status.in_(["completed", "cancelled"]),
    ]

    count_q = select(func.count()).select_from(Event).where(*where_clauses)
    total = (await db.execute(count_q)).scalar() or 0

    query = (
        select(Event)
        .options(selectinload(Event.host), selectinload(Event.registrations))
        .where(*where_clauses)
        .order_by(Event.end_time.desc().nullslast())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    events = result.unique().scalars().all()

    return {"success": True, "data": [_build_event_response(e) for e in events], "total": total}


# ---------------------------------------------------------------------------
# Get single event by slug (public)
# ---------------------------------------------------------------------------

@router.get("/{slug}")
async def get_event(
    slug: str,
    user: Optional[User] = Depends(get_optional_user),
    agent: Optional[Agent] = Depends(get_optional_agent),
    db: AsyncSession = Depends(get_db),
):
    """Get event detail by slug or ID. Address masked if require_approval and not approved."""
    import uuid as _uuid
    try:
        event_uuid = _uuid.UUID(slug)
        where_clause = Event.id == event_uuid
    except ValueError:
        where_clause = Event.slug == slug

    result = await db.execute(
        select(Event)
        .options(
            selectinload(Event.host),
            selectinload(Event.custom_questions),
            selectinload(Event.registrations).selectinload(EventRegistration.user),
            selectinload(Event.cohosts).selectinload(EventCoHost.user),
        )
        .where(where_clause)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="活动不存在")

    should_mask = False
    if event.require_approval:
        caller_id = user.id if user else (agent.owner_id if agent else None)
        if caller_id and caller_id == event.host_id:
            should_mask = False
        elif caller_id:
            approved = any(
                r.user_id == caller_id and r.status == "approved"
                for r in (event.registrations or [])
            )
            should_mask = not approved
        else:
            should_mask = True

    return {"success": True, "data": _build_event_response(event, mask_address=should_mask)}


# ---------------------------------------------------------------------------
# Create event (dual auth: human user or agent)
# ---------------------------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_event(
    data: EventCreate,
    agent: Optional[Agent] = Depends(get_optional_agent),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new event (draft). Supports human (JWT) or agent (Bearer) auth."""
    if not user and not agent:
        raise HTTPException(status_code=401, detail="请先登录或使用 Agent API Key 认证")

    host_id = user.id if user else agent.owner_id
    assigner_id = user.id if user else agent.owner_id

    slug = await _ensure_unique_slug(db, _slugify(data.title))

    event = Event(
        title=data.title,
        slug=slug,
        description=data.description,
        cover_image_url=data.cover_image_url,
        event_type=data.event_type,
        location_name=data.location_name,
        location_address=data.location_address,
        online_url=data.online_url,
        start_time=data.start_time,
        end_time=data.end_time,
        timezone=data.timezone,
        capacity=data.capacity,
        registration_deadline=data.registration_deadline,
        visibility=data.visibility,
        require_approval=data.require_approval,
        notify_on_register=data.notify_on_register,
        theme=data.theme or {},
        host_id=host_id,
        approval_rules=data.approval_rules,
        status="draft",
    )
    db.add(event)
    await db.flush()

    if data.custom_questions:
        for i, q in enumerate(data.custom_questions):
            db.add(EventCustomQuestion(
                event_id=event.id,
                question_text=q.question_text,
                question_type=q.question_type,
                options=q.options,
                is_required=q.is_required,
                sort_order=i,
            ))

    if data.staff_agents:
        for sa in data.staff_agents:
            agent_result = await db.execute(
                select(Agent).where(Agent.name == sa.agent_name, Agent.is_active == True)
            )
            found_agent = agent_result.scalar_one_or_none()
            if found_agent:
                db.add(EventStaff(
                    event_id=event.id,
                    agent_id=found_agent.id,
                    role=sa.role,
                    permissions=sa.permissions,
                    assigned_by=assigner_id,
                ))

    await db.commit()

    result = await db.execute(
        select(Event)
        .options(selectinload(Event.host), selectinload(Event.custom_questions), selectinload(Event.registrations))
        .where(Event.id == event.id)
    )
    event = result.scalar_one()

    return {"success": True, "data": _build_event_response(event)}


# ---------------------------------------------------------------------------
# Update event
# ---------------------------------------------------------------------------

@router.put("/{event_id}")
async def update_event(
    event_id: str,
    data: EventUpdate,
    agent: Optional[Agent] = Depends(get_optional_agent),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Update event (host only). Supports human or agent auth."""
    if not user and not agent:
        raise HTTPException(status_code=401, detail="请先登录或使用 Agent API Key 认证")

    result = await db.execute(
        select(Event).options(selectinload(Event.host)).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="活动不存在")

    caller_id = user.id if user else agent.owner_id
    if event.host_id != caller_id:
        raise HTTPException(status_code=403, detail="无权修改此活动")

    update_data = data.model_dump(exclude_unset=True)
    new_questions = update_data.pop("custom_questions", None)

    for field, value in update_data.items():
        setattr(event, field, value)

    if new_questions is not None:
        await db.execute(
            select(EventCustomQuestion).where(EventCustomQuestion.event_id == event.id)
        )
        from sqlalchemy import delete
        await db.execute(delete(EventCustomQuestion).where(EventCustomQuestion.event_id == event.id))
        for i, q in enumerate(new_questions):
            db.add(EventCustomQuestion(
                event_id=event.id,
                question_text=q["question_text"],
                question_type=q.get("question_type", "text"),
                options=q.get("options"),
                is_required=q.get("is_required", False),
                sort_order=i,
            ))

    await db.flush()

    result2 = await db.execute(
        select(Event)
        .options(selectinload(Event.host), selectinload(Event.custom_questions), selectinload(Event.registrations))
        .where(Event.id == event.id)
    )
    event = result2.scalar_one()

    return {"success": True, "data": _build_event_response(event)}


# ---------------------------------------------------------------------------
# Clone event
# ---------------------------------------------------------------------------

@router.post("/{event_id}/clone", status_code=status.HTTP_201_CREATED)
async def clone_event(
    event_id: str,
    user: Optional[User] = Depends(get_optional_user),
    agent: Optional[Agent] = Depends(get_optional_agent),
    db: AsyncSession = Depends(get_db),
):
    """Clone an existing event as a new draft. Copies settings and questions, not registrations."""
    if not user and not agent:
        raise HTTPException(status_code=401, detail="请先登录")

    result = await db.execute(
        select(Event)
        .options(selectinload(Event.custom_questions))
        .where(Event.id == event_id)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="活动不存在")

    caller_id = user.id if user else agent.owner_id
    if source.host_id != caller_id:
        raise HTTPException(status_code=403, detail="只能克隆自己创建的活动")

    new_slug = await _ensure_unique_slug(db, _slugify(source.title))

    clone = Event(
        title=source.title,
        slug=new_slug,
        description=source.description,
        cover_image_url=source.cover_image_url,
        event_type=source.event_type,
        location_name=source.location_name,
        location_address=source.location_address,
        online_url=source.online_url,
        start_time=source.start_time,
        end_time=source.end_time,
        timezone=source.timezone,
        capacity=source.capacity,
        registration_deadline=None,
        visibility=source.visibility,
        require_approval=source.require_approval,
        notify_on_register=source.notify_on_register,
        theme=source.theme or {},
        host_id=caller_id,
        approval_rules=source.approval_rules,
        status="draft",
    )
    db.add(clone)
    await db.flush()

    if source.custom_questions:
        for i, q in enumerate(source.custom_questions):
            db.add(EventCustomQuestion(
                event_id=clone.id,
                question_text=q.question_text,
                question_type=q.question_type,
                options=q.options,
                is_required=q.is_required,
                sort_order=i,
            ))

    await db.commit()

    result2 = await db.execute(
        select(Event)
        .options(selectinload(Event.host), selectinload(Event.custom_questions), selectinload(Event.registrations))
        .where(Event.id == clone.id)
    )
    clone = result2.scalar_one()

    return {"success": True, "data": _build_event_response(clone)}


# ---------------------------------------------------------------------------
# Publish / Cancel / Complete
# ---------------------------------------------------------------------------

@router.post("/{event_id}/publish")
async def publish_event(
    event_id: str,
    authorization: Optional[str] = Header(None),
    agent: Optional[Agent] = Depends(get_optional_agent),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Publish a draft event. Supports both human (JWT) and agent (Bearer) auth."""
    if not user and not agent:
        raise HTTPException(status_code=401, detail="请先登录或使用 Agent API Key 认证")

    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="活动不存在")

    caller_id = user.id if user else (agent.owner_id if agent else None)
    if event.host_id != caller_id:
        raise HTTPException(status_code=403, detail="无权操作此活动")
    if event.status != "draft":
        raise HTTPException(status_code=400, detail=f"当前状态 {event.status} 不能发布")

    event.status = "published"

    agent_api_key = None
    if agent and authorization:
        parts = authorization.split()
        if len(parts) == 2:
            agent_api_key = parts[1]

    try:
        circle_id = await _create_event_circle(
            event_title=event.title,
            event_description=event.description,
            event_slug=event.slug,
            agent_api_key=agent_api_key,
        )
        if circle_id:
            event.circle_id = circle_id
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Circle creation failed for event {event_id}: {e}")

    return {"success": True, "data": {"id": str(event.id), "status": event.status, "circle_id": str(event.circle_id) if event.circle_id else None}}


@router.post("/{event_id}/cancel")
async def cancel_event(
    event_id: str,
    agent: Optional[Agent] = Depends(get_optional_agent),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an event. Supports human or agent auth."""
    if not user and not agent:
        raise HTTPException(status_code=401, detail="请先登录或使用 Agent API Key 认证")

    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="活动不存在")

    caller_id = user.id if user else agent.owner_id
    if event.host_id != caller_id:
        raise HTTPException(status_code=403, detail="无权操作此活动")

    event.status = "cancelled"
    return {"success": True, "data": {"id": str(event.id), "status": event.status}}


@router.delete("/{event_id}")
async def delete_event(
    event_id: str,
    agent: Optional[Agent] = Depends(get_optional_agent),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently delete a cancelled/draft event and all related data."""
    if not user and not agent:
        raise HTTPException(status_code=401, detail="请先登录或使用 Agent API Key 认证")

    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="活动不存在")

    caller_id = user.id if user else agent.owner_id
    if event.host_id != caller_id:
        raise HTTPException(status_code=403, detail="无权操作此活动")
    if event.status not in ("draft", "cancelled"):
        raise HTTPException(status_code=400, detail="只能删除草稿或已取消的活动")

    from sqlalchemy import delete
    # Delete in FK-dependency order: logs → blasts → winners → rankings → registrations → questions → staff → event
    blast_ids = select(EventBlast.id).where(EventBlast.event_id == event.id)
    reg_ids = select(EventRegistration.id).where(EventRegistration.event_id == event.id)
    await db.execute(delete(EventBlastLog).where(EventBlastLog.blast_id.in_(blast_ids)))
    await db.execute(delete(EventBlast).where(EventBlast.event_id == event.id))
    await db.execute(delete(EventWinner).where(EventWinner.registration_id.in_(reg_ids)))
    await db.execute(delete(EventRanking).where(EventRanking.event_id == event.id))
    await db.execute(delete(EventRegistration).where(EventRegistration.event_id == event.id))
    await db.execute(delete(EventCustomQuestion).where(EventCustomQuestion.event_id == event.id))
    await db.execute(delete(EventStaff).where(EventStaff.event_id == event.id))
    await db.delete(event)

    return {"success": True, "message": "活动已彻底删除"}


# ---------------------------------------------------------------------------
# Register for an event (dual auth: user or agent)
# ---------------------------------------------------------------------------

@router.post("/{slug}/register", status_code=status.HTTP_201_CREATED)
async def register_for_event(
    slug: str,
    data: RegisterRequest = RegisterRequest(),
    agent: Optional[Agent] = Depends(get_optional_agent),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Register for an event. Supports both human (JWT) and agent (Bearer key)."""
    if not agent and not user:
        raise HTTPException(status_code=401, detail="请先登录或使用 Agent API Key")

    # Resolve identity
    if agent:
        if not agent.is_claimed or not agent.owner:
            raise HTTPException(status_code=403, detail="Agent 尚未认领，无法报名")
        owner = agent.owner
        via = "agent_api"
    else:
        owner = user
        via = "web"

    # Load event
    result = await db.execute(
        select(Event)
        .options(selectinload(Event.registrations), selectinload(Event.custom_questions))
        .where(Event.slug == slug)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="活动不存在")
    if event.status != "published":
        raise HTTPException(status_code=400, detail="活动未发布或已结束")

    if event.registration_deadline:
        from datetime import datetime, timezone as tz
        if datetime.now(tz.utc) > event.registration_deadline:
            raise HTTPException(status_code=400, detail="报名已截止")

    # Check phone
    phone = owner.phone or (data.phone if data else None)
    if not phone:
        return {
            "success": False,
            "need_phone": True,
            "hint": "需要手机号接收活动通知。请补充手机号后重试。",
        }

    # Validate custom answers for required questions
    if event.custom_questions:
        required_ids = {str(q.id) for q in event.custom_questions if q.is_required}
        provided = data.custom_answers or {} if data else {}
        missing = required_ids - set(provided.keys())
        if missing:
            missing_texts = [q.question_text for q in event.custom_questions if str(q.id) in missing]
            raise HTTPException(
                status_code=422,
                detail=f"请填写必填问题：{', '.join(missing_texts)}",
            )

    # Check duplicate
    dup = await db.execute(
        select(EventRegistration).where(
            EventRegistration.event_id == event.id,
            EventRegistration.user_id == owner.id,
            EventRegistration.status.notin_(["cancelled", "declined"]),
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="已报名此活动")

    # Capacity check
    if event.capacity:
        active_count = len([r for r in event.registrations if r.status in ("approved", "pending")])
        if active_count >= event.capacity:
            reg_status = "waitlisted"
        else:
            reg_status = "pending" if event.require_approval else "approved"
    else:
        reg_status = "pending" if event.require_approval else "approved"

    reg = EventRegistration(
        event_id=event.id,
        user_id=owner.id,
        agent_id=agent.id if agent else None,
        status=reg_status,
        phone=phone,
        custom_answers=data.custom_answers if data else None,
        qr_code_token=generate_qr_token(),
        registered_via=via,
        approved_at=utc_now() if reg_status == "approved" else None,
    )
    db.add(reg)
    await db.flush()

    import logging
    _log = logging.getLogger(__name__)

    # Notify the registrant (confirmation)
    try:
        await _notify_registrant_confirmation(reg, event.title, reg_status, db)
    except Exception as e:
        _log.warning(f"Registration confirmation notification failed: {e}")

    # Notify the host (if opted in)
    if event.notify_on_register:
        try:
            await _notify_host_new_registration(event, owner, reg_status)
        except Exception as e:
            _log.warning(f"Host notification failed: {e}")

    return {
        "success": True,
        "data": {
            "registration_id": str(reg.id),
            "event_title": event.title,
            "status": reg_status,
            "qr_code_token": reg.qr_code_token,
            "qr_code_url": f"/checkin/{reg.qr_code_token}",
            "message": {
                "approved": "报名成功！",
                "pending": "报名已提交，等待主办方审批。",
                "waitlisted": "活动已满，您已加入候补名单。",
            }.get(reg_status, "报名已提交"),
        },
    }


# ---------------------------------------------------------------------------
# Check registration status
# ---------------------------------------------------------------------------

@router.get("/{slug}/registration")
async def get_registration(
    slug: str,
    agent: Optional[Agent] = Depends(get_optional_agent),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Check my registration status for an event."""
    if not agent and not user:
        raise HTTPException(status_code=401, detail="请先登录")

    owner_id = agent.owner_id if agent else user.id

    result = await db.execute(
        select(EventRegistration)
        .join(Event)
        .where(Event.slug == slug, EventRegistration.user_id == owner_id)
    )
    reg = result.scalar_one_or_none()
    if not reg:
        return {"success": True, "data": None, "registered": False}

    return {
        "success": True,
        "registered": True,
        "data": {
            "id": str(reg.id),
            "status": reg.status,
            "qr_code_token": reg.qr_code_token,
            "registered_via": reg.registered_via,
            "registered_at": reg.registered_at.isoformat(),
            "checked_in_at": reg.checked_in_at.isoformat() if reg.checked_in_at else None,
        },
    }


@router.delete("/{slug}/registration")
async def cancel_registration(
    slug: str,
    agent: Optional[Agent] = Depends(get_optional_agent),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel my registration."""
    if not agent and not user:
        raise HTTPException(status_code=401, detail="请先登录")

    owner_id = agent.owner_id if agent else user.id

    result = await db.execute(
        select(EventRegistration)
        .join(Event)
        .where(Event.slug == slug, EventRegistration.user_id == owner_id)
    )
    reg = result.scalar_one_or_none()
    if not reg:
        raise HTTPException(status_code=404, detail="未找到报名记录")
    if reg.status == "cancelled":
        raise HTTPException(status_code=400, detail="已取消")

    reg.status = "cancelled"
    return {"success": True, "message": "报名已取消"}


# ---------------------------------------------------------------------------
# AI Description generation
# ---------------------------------------------------------------------------

class GenerateDescRequest(BaseModel):
    title: str
    event_type: str = "in_person"
    location: Optional[str] = None
    start_time: Optional[str] = None
    existing_description: Optional[str] = None


@router.post("/generate-description")
async def generate_description(
    data: GenerateDescRequest,
    user: User = Depends(get_current_user),
):
    """Generate Markdown event description via AI."""
    result = await generate_event_description(
        title=data.title,
        event_type=data.event_type,
        location=data.location,
        start_time=data.start_time,
        existing_description=data.existing_description,
    )
    if result is None:
        raise HTTPException(status_code=500, detail="AI 描述生成失败，请稍后重试")
    return {"success": True, "description": result}


# ---------------------------------------------------------------------------
# Post-event Feedback
# ---------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    rating: int  # 1-5
    comment: Optional[str] = None

from app.models.event import EventFeedback


@router.post("/{slug}/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    slug: str,
    body: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit post-event feedback. Only approved registrants can leave feedback after event ends."""
    if body.rating < 1 or body.rating > 5:
        raise HTTPException(status_code=422, detail="评分 1-5")

    result = await db.execute(
        select(Event).options(selectinload(Event.registrations)).where(Event.slug == slug)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="活动不存在")
    if event.status not in ("completed",):
        raise HTTPException(status_code=400, detail="活动尚未结束，暂不可评价")

    reg = next(
        (r for r in event.registrations if r.user_id == user.id and r.status == "approved"),
        None,
    )
    if not reg:
        raise HTTPException(status_code=403, detail="仅已通过的参会者可以评价")

    existing = await db.execute(
        select(EventFeedback).where(EventFeedback.event_id == event.id, EventFeedback.user_id == user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="已提交过评价")

    fb = EventFeedback(event_id=event.id, user_id=user.id, rating=body.rating, comment=body.comment)
    db.add(fb)
    await db.flush()

    return {"success": True, "data": {"id": str(fb.id)}}


@router.get("/{slug}/feedback")
async def get_feedback(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all feedback for an event."""
    result = await db.execute(select(Event).where(Event.slug == slug))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="活动不存在")

    fb_result = await db.execute(
        select(EventFeedback)
        .options(selectinload(EventFeedback.user))
        .where(EventFeedback.event_id == event.id)
        .order_by(EventFeedback.created_at.desc())
    )
    feedbacks = fb_result.unique().scalars().all()

    avg_rating = 0.0
    if feedbacks:
        avg_rating = round(sum(f.rating for f in feedbacks) / len(feedbacks), 1)

    return {
        "success": True,
        "data": {
            "avg_rating": avg_rating,
            "count": len(feedbacks),
            "items": [
                {
                    "id": str(f.id),
                    "rating": f.rating,
                    "comment": f.comment,
                    "user": {
                        "nickname": f.user.nickname if f.user else None,
                        "avatar_url": f.user.avatar_url if f.user else None,
                    },
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in feedbacks
            ],
        },
    }


# ---------------------------------------------------------------------------
# Poster (share image with QR code)
# ---------------------------------------------------------------------------

@router.get("/{slug}/poster")
async def get_event_poster(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Generate a shareable poster image (PNG) with QR code."""
    import io
    import qrcode
    from PIL import Image, ImageDraw, ImageFont
    from fastapi.responses import StreamingResponse

    result = await db.execute(
        select(Event).options(selectinload(Event.host)).where(Event.slug == slug)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="活动不存在")

    W, H = 750, 1334
    canvas = Image.new("RGB", (W, H), "#ffffff")
    draw = ImageDraw.Draw(canvas)

    font_path = _find_cjk_font()
    font_title = ImageFont.truetype(font_path, 40) if font_path else ImageFont.load_default()
    font_body = ImageFont.truetype(font_path, 26) if font_path else ImageFont.load_default()
    font_small = ImageFont.truetype(font_path, 22) if font_path else ImageFont.load_default()

    cover_h = 450
    if event.cover_image_url:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                img_resp = await client.get(event.cover_image_url)
            if img_resp.status_code == 200:
                cover_img = Image.open(io.BytesIO(img_resp.content))
                cover_img = cover_img.resize((W, cover_h), Image.LANCZOS)
                canvas.paste(cover_img, (0, 0))
            else:
                _draw_gradient(draw, W, cover_h, event.id)
        except Exception:
            _draw_gradient(draw, W, cover_h, event.id)
    else:
        _draw_gradient(draw, W, cover_h, event.id)

    y = cover_h + 30
    _draw_text_wrapped(draw, event.title, 40, y, W - 80, font_title, "#1a1a1a")
    y += _text_height(draw, event.title, W - 80, font_title) + 20

    type_labels = {"in_person": "线下", "online": "线上", "hybrid": "混合"}
    if event.start_time:
        from datetime import datetime
        dt = event.start_time
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        date_str = dt.strftime("%Y年%m月%d日 %H:%M")
        draw.text((40, y), f"🗓  {date_str}", font=font_body, fill="#555555")
        y += 40

    if event.location_name:
        draw.text((40, y), f"📍  {event.location_name}", font=font_body, fill="#555555")
        y += 40

    draw.text((40, y), f"🏷  {type_labels.get(event.event_type, event.event_type)}", font=font_body, fill="#555555")
    y += 40

    if event.host:
        draw.text((40, y), f"主办：{event.host.nickname}", font=font_small, fill="#888888")
        y += 35

    from app.core.config import settings
    event_url = f"{settings.frontend_url}/e/{event.slug}"
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(event_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    qr_size = 220
    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
    qr_x = (W - qr_size) // 2
    qr_y = H - qr_size - 100
    canvas.paste(qr_img, (qr_x, qr_y))

    draw.text((0, qr_y + qr_size + 10), "扫码查看活动详情", font=font_small, fill="#888888")
    text_w = draw.textlength("扫码查看活动详情", font=font_small)
    draw.text(((W - text_w) / 2, qr_y + qr_size + 10), "扫码查看活动详情", font=font_small, fill="#888888")

    buf = io.BytesIO()
    canvas.save(buf, format="PNG", quality=95)
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png", headers={
        "Cache-Control": "public, max-age=300",
    })


def _find_cjk_font() -> Optional[str]:
    """Find a CJK font on the system."""
    import os
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _draw_gradient(draw, w: int, h: int, event_id):
    """Draw a gradient background."""
    gradients = [
        ((102, 126, 234), (118, 75, 162)),
        ((240, 147, 251), (245, 87, 108)),
        ((79, 172, 254), (0, 242, 254)),
        ((67, 233, 123), (56, 249, 215)),
        ((250, 112, 154), (254, 225, 64)),
        ((161, 140, 209), (251, 194, 235)),
    ]
    eid = str(event_id).replace("-", "")
    idx = int(eid[:8], 16) % len(gradients)
    c1, c2 = gradients[idx]
    for y in range(h):
        r = int(c1[0] + (c2[0] - c1[0]) * y / h)
        g = int(c1[1] + (c2[1] - c1[1]) * y / h)
        b = int(c1[2] + (c2[2] - c1[2]) * y / h)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def _draw_text_wrapped(draw, text: str, x: int, y: int, max_w: int, font, fill: str):
    """Draw text with word wrapping."""
    lines = []
    current = ""
    for char in text:
        test = current + char
        if draw.textlength(test, font=font) > max_w:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + 8


def _text_height(draw, text: str, max_w: int, font) -> int:
    """Calculate wrapped text height."""
    lines = 1
    current = ""
    for char in text:
        test = current + char
        if draw.textlength(test, font=font) > max_w:
            lines += 1
            current = char
        else:
            current = test
    return lines * (font.size + 8)
