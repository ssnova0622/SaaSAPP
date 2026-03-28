"""
Product/media image storage: tenant-based folder (media_storage/{tenant}/) or S3 when enabled.
Stores only the URL/path in DB; image bytes are on disk or S3.
"""
from __future__ import annotations
import io
import os
import uuid
from typing import Optional

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from settings import env


# Use same S3 bucket as general uploads; prefix separates product media
MEDIA_PREFIX = "media_storage/"


class MediaStorage:
    """Store product images under media_storage/{tenant}/ (local) or S3 prefix media_storage/{tenant}/."""

    @staticmethod
    def _client():
        region = env.str("AWS_REGION", "us-east-1")
        return boto3.client(
            "s3",
            region_name=region,
            config=Config(signature_version="s3v4"),
        )

    @staticmethod
    def s3_enabled() -> bool:
        return env.bool("S3_ENABLED", False)

    @staticmethod
    def bucket() -> str:
        return env.str("UPLOADS_BUCKET", "demo-uploads-bucket")

    @classmethod
    def _key(cls, tenant: str, unique_name: str) -> str:
        return f"{MEDIA_PREFIX}{tenant}/{unique_name}"

    @classmethod
    def upload_media(cls, tenant: str, filename: str, data: bytes, content_type: Optional[str] = None) -> str:
        """
        Save image to media_storage/{tenant}/{uuid}.ext (local) or S3 with prefix media_storage/{tenant}/.
        Returns a URL path that can be stored in product.image_url: /v1/media/{tenant}/{unique_name}.
        """
        ext = (os.path.splitext(filename)[1] or "").lower()
        if ext not in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            ext = ".jpg"
        unique_name = f"{uuid.uuid4().hex}{ext}"

        if cls.s3_enabled():
            key = cls._key(tenant, unique_name)
            try:
                client = cls._client()
                extra = {"ContentType": content_type or "image/jpeg"}
                client.put_object(Bucket=cls.bucket(), Key=key, Body=io.BytesIO(data), **extra)
                return f"/v1/media/{tenant}/{unique_name}"
            except (BotoCoreError, ClientError):
                return cls._save_local(tenant, unique_name, data)
        return cls._save_local(tenant, unique_name, data)

    @staticmethod
    def _save_local(tenant: str, unique_name: str, data: bytes) -> str:
        base = os.path.join(os.getcwd(), "media_storage", tenant)
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, unique_name)
        with open(path, "wb") as f:
            f.write(data)
        return f"/v1/media/{tenant}/{unique_name}"

    @classmethod
    def resolve_to_path_or_key(cls, url_path: str) -> tuple[str, Optional[str]]:
        """
        Given a stored URL path like /v1/media/{tenant}/{filename}, return (local_path, s3_key).
        One of them will be set for serving.
        """
        if not url_path or not url_path.startswith("/v1/media/"):
            return ("", None)
        parts = url_path.strip().split("/")
        if len(parts) < 5:
            return ("", None)
        tenant, filename = parts[3], parts[4]
        local_path = os.path.join(os.getcwd(), "media_storage", tenant, filename)
        s3_key = f"{MEDIA_PREFIX}{tenant}/{filename}" if cls.s3_enabled() else None
        return (local_path, s3_key)

    @classmethod
    def get_bytes(cls, url_path: str) -> Optional[bytes]:
        """Read media bytes from local file or S3. Returns None if not found."""
        local_path, s3_key = cls.resolve_to_path_or_key(url_path)
        if local_path and os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read()
        if s3_key:
            try:
                client = cls._client()
                obj = client.get_object(Bucket=cls.bucket(), Key=s3_key)
                body = obj.get("Body")
                return body.read() if body else None
            except (BotoCoreError, ClientError):
                pass
        return None
