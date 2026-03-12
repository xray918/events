"""Alibaba Cloud OSS upload service for Events (covers, description images)."""

import uuid
import logging
from datetime import datetime

import oss2

from app.core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def _get_bucket() -> oss2.Bucket:
    auth = oss2.Auth(
        settings.alibaba_cloud_access_key_id,
        settings.alibaba_cloud_access_key_secret,
    )
    return oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket_name)


def _build_url(key: str) -> str:
    return f"https://{settings.oss_bucket_name}.{settings.oss_endpoint}/{key}"


def upload_image(file_content: bytes, file_ext: str, owner_id: str) -> str:
    """Upload an image to OSS, return public URL."""
    bucket = _get_bucket()
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    uid = uuid.uuid4().hex[:8]
    key = f"{settings.oss_prefix}images/{owner_id}/{ts}_{uid}{file_ext}"
    bucket.put_object(key, file_content)
    url = _build_url(key)
    logger.info(f"Image uploaded: {key}")
    return url
