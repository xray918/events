"""Image upload via ClawdChat file API (proxy to ClawdChat's OSS)."""

import logging
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


async def upload_image(file_content: bytes, filename: str, content_type: str) -> str:
    """Upload image via ClawdChat file API, return public URL."""
    api_key = settings.events_bot_api_key
    if not api_key:
        raise RuntimeError("EVENTS_BOT_API_KEY 未配置，无法上传图片")

    base = settings.clawdchat_api_base.rstrip("/")
    url = f"{base}/files/upload"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (filename, file_content, content_type)},
        )

    if resp.status_code != 200:
        logger.error("ClawdChat file upload failed: %s %s", resp.status_code, resp.text[:300])
        raise RuntimeError(f"虾聊图床上传失败: {resp.status_code} {resp.text[:200]}")

    data = resp.json()
    image_url = data.get("url", "")
    logger.info("Image uploaded via ClawdChat: %s", image_url)
    return image_url
