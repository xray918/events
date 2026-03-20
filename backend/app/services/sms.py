"""Alibaba Cloud SMS service."""

import json
import logging
import re
from typing import Optional

from app.core.config import settings

_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002702-\U000027B0"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "\U00002600-\U000026FF"
    "]+",
    flags=re.UNICODE,
)


def _strip_emoji(text: str) -> str:
    return _EMOJI_RE.sub("", text).strip()

logger = logging.getLogger(__name__)

_client = None


def _get_sms_client():
    global _client
    if _client is not None:
        return _client

    if not settings.alibaba_cloud_access_key_id:
        logger.warning("Alibaba Cloud SMS not configured")
        return None

    try:
        from alibabacloud_dysmsapi20170525.client import Client
        from alibabacloud_dysmsapi20170525 import models as sms_models
        from alibabacloud_tea_openapi import models as open_models

        config = open_models.Config(
            access_key_id=settings.alibaba_cloud_access_key_id,
            access_key_secret=settings.alibaba_cloud_access_key_secret,
            connect_timeout=10000,
            read_timeout=15000,
        )
        config.endpoint = "dysmsapi.aliyuncs.com"
        _client = Client(config)
        return _client
    except Exception as e:
        logger.error(f"Failed to init SMS client: {e}")
        return None


async def send_sms(
    phone: str,
    template_code: str,
    template_params: Optional[dict] = None,
) -> dict:
    """Send SMS via Alibaba Cloud."""
    client = _get_sms_client()
    if not client:
        logger.warning(f"SMS not sent (no client): phone={phone}")
        return {"success": False, "error": "SMS service not configured"}

    try:
        from alibabacloud_dysmsapi20170525 import models as sms_models

        clean_params = None
        if template_params:
            clean_params = {k: _strip_emoji(str(v)) for k, v in template_params.items()}

        request = sms_models.SendSmsRequest(
            phone_numbers=phone,
            sign_name=settings.sms_sign_name,
            template_code=template_code,
            template_param=json.dumps(clean_params) if clean_params else None,
        )
        response = client.send_sms(request)
        body = response.body

        if body.code == "OK":
            return {"success": True, "request_id": body.request_id}
        else:
            return {"success": False, "error": body.message, "code": body.code}
    except Exception as e:
        logger.error(f"SMS send failed: {e}")
        return {"success": False, "error": str(e)}


async def send_verification_code(phone: str, code: str) -> dict:
    """Send SMS verification code for login."""
    template_code = settings.sms_template_code
    if not template_code:
        logger.warning(f"SMS template not configured, code={code} for {phone}")
        return {"success": True, "mock": True, "code": code}

    return await send_sms(phone, template_code, {"code": code})
