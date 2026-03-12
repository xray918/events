"""Image upload API."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.clawdchat import User
from app.core.config import settings
from app.core.deps import get_current_user
from app.services.oss import upload_image, ALLOWED_IMAGE_TYPES

router = APIRouter()

MAX_SIZE = settings.image_max_size_mb * 1024 * 1024


@router.post("/image")
async def upload_image_endpoint(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """Upload an image (cover, description embed). Returns {url}."""
    if not settings.alibaba_cloud_access_key_id:
        raise HTTPException(status_code=503, detail="OSS 未配置")

    content_type = file.content_type or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的图片格式: {content_type}，支持 jpeg/png/gif/webp",
        )

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"图片大小超过 {settings.image_max_size_mb}MB 限制",
        )

    file_ext = ALLOWED_IMAGE_TYPES[content_type]
    url = upload_image(contents, file_ext, str(user.id))

    return {"success": True, "url": url}
