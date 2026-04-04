"""
LAYERS - MinIO Storage Utility
Handles file uploads to MinIO (S3-compatible object storage).
"""

import io
import json
import uuid
import asyncio
import logging
from functools import partial

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


def _get_client() -> Minio:
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def _ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        logger.info(f"Created MinIO bucket: {bucket}")

    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"AWS": ["*"]},
            "Action": ["s3:GetObject"],
            "Resource": [f"arn:aws:s3:::{bucket}/*"],
        }],
    }
    client.set_bucket_policy(bucket, json.dumps(policy))


def _upload_bytes(data: bytes, object_name: str, content_type: str) -> str:
    """Synchronous upload — run in executor to avoid blocking the event loop."""
    client = _get_client()
    bucket = settings.minio_bucket_name
    _ensure_bucket(client, bucket)

    client.put_object(
        bucket_name=bucket,
        object_name=object_name,
        data=io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )

    return f"{settings.minio_public_url}/{bucket}/{object_name}"


async def upload_avatar(data: bytes, content_type: str) -> str:
    """
    Upload avatar bytes to MinIO and return the public URL.

    Args:
        data: Raw file bytes.
        content_type: MIME type (e.g. "image/jpeg").

    Returns:
        Public URL of the uploaded file.
    """
    ext = content_type.split("/")[-1].replace("jpeg", "jpg")
    object_name = f"avatars/{uuid.uuid4().hex}.{ext}"

    loop = asyncio.get_event_loop()
    url = await loop.run_in_executor(
        None, partial(_upload_bytes, data, object_name, content_type)
    )
    logger.info(f"Avatar uploaded: {object_name}")
    return url
