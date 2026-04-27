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


def _upload_bytes(data: bytes, object_name: str, content_type: str) -> None:
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


def _get_object_bytes(object_name: str) -> tuple[bytes, str]:
    """Synchronous MinIO object read — run in executor."""
    client = _get_client()
    bucket = settings.minio_bucket_name
    response = client.get_object(bucket, object_name)
    try:
        data = response.read()
        content_type = response.headers.get("Content-Type", "application/octet-stream")
    finally:
        response.close()
        response.release_conn()
    return data, content_type


async def upload_avatar(data: bytes, content_type: str) -> str:
    """
    Upload avatar bytes to MinIO and return the object name.

    Args:
        data: Raw file bytes.
        content_type: MIME type (e.g. "image/jpeg").

    Returns:
        Object name within the bucket (e.g. "avatars/abc123.jpg").
        The caller constructs the full URL based on the serving strategy.
    """
    ext = content_type.split("/")[-1].replace("jpeg", "jpg")
    object_name = f"avatars/{uuid.uuid4().hex}.{ext}"

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None, partial(_upload_bytes, data, object_name, content_type)
    )
    logger.info(f"Avatar uploaded: {object_name}")
    return object_name


async def get_object(object_name: str) -> tuple[bytes, str]:
    """Retrieve an object from MinIO. Returns (data, content_type)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(_get_object_bytes, object_name))
