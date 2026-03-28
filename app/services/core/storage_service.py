# app/services/core/storage_service.py
from __future__ import annotations

# ============================================================
# Imports
# ============================================================

import io
import os
import uuid
from typing import Optional

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from settings import env



# Normalize prefixes
if not REPORTS_PREFIX.endswith("/"):
    REPORTS_PREFIX += "/"
if not UPLOADS_PREFIX.endswith("/"):
    UPLOADS_PREFIX += "/"


# ============================================================
# Core Storage Service
# ============================================================

class CoreStorageService:
    """
    Unified storage service for:
    - Reports (PDFs)
    - File uploads (images, docs, etc.)
    Supports S3 and local fallback.
    """

    # --------------------------------------------------------
    # S3 Client
    # --------------------------------------------------------

    @staticmethod
    def _s3_client():
        return boto3.client(
            "s3",
            region_name=DEFAULT_REGION,
            config=Config(signature_version="s3v4"),
        )

    @staticmethod
    def is_s3_enabled() -> bool:
        return S3_ENABLED

    # --------------------------------------------------------
    # Key Builders
    # --------------------------------------------------------

    @staticmethod
    def _report_key(tenant: str, date_str: str) -> str:
        return f"{REPORTS_PREFIX}{tenant}/{date_str}.pdf"

    @staticmethod
    def _upload_key(tenant: str, filename: str) -> str:
        return f"{UPLOADS_PREFIX}{tenant}/{filename}"

    # --------------------------------------------------------
    # Local Paths
    # --------------------------------------------------------

    @staticmethod
    def _local_report_path(tenant: str, date_str: str) -> str:
        base = os.path.join(os.getcwd(), "reports", tenant)
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, f"{date_str}.pdf")

    @staticmethod
    def _local_upload_path(tenant: str, filename: str) -> str:
        base = os.path.join(os.getcwd(), "uploads", tenant)
        os.makedirs(base, exist_ok=True)
        return os.path.join(base, filename)

    # ============================================================
    # REPORTS
    # ============================================================

    @classmethod
    def upload_report(cls, tenant: str, date_str: str, data: bytes) -> str:
        """
        Upload a PDF report to S3 or local storage.
        Returns the S3 key or local file path.
        """
        if cls.is_s3_enabled():
            key = cls._report_key(tenant, date_str)
            try:
                cls._s3_client().put_object(
                    Bucket=REPORTS_BUCKET,
                    Key=key,
                    Body=io.BytesIO(data),
                    ContentType="application/pdf",
                )
                return key
            except (BotoCoreError, ClientError):
                pass  # fallback to local

        # Local fallback
        path = cls._local_report_path(tenant, date_str)
        with open(path, "wb") as f:
            f.write(data)
        return path

    @classmethod
    def get_report_presigned_url(cls, key_or_path: str, expires_seconds: int = 86400) -> Optional[str]:
        """
        Returns a presigned S3 URL or a file:// URL for local storage.
        """
        if cls.is_s3_enabled() and not key_or_path.startswith("/"):
            try:
                return cls._s3_client().generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": REPORTS_BUCKET, "Key": key_or_path},
                    ExpiresIn=expires_seconds,
                )
            except (BotoCoreError, ClientError):
                return None

        # Local file
        if os.path.exists(key_or_path):
            return f"file://{key_or_path}"

        return None

    @classmethod
    def get_report_bytes(cls, key: str) -> Optional[bytes]:
        """
        Fetch report bytes from S3.
        """
        if not cls.is_s3_enabled():
            return None

        try:
            obj = cls._s3_client().get_object(Bucket=REPORTS_BUCKET, Key=key)
            body = obj.get("Body")
            return body.read() if body else None
        except (BotoCoreError, ClientError):
            return None

    # ============================================================
    # UPLOADS
    # ============================================================

    @classmethod
    def upload_file(
            cls,
            tenant: str,
            filename: str,
            data: bytes,
            content_type: Optional[str] = None,
    ) -> str:
        """
        Upload a file (image, doc, etc.) to S3 or local storage.
        Returns the S3 key or local URL.
        """
        ext = os.path.splitext(filename)[1]
        unique_name = f"{uuid.uuid4()}{ext}"

        if cls.is_s3_enabled():
            key = cls._upload_key(tenant, unique_name)
            try:
                extra_args = {"ContentType": content_type} if content_type else {}
                cls._s3_client().put_object(
                    Bucket=UPLOADS_BUCKET,
                    Key=key,
                    Body=io.BytesIO(data),
                    **extra_args,
                )
                return key
            except (BotoCoreError, ClientError):
                pass  # fallback to local

        # Local fallback
        path = cls._local_upload_path(tenant, unique_name)
        with open(path, "wb") as f:
            f.write(data)

        # Local uploads return a public API path
        return f"/v1/uploads/{tenant}/{unique_name}"

    @classmethod
    def get_file_url(cls, tenant: str, key_or_path: str) -> str:
        """
        Returns a presigned S3 URL or a local path.
        """
        # Local upload path
        if key_or_path.startswith("/v1/uploads/"):
            return key_or_path

        # S3
        if cls.is_s3_enabled() and not key_or_path.startswith("/"):
            try:
                return cls._s3_client().generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": UPLOADS_BUCKET, "Key": key_or_path},
                    ExpiresIn=86400,
                )
            except (BotoCoreError, ClientError):
                pass

        # Local file path
        return key_or_path
