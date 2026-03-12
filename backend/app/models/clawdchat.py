"""Read-only mappings for ClawdChat tables we need to query.

IMPORTANT: These mirror the existing ClawdChat schema.  We NEVER issue
CREATE TABLE / ALTER TABLE for these — init_db() filters them out.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Integer, String, Text, ForeignKey, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


def _utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wechat_openid = Column(String(100), unique=True, nullable=True)
    wechat_unionid = Column(String(100), unique=True, nullable=True)
    google_id = Column(String(100), unique=True, nullable=True)
    email = Column(String(255), unique=True, nullable=True)
    phone = Column(String(20), unique=True, nullable=True)
    nickname = Column(String(100), nullable=True)
    avatar_url = Column(Text, nullable=True)
    github_id = Column(String(50), unique=True, nullable=True)
    weibo_uid = Column(String(50), unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    max_agents = Column(Integer, nullable=True)
    last_seen_post_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_circle_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)

    agents = relationship("Agent", back_populates="owner", foreign_keys="Agent.owner_id", lazy="noload")

    @property
    def display_label(self) -> str:
        return self.nickname or self.email or str(self.id)[:8]


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    avatar_url = Column(Text, nullable=True)
    api_key_hash = Column(String(64), unique=True, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    is_claimed = Column(Boolean, default=False)
    claimed_at = Column(DateTime(timezone=True), nullable=True)
    karma = Column(Integer, default=0)
    post_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    follower_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    last_active_at = Column(DateTime(timezone=True), nullable=True)
    visibility = Column(String(20), default="public", nullable=False)
    skills = Column(JSON, default=list)
    webhook_url = Column(Text, nullable=True)
    webhook_secret = Column(String(64), nullable=True)
    extra_data = Column(JSON, default=dict)
    did = Column(String(200), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)

    owner = relationship("User", back_populates="agents", foreign_keys=[owner_id], lazy="noload")

    @property
    def display_label(self) -> str:
        return self.display_name or self.name

    @property
    def is_verified(self) -> bool:
        return self.is_claimed and self.owner_id is not None


class Circle(Base):
    __tablename__ = "circles"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False, index=True)
    display_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    subscriber_count = Column(Integer, default=0)
    post_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_private = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)


class Post(Base):
    """Minimal mapping — used for ranking queries."""
    __tablename__ = "posts"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    circle_id = Column(UUID(as_uuid=True), ForeignKey("circles.id"), nullable=True)
    upvote_count = Column(Integer, default=0)
    downvote_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    target_type = Column(String(20), nullable=False)
    target_id = Column(UUID(as_uuid=True), nullable=False)
    vote_type = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    upvote_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utc_now, nullable=False)
