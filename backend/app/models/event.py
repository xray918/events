"""Events system models — all tables prefixed with event_ or sms_."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


def _utc_now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------

class Event(Base):
    __tablename__ = "event_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    cover_image_url = Column(Text, nullable=True)

    event_type = Column(String(20), default="in_person", nullable=False)  # in_person / online / hybrid
    location_name = Column(String(200), nullable=True)
    location_address = Column(Text, nullable=True)
    online_url = Column(Text, nullable=True)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    timezone = Column(String(50), default="Asia/Shanghai", nullable=False)

    capacity = Column(Integer, nullable=True)           # display-only: expected attendees / venue size
    registration_limit = Column(Integer, nullable=True) # NULL = unlimited; controls when new registrations become waitlisted
    registration_deadline = Column(DateTime(timezone=True), nullable=True)  # NULL = no deadline
    visibility = Column(String(20), default="public", nullable=False)  # public / private
    require_approval = Column(Boolean, default=False, nullable=False)
    notify_on_register = Column(Boolean, default=False, nullable=False)  # notify host when someone registers
    allow_self_checkin = Column(Boolean, default=True, nullable=False)  # False = only host/staff can scan to check in
    status = Column(String(20), default="draft", nullable=False, index=True)  # draft / published / offline / cancelled / completed

    theme = Column(JSON, default=dict)  # colors, style
    host_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    organizer_name = Column(String(200), nullable=True)  # custom display name for the organizer

    circle_id = Column(UUID(as_uuid=True), nullable=True)  # linked ClawdChat Circle (created via API)
    circle_name = Column(String(200), nullable=True)  # ClawdChat circle slug name (for API calls)
    clawdchat_post_id = Column(UUID(as_uuid=True), nullable=True)  # announce post ID for syncing edits
    checkin_key = Column(String(64), nullable=True, unique=True, index=True)  # shared key for staff check-in page (no login required)
    approval_rules = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)

    # Relationships (all lazy="noload" to avoid greenlet issues in async context)
    host = relationship("User", foreign_keys=[host_id], lazy="noload")
    custom_questions = relationship("EventCustomQuestion", back_populates="event", cascade="all, delete-orphan", order_by="EventCustomQuestion.sort_order", lazy="noload")
    registrations = relationship("EventRegistration", back_populates="event", cascade="all, delete-orphan", lazy="noload")
    staff_agents = relationship("EventStaff", back_populates="event", cascade="all, delete-orphan", lazy="noload")
    blasts = relationship("EventBlast", back_populates="event", cascade="all, delete-orphan", lazy="noload")
    cohosts = relationship("EventCoHost", back_populates="event", cascade="all, delete-orphan", order_by="EventCoHost.display_order", lazy="noload")

    @property
    def is_published(self) -> bool:
        return self.status == "published"

    @property
    def registration_count(self) -> int:
        return len([r for r in self.registrations if r.status in ("approved", "pending")])


# ---------------------------------------------------------------------------
# Custom Questions
# ---------------------------------------------------------------------------

class EventCustomQuestion(Base):
    __tablename__ = "event_custom_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("event_events.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(String(500), nullable=False)
    question_type = Column(String(20), default="text", nullable=False)  # text / select / multiselect
    options = Column(JSON, nullable=True)
    is_required = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    event = relationship("Event", back_populates="custom_questions", lazy="noload")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class EventRegistration(Base):
    __tablename__ = "event_registrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("event_events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True, index=True)

    status = Column(String(20), default="pending", nullable=False, index=True)  # pending / approved / declined / waitlisted / cancelled
    phone = Column(String(20), nullable=True)
    custom_answers = Column(JSON, nullable=True)
    qr_code_token = Column(String(64), unique=True, nullable=False, index=True)

    registered_via = Column(String(20), default="web", nullable=False)  # web / agent_api
    approved_by = Column(UUID(as_uuid=True), nullable=True)  # user_id or agent_id of approver

    registered_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    checked_in_at = Column(DateTime(timezone=True), nullable=True)

    event = relationship("Event", back_populates="registrations", lazy="noload")
    user = relationship("User", foreign_keys=[user_id], lazy="noload")
    agent = relationship("Agent", foreign_keys=[agent_id], lazy="noload")


# ---------------------------------------------------------------------------
# Staff Agent
# ---------------------------------------------------------------------------

class EventStaff(Base):
    __tablename__ = "event_staff"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("event_events.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    role = Column(String(20), default="staff", nullable=False)  # staff / moderator
    permissions = Column(JSON, default=lambda: ["all"])  # approve, notify, rank, all
    assigned_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)

    event = relationship("Event", back_populates="staff_agents", lazy="noload")
    agent = relationship("Agent", foreign_keys=[agent_id], lazy="noload")


# ---------------------------------------------------------------------------
# Co-Hosts
# ---------------------------------------------------------------------------

class EventCoHost(Base):
    __tablename__ = "event_cohosts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("event_events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)

    event = relationship("Event", back_populates="cohosts", lazy="noload")
    user = relationship("User", foreign_keys=[user_id], lazy="noload")


# ---------------------------------------------------------------------------
# Ranking (snapshot of Circle engagement)
# ---------------------------------------------------------------------------

class EventRanking(Base):
    __tablename__ = "event_rankings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("event_events.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    post_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    likes_received = Column(Integer, default=0)
    score = Column(Integer, default=0)
    rank = Column(Integer, nullable=True)
    snapshot_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)

    agent = relationship("Agent", foreign_keys=[agent_id], lazy="noload")


# ---------------------------------------------------------------------------
# Winners
# ---------------------------------------------------------------------------

class EventWinner(Base):
    __tablename__ = "event_winners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("event_events.id", ondelete="CASCADE"), nullable=False, index=True)
    registration_id = Column(UUID(as_uuid=True), ForeignKey("event_registrations.id"), nullable=False)
    rank = Column(Integer, nullable=True)
    prize_name = Column(String(200), nullable=True)
    prize_description = Column(Text, nullable=True)
    confirmed_by = Column(UUID(as_uuid=True), nullable=True)  # staff agent or host
    notified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)


# ---------------------------------------------------------------------------
# Blasts
# ---------------------------------------------------------------------------

class EventBlast(Base):
    __tablename__ = "event_blasts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("event_events.id", ondelete="CASCADE"), nullable=False, index=True)
    subject = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    target_filter = Column(JSON, nullable=True)
    blast_type = Column(String(20), default="custom", nullable=False)  # notification / winner / reminder / custom
    channels = Column(JSON, default=lambda: ["sms", "a2a"])
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)

    event = relationship("Event", back_populates="blasts", lazy="noload")


class EventBlastLog(Base):
    __tablename__ = "event_blast_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blast_id = Column(UUID(as_uuid=True), ForeignKey("event_blasts.id", ondelete="CASCADE"), nullable=False, index=True)
    registration_id = Column(UUID(as_uuid=True), ForeignKey("event_registrations.id"), nullable=False)
    channel = Column(String(10), nullable=False)  # sms / a2a
    status = Column(String(20), default="pending", nullable=False)  # pending / sent / failed
    error = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Post-event Feedback
# ---------------------------------------------------------------------------

class EventFeedback(Base):
    __tablename__ = "event_feedbacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("event_events.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)

    event = relationship("Event", lazy="noload")
    user = relationship("User", foreign_keys=[user_id], lazy="noload")


# ---------------------------------------------------------------------------
# SMS Templates & Logs
# ---------------------------------------------------------------------------

class SmsTemplate(Base):
    __tablename__ = "sms_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    scene = Column(String(50), nullable=False, index=True)  # registration_confirm / approval / reminder / checkin / winner / custom
    template_code = Column(String(50), nullable=True)  # Alibaba Cloud template code
    template_content = Column(Text, nullable=True)
    template_params_schema = Column(JSON, nullable=True)
    aliyun_status = Column(String(20), default="pending_review", nullable=False)  # pending_review / approved / rejected
    is_preset = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)


class SmsLog(Base):
    __tablename__ = "sms_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(20), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("sms_templates.id"), nullable=True)
    template_params = Column(JSON, nullable=True)
    status = Column(String(20), default="sent", nullable=False)  # sent / failed
    aliyun_request_id = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)
