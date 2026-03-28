from __future__ import annotations
import io
import os
from typing import Optional

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from settings import env


class S3Reports:
    @staticmethod
    def _client():
        region = env.str("AWS_REGION", "us-east-1")
        return boto3.client(
            "s3",
            region_name=region,
            config=Config(signature_version="s3v4"),
        )

    @staticmethod
    def enabled() -> bool:
        return env.bool("S3_ENABLED", False)

    @staticmethod
    def bucket() -> str:
        return env.str("REPORTS_BUCKET", "demo-reports-bucket")

    @staticmethod
    def prefix() -> str:
        p = env.str("REPORTS_PREFIX", "reports/")
        if p and not p.endswith("/"):
            p += "/"
        return p

    @classmethod
    def key_for(cls, tenant: str, date_str: str) -> str:
        # date_str expected YYYY-MM-DD
        return f"{cls.prefix()}{tenant}/{date_str}.pdf"

    @classmethod
    def upload_report(cls, tenant: str, date_str: str, data: bytes) -> str:
        """
        Upload report bytes to S3 if enabled; otherwise save locally under ./reports/{tenant}/{date}.pdf
        Returns the storage key or local path.
        """
        if cls.enabled():
            client = cls._client()
            key = cls.key_for(tenant, date_str)
            try:
                client.put_object(Bucket=cls.bucket(), Key=key, Body=io.BytesIO(data), ContentType="application/pdf")
            except (BotoCoreError, ClientError) as e:
                # Fallback to local save on error
                return cls._save_local(tenant, date_str, data)
            return key
        else:
            return cls._save_local(tenant, date_str, data)

    @staticmethod
    def _save_local(tenant: str, date_str: str, data: bytes) -> str:
        base = os.path.join(os.getcwd(), "reports", tenant)
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, f"{date_str}.pdf")
        with open(path, "wb") as f:
            f.write(data)
        return path

    @classmethod
    def get_presigned_url(cls, key_or_path: str, expires_seconds: int = 86400) -> Optional[str]:
        if cls.enabled():
            client = cls._client()
            try:
                url = client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": cls.bucket(), "Key": key_or_path},
                    ExpiresIn=expires_seconds,
                )
                return url
            except (BotoCoreError, ClientError):
                return None
        # Local file path cannot be presigned; return file:// URL for dev
        if os.path.exists(key_or_path):
            return f"file://{key_or_path}"
        return None

    @classmethod
    def get_bytes(cls, key: str) -> Optional[bytes]:
        """Fetch object bytes from S3 by key when S3 is enabled. Returns None on failure."""
        if not cls.enabled():
            return None
        client = cls._client()
        try:
            obj = client.get_object(Bucket=cls.bucket(), Key=key)
            body = obj.get("Body")
            if body is None:
                return None
            return body.read()
        except (BotoCoreError, ClientError):
            return None
