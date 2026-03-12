"""Image upload API — proxies to ClawdChat file API."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

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
    if not settings.events_bot_api_key:
        raise HTTPException(status_code=503, detail="图床未配置（缺少 EventsBot API Key）")

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

    filename = file.filename or "image.png"
    try:
        url = await upload_image(contents, filename, content_type)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"success": True, "url": url}
