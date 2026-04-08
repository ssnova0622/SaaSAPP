"""
Central storage service.

Set  S3_ENABLED=true  in .env to route ALL file I/O to AWS S3.
Leave it false (default) to store files on the local disk.

Required env vars when S3_ENABLED=true:
  AWS_REGION         (default: us-east-1)
  UPLOADS_BUCKET     (default: demo-uploads-bucket)  — general uploads + product images
  UPLOADS_PREFIX     (default: uploads/)              — key prefix for general uploads
  REPORTS_BUCKET     (default: demo-reports-bucket)   — PDF reports
  REPORTS_PREFIX     (default: reports/)              — key prefix for reports

AWS credentials are read from the standard boto3 chain:
  AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN / IAM role …
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

# Supported product-image extensions and their MIME types
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
_IMAGE_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


class StorageService:
    """
    Single entry-point for all file storage operations.

    When S3_ENABLED=true  → upload/download from AWS S3.
    When S3_ENABLED=false → read/write local directories:
        uploads/           general uploads
        media_storage/     product images
        reports/           PDF reports
    """

    _s3_client = None  # lazy-initialised, shared across calls

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @classmethod
    def is_s3(cls) -> bool:
        """Return True when S3 storage is enabled via S3_ENABLED env var."""
        return env.bool("S3_ENABLED", False)

    @classmethod
    def _client(cls):
        """Return a cached boto3 S3 client (initialised once per process)."""
        if cls._s3_client is None:
            cls._s3_client = boto3.client(
                "s3",
                region_name=env.str("AWS_REGION", "us-east-1"),
                config=Config(signature_version="s3v4"),
            )
        return cls._s3_client

    @classmethod
    def _uploads_bucket(cls) -> str:
        return env.str("UPLOADS_BUCKET", "demo-uploads-bucket")

    @classmethod
    def _reports_bucket(cls) -> str:
        return env.str("REPORTS_BUCKET", "demo-reports-bucket")

    @classmethod
    def _uploads_prefix(cls) -> str:
        p = env.str("UPLOADS_PREFIX", "uploads/")
        return p if p.endswith("/") else p + "/"

    @classmethod
    def _reports_prefix(cls) -> str:
        p = env.str("REPORTS_PREFIX", "reports/")
        return p if p.endswith("/") else p + "/"

    # ------------------------------------------------------------------
    # Low-level S3 primitives (private)
    # ------------------------------------------------------------------

    @classmethod
    def _s3_put(cls, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
        try:
            cls._client().put_object(
                Bucket=bucket, Key=key, Body=io.BytesIO(data), ContentType=content_type
            )
            return True
        except (BotoCoreError, ClientError):
            return False

    @classmethod
    def _s3_get(cls, bucket: str, key: str) -> Optional[bytes]:
        try:
            obj = cls._client().get_object(Bucket=bucket, Key=key)
            body = obj.get("Body")
            return body.read() if body else None
        except (BotoCoreError, ClientError):
            return None

    @classmethod
    def _s3_presign(cls, bucket: str, key: str, expires: int = 86400) -> Optional[str]:
        try:
            return cls._client().generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires,
            )
        except (BotoCoreError, ClientError):
            return None

    # ------------------------------------------------------------------
    # Low-level local primitive (private)
    # ------------------------------------------------------------------

    @staticmethod
    def _local_write(directory: str, filename: str, data: bytes) -> str:
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, filename)
        with open(path, "wb") as fh:
            fh.write(data)
        return path

    # ------------------------------------------------------------------
    # General file uploads  (documents, promotions, etc.)
    # Stored URL: /v1/uploads/{tenant}/{uuid}{ext}
    # S3 key:     {uploads_prefix}{tenant}/{uuid}{ext}
    # ------------------------------------------------------------------

    @classmethod
    def upload_file(cls, tenant: str, filename: str, data: bytes, content_type: Optional[str] = None) -> str:
        """
        Upload arbitrary file bytes.
        Returns an S3 key (when S3 is on) or a /v1/uploads/… path (local).
        Use get_upload_url() to resolve the stored value back to a URL.
        """
        ext = os.path.splitext(filename)[1]
        unique_name = f"{uuid.uuid4()}{ext}"

        if cls.is_s3():
            key = f"{cls._uploads_prefix()}{tenant}/{unique_name}"
            if cls._s3_put(cls._uploads_bucket(), key, data, content_type or "application/octet-stream"):
                return key  # S3 key — resolved to presigned URL on demand

        cls._local_write(os.path.join(os.getcwd(), "uploads", tenant), unique_name, data)
        return f"/v1/uploads/{tenant}/{unique_name}"

    @classmethod
    def get_upload_bytes(cls, key_or_path: str) -> Optional[bytes]:
        """
        Return raw bytes for a previously uploaded file.
        Accepts either an S3 key or a /v1/uploads/… path.
        """
        if cls.is_s3() and key_or_path and not key_or_path.startswith("/"):
            return cls._s3_get(cls._uploads_bucket(), key_or_path)

        # Derive local path from /v1/uploads/{tenant}/{filename}
        parts = key_or_path.strip("/").split("/")
        # Strip leading "v1" and "uploads" segments if present
        while parts and parts[0] in ("v1", "uploads"):
            parts.pop(0)
        if len(parts) >= 2:
            local = os.path.join(os.getcwd(), "uploads", *parts)
            if os.path.exists(local):
                with open(local, "rb") as fh:
                    return fh.read()
        return None

    @classmethod
    def get_upload_url(cls, key_or_path: str) -> str:
        """
        Resolve a stored upload reference to a usable URL.
        S3 mode returns a short-lived presigned URL; local mode returns the /v1/uploads/… path.
        """
        if key_or_path.startswith("/v1/uploads/"):
            return key_or_path
        if cls.is_s3() and key_or_path and not key_or_path.startswith("/"):
            url = cls._s3_presign(cls._uploads_bucket(), key_or_path)
            if url:
                return url
        return key_or_path

    # ------------------------------------------------------------------
    # Product / media images
    # Stored URL: /v1/media/{tenant}/{uuid}{ext}  (both local and S3)
    # S3 key:     media_storage/{tenant}/{uuid}{ext}
    # ------------------------------------------------------------------

    @classmethod
    def upload_media(cls, tenant: str, filename: str, data: bytes, content_type: Optional[str] = None) -> str:
        """
        Upload a product image.
        Returns /v1/media/{tenant}/{filename} in both S3 and local mode so the
        serving endpoint (GET /v1/media/{tenant}/{filename}) always resolves correctly.
        """
        ext = (os.path.splitext(filename)[1] or "").lower()
        if ext not in _IMAGE_EXTS:
            ext = ".jpg"
        unique_name = f"{uuid.uuid4().hex}{ext}"

        if cls.is_s3():
            key = f"media_storage/{tenant}/{unique_name}"
            ct = _IMAGE_MIME.get(ext, "image/jpeg")
            if cls._s3_put(cls._uploads_bucket(), key, data, content_type or ct):
                return f"/v1/media/{tenant}/{unique_name}"

        cls._local_write(os.path.join(os.getcwd(), "media_storage", tenant), unique_name, data)
        return f"/v1/media/{tenant}/{unique_name}"

    @classmethod
    def get_media_bytes(cls, url_path: str) -> Optional[bytes]:
        """
        Fetch image bytes for a /v1/media/{tenant}/{filename} path.
        Checks local disk first (covers local mode and any locally cached files),
        then falls back to S3 when S3 is enabled.
        """
        if not url_path or not url_path.startswith("/v1/media/"):
            return None
        parts = url_path.strip().split("/")
        if len(parts) < 5:
            return None
        tenant, filename = parts[3], parts[4]

        local_path = os.path.join(os.getcwd(), "media_storage", tenant, filename)
        if os.path.exists(local_path):
            with open(local_path, "rb") as fh:
                return fh.read()

        if cls.is_s3():
            return cls._s3_get(cls._uploads_bucket(), f"media_storage/{tenant}/{filename}")

        return None

    # ------------------------------------------------------------------
    # Report PDFs
    # S3 key:   {reports_prefix}{tenant}/{date_str}.pdf
    # Local path: ./reports/{tenant}/{date_str}.pdf  (absolute os path)
    # ------------------------------------------------------------------

    @classmethod
    def upload_report(cls, tenant: str, date_str: str, data: bytes) -> str:
        """
        Persist a PDF report.
        Returns the S3 key (when S3 is on) or the absolute local file path.
        """
        if cls.is_s3():
            key = f"{cls._reports_prefix()}{tenant}/{date_str}.pdf"
            if cls._s3_put(cls._reports_bucket(), key, data, "application/pdf"):
                return key

        return cls._local_write(
            os.path.join(os.getcwd(), "reports", tenant),
            f"{date_str}.pdf",
            data,
        )

    @classmethod
    def get_report_bytes(cls, key_or_path: str) -> Optional[bytes]:
        """
        Fetch PDF bytes.  key_or_path is either an S3 key (no leading /) or a local file path.
        """
        if not key_or_path:
            return None
        if cls.is_s3() and not key_or_path.startswith("/") and not key_or_path.startswith("file://"):
            data = cls._s3_get(cls._reports_bucket(), key_or_path)
            if data is not None:
                return data

        path = key_or_path.removeprefix("file://")
        if os.path.exists(path):
            with open(path, "rb") as fh:
                return fh.read()
        return None

    @classmethod
    def get_report_url(cls, key_or_path: str, expires: int = 86400) -> Optional[str]:
        """
        Return a URL to access the PDF.
        S3 mode: presigned URL (valid for `expires` seconds).
        Local mode: file:// path (for internal email attachment; not HTTP-accessible).
        """
        if not key_or_path:
            return None
        if cls.is_s3() and not key_or_path.startswith("/") and not key_or_path.startswith("file://"):
            return cls._s3_presign(cls._reports_bucket(), key_or_path, expires)

        path = key_or_path.removeprefix("file://")
        return f"file://{path}" if os.path.exists(path) else None
