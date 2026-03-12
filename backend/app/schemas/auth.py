"""Auth schemas."""

from typing import Optional
from pydantic import BaseModel


class PhoneSendCodeRequest(BaseModel):
    phone: str


class PhoneLoginRequest(BaseModel):
    phone: str
    code: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict] = None
