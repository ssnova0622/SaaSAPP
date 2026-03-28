from __future__ import annotations
import io
import os
import uuid
from typing import Optional

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from settings import env


class StorageUpload:
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
        return env.str("UPLOADS_BUCKET", "demo-uploads-bucket")

    @staticmethod
    def prefix() -> str:
        p = env.str("UPLOADS_PREFIX", "uploads/")
        if p and not p.endswith("/"):
            p += "/"
        return p

    @classmethod
    def upload_file(cls, tenant: str, filename: str, data: bytes, content_type: Optional[str] = None) -> str:
        """
        Upload file bytes to S3 if enabled; otherwise save locally under ./uploads/{tenant}/{uuid}_{filename}
        Returns a URL or path that can be used to access the file.
        """
        ext = os.path.splitext(filename)[1]
        unique_name = f"{uuid.uuid4()}{ext}"

        if cls.enabled():
            client = cls._client()
            key = f"{cls.prefix()}{tenant}/{unique_name}"
            try:
                extra_args = {}
                if content_type:
                    extra_args["ContentType"] = content_type
                client.put_object(Bucket=cls.bucket(), Key=key, Body=io.BytesIO(data), **extra_args)
                # In a real app, we might return a public URL or a presigned URL later.
                # For now, we return the key or a simulated URL.
                return key
            except (BotoCoreError, ClientError):
                return cls._save_local(tenant, unique_name, data)
        else:
            return cls._save_local(tenant, unique_name, data)

    @staticmethod
    def _save_local(tenant: str, unique_name: str, data: bytes) -> str:
        base = os.path.join(os.getcwd(), "uploads", tenant)
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, unique_name)
        with open(path, "wb") as f:
            f.write(data)
        # Return a relative path or a way to access it via an endpoint
        return f"/v1/uploads/{tenant}/{unique_name}"

    @classmethod
    def get_file_url(cls, tenant: str, key_or_path: str) -> str:
        if key_or_path.startswith("/v1/uploads/"):
            return key_or_path

        if cls.enabled() and not key_or_path.startswith("/"):
            try:
                client = cls._client()
                url = client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": cls.bucket(), "Key": key_or_path},
                    ExpiresIn=86400,
                )
                return url
            except (BotoCoreError, ClientError):
                pass

        return key_or_path
