"""Authentication — phone + SMS code, Google OAuth (shared with ClawdChat users table)."""

import re
import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.clawdchat import User
from app.core.config import settings
from app.core.security import create_access_token, utc_now
from app.core.deps import get_current_user
from app.schemas.auth import PhoneSendCodeRequest, PhoneLoginRequest, LoginResponse
from app.services.verification import generate_code, store_code, verify_code, can_send
from app.services.sms import send_verification_code

logger = logging.getLogger(__name__)

router = APIRouter()

COOKIE_NAME = "events_token"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days

PHONE_RE = re.compile(r"^1[3-9]\d{9}$")


def _set_auth_cookie(response: Response, user_id: str):
    token = create_access_token({"sub": user_id})
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=COOKIE_MAX_AGE,
        samesite="lax",
        secure=settings.app_env == "production",
    )


# ---------------------------------------------------------------------------
# Phone + SMS verification code
# ---------------------------------------------------------------------------

@router.post("/phone/send-code")
async def phone_send_code(data: PhoneSendCodeRequest):
    """发送手机验证码"""
    phone = data.phone.strip()
    if not PHONE_RE.match(phone):
        raise HTTPException(status_code=400, detail="请输入有效的手机号")

    if not await can_send(phone):
        raise HTTPException(status_code=429, detail="发送过于频繁，请60秒后重试")

    code = generate_code()
    await store_code(phone, code)

    result = await send_verification_code(phone, code)
    if result.get("mock"):
        logger.info(f"[MOCK] 验证码 {phone}: {code}")
        return {"success": True, "message": "验证码已发送（测试模式）"}

    if not result.get("success"):
        logger.error(f"SMS send failed for {phone}: {result}")
        raise HTTPException(status_code=500, detail=f"短信发送失败: {result.get('error', '未知错误')}")

    logger.info(f"SMS sent to {phone}, request_id={result.get('request_id')}")
    return {"success": True, "message": "验证码已发送"}


@router.post("/phone/login", response_model=LoginResponse)
async def phone_login(
    data: PhoneLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """手机号 + 验证码登录（自动注册）"""
    phone = data.phone.strip()
    if not PHONE_RE.match(phone):
        raise HTTPException(status_code=400, detail="请输入有效的手机号")

    if not await verify_code(phone, data.code.strip()):
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if not user:
        user = User(phone=phone, nickname=f"用户{phone[-4:]}", last_login_at=utc_now())
        db.add(user)
        await db.flush()
    else:
        user.last_login_at = utc_now()

    await db.commit()

    _set_auth_cookie(response, str(user.id))

    return LoginResponse(
        success=True,
        message="登录成功",
        user={"id": str(user.id), "nickname": user.nickname, "avatar_url": user.avatar_url},
    )


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------

@router.get("/google/start")
async def google_start():
    """重定向到 Google 授权页"""
    from app.services.google import google_service
    auth_url = google_service.get_auth_url(state="login")
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    code: str = "",
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    """处理 Google OAuth 回调"""
    if not code:
        raise HTTPException(status_code=400, detail="缺少授权码")

    from app.services.google import google_service
    user_info = await google_service.authenticate(code)
    if not user_info:
        raise HTTPException(status_code=400, detail="Google 认证失败，请重试")

    google_id = user_info.get("id")
    email = user_info.get("email")
    name = user_info.get("name")
    picture = user_info.get("picture")

    if not google_id or not email:
        raise HTTPException(status_code=400, detail="无法获取 Google 用户信息")

    result = await db.execute(
        select(User).where(or_(User.google_id == google_id, User.email == email))
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            google_id=google_id,
            email=email,
            nickname=name or email.split("@")[0],
            avatar_url=picture,
            last_login_at=utc_now(),
        )
        db.add(user)
        await db.flush()
    else:
        user.last_login_at = utc_now()
        if not user.google_id:
            user.google_id = google_id
        if not user.email and email:
            user.email = email
        if not user.nickname and name:
            user.nickname = name
        if not user.avatar_url and picture:
            user.avatar_url = picture

    await db.commit()

    redirect = RedirectResponse(url=settings.frontend_url, status_code=302)
    _set_auth_cookie(redirect, str(user.id))
    return redirect


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return {
        "success": True,
        "data": {
            "id": str(user.id),
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
            "phone": user.phone,
            "email": user.email,
        },
    }


@router.post("/logout")
async def logout(response: Response):
    """退出登录"""
    response.delete_cookie(COOKIE_NAME)
    return {"success": True, "message": "已退出"}
