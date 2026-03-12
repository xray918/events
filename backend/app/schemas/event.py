"""Event schemas."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------

class CustomQuestionCreate(BaseModel):
    question_text: str
    question_type: str = "text"
    options: Optional[list[str]] = None
    is_required: bool = False


class StaffAgentAssign(BaseModel):
    agent_name: str
    role: str = "staff"
    permissions: list[str] = Field(default_factory=lambda: ["all"])


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    event_type: str = "in_person"
    location_name: Optional[str] = None
    location_address: Optional[str] = None
    online_url: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    timezone: str = "Asia/Shanghai"
    capacity: Optional[int] = None
    registration_deadline: Optional[datetime] = None
    visibility: str = "public"
    require_approval: bool = False
    notify_on_register: bool = False
    theme: Optional[dict] = None
    custom_questions: Optional[list[CustomQuestionCreate]] = None
    staff_agents: Optional[list[StaffAgentAssign]] = None
    approval_rules: Optional[dict] = None


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    event_type: Optional[str] = None
    location_name: Optional[str] = None
    location_address: Optional[str] = None
    online_url: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    timezone: Optional[str] = None
    capacity: Optional[int] = None
    registration_deadline: Optional[datetime] = None
    visibility: Optional[str] = None
    require_approval: Optional[bool] = None
    notify_on_register: Optional[bool] = None
    theme: Optional[dict] = None
    approval_rules: Optional[dict] = None
    custom_questions: Optional[list[CustomQuestionCreate]] = None


class EventResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    event_type: str
    location_name: Optional[str] = None
    location_address: Optional[str] = None
    online_url: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    timezone: str
    capacity: Optional[int] = None
    visibility: str
    require_approval: bool
    status: str
    theme: Optional[dict] = None
    host: Optional[dict] = None
    circle_id: Optional[UUID] = None
    custom_questions: Optional[list[dict]] = None
    registration_count: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    success: bool = True
    data: list[EventResponse]
    total: int


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    custom_answers: Optional[dict[str, Any]] = None
    phone: Optional[str] = None  # agent can supply owner phone


class RegisterResponse(BaseModel):
    success: bool = True
    data: dict
