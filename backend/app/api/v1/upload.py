"""Image upload API — proxies to ClawdChat file API."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.models.clawdchat import User
from app.core.config import settings
from app.core.deps import get_current_user
from app.services.oss import upload_image, ALLOWED_IMAGE_TYPES

router = APIRouter()

MAX_SIZE = settings.image_max_size_mb * 1024 * 1024

_MAGIC_SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),  # RIFF....WEBP — checked with extra guard below
]


def _detect_mime(data: bytes) -> str | None:
    """Detect image MIME type from magic bytes, ignoring declared content-type."""
    for sig, mime in _MAGIC_SIGNATURES:
        if data[:len(sig)] == sig:
            if mime == "image/webp" and data[8:12] != b"WEBP":
                continue
            return mime
    return None


@router.post("/image")
async def upload_image_endpoint(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """Upload an image (cover, description embed). Returns {url}."""
    if not settings.events_bot_api_key:
        raise HTTPException(status_code=503, detail="图床未配置（缺少 EventsBot API Key）")

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"图片大小超过 {settings.image_max_size_mb}MB 限制",
        )

    content_type = _detect_mime(contents) or file.content_type or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的图片格式: {content_type}，支持 jpeg/png/gif/webp",
        )

    ext = ALLOWED_IMAGE_TYPES[content_type]
    filename = file.filename or "image.png"
    if not filename.lower().endswith(ext):
        base = filename.rsplit(".", 1)[0] if "." in filename else filename
        filename = f"{base}{ext}"

    try:
        url = await upload_image(contents, filename, content_type)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"success": True, "url": url}
