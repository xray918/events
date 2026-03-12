"""Alibaba Cloud SMS service."""

import json
import logging
from typing import Optional

from app.core.config import settings

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

        request = sms_models.SendSmsRequest(
            phone_numbers=phone,
            sign_name=settings.sms_sign_name,
            template_code=template_code,
            template_param=json.dumps(template_params) if template_params else None,
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
