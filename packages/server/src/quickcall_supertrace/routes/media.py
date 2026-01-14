"""
Media serving API routes.

Handles storage and retrieval of images and other media files
uploaded as part of events.

Related: events.py (stores media references), main.py (mounts router)
"""

import base64
import hashlib
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

router = APIRouter(prefix="/api/media", tags=["media"])

# Media storage directory - configurable via environment variable
MEDIA_DIR = Path(os.environ.get("QUICKCALL_SUPERTRACE_MEDIA_DIR", "~/.quickcall-supertrace/media")).expanduser()


class ImageUpload(BaseModel):
    """Image upload payload."""

    base64: str
    media_type: str = "image/png"
    session_id: str


class ImageResponse(BaseModel):
    """Response after storing an image."""

    id: str
    url: str


def ensure_media_dir() -> Path:
    """Ensure media directory exists."""
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    return MEDIA_DIR


def get_extension(media_type: str) -> str:
    """Get file extension from MIME type."""
    extensions = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
    }
    return extensions.get(media_type, ".bin")


def store_image(base64_data: str, media_type: str, session_id: str) -> tuple[str, str]:
    """
    Store base64 image to disk.

    Returns (image_id, relative_url).
    """
    ensure_media_dir()

    # Decode base64
    try:
        image_bytes = base64.b64decode(base64_data)
    except Exception as e:
        raise ValueError(f"Invalid base64 data: {e}")

    # Generate unique ID from content hash
    content_hash = hashlib.sha256(image_bytes).hexdigest()[:16]
    ext = get_extension(media_type)
    image_id = f"{session_id[:8]}_{content_hash}{ext}"

    # Store file
    file_path = MEDIA_DIR / image_id
    if not file_path.exists():
        file_path.write_bytes(image_bytes)

    return image_id, f"/api/media/{image_id}"


def process_images_in_event(event_data: dict[str, Any], session_id: str) -> dict[str, Any]:
    """
    Process images in event data, storing them to disk and replacing
    base64 data with URLs.

    Returns modified event_data with image URLs.
    """
    images = event_data.get("images")
    if not images or not isinstance(images, list):
        return event_data

    processed_images = []
    for img in images:
        if not isinstance(img, dict):
            continue

        base64_data = img.get("base64")
        if not base64_data:
            processed_images.append(img)
            continue

        media_type = img.get("media_type", "image/png")

        try:
            image_id, url = store_image(base64_data, media_type, session_id)
            processed_images.append(
                {
                    "id": image_id,
                    "url": url,
                    "media_type": media_type,
                    "index": img.get("index", 0),
                    "source": img.get("source", "hook"),
                }
            )
        except ValueError:
            # If we can't decode, keep original (will be large in DB but functional)
            processed_images.append(img)

    return {**event_data, "images": processed_images}


@router.get("/{image_id}")
async def get_image(image_id: str) -> Response:
    """
    Serve a stored image by ID.

    Returns the image file with appropriate content type.
    """
    # Sanitize image_id to prevent path traversal
    safe_id = Path(image_id).name
    file_path = MEDIA_DIR / safe_id

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    # Determine content type from extension
    ext = file_path.suffix.lower()
    content_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }
    content_type = content_types.get(ext, "application/octet-stream")

    return FileResponse(file_path, media_type=content_type)


@router.post("")
async def upload_image(upload: ImageUpload) -> ImageResponse:
    """
    Upload an image directly via API.

    This is an alternative to embedding images in events.
    """
    try:
        image_id, url = store_image(upload.base64, upload.media_type, upload.session_id)
        return ImageResponse(id=image_id, url=url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
