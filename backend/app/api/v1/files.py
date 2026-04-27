"""
LAYERS - File Proxy
Serves stored objects (avatars, etc.) from MinIO through the API.
This avoids requiring the mobile client to reach MinIO directly.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from minio.error import S3Error

from app.core.storage import get_object

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("/{path:path}")
async def serve_file(path: str):
    """Stream a stored object (avatar, etc.) from MinIO."""
    try:
        data, content_type = await get_object(path)
        return Response(content=data, media_type=content_type)
    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        logger.error(f"MinIO error serving {path}: {e}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Storage error")
    except Exception as e:
        logger.error(f"Unexpected error serving {path}: {e}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Storage unavailable")
