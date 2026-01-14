from __future__ import annotations

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from api.settings import settings


class ObjectStorage:
    def __init__(self) -> None:
        self._s3 = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=Config(signature_version="s3v4"),
        )
        self._bucket = settings.S3_BUCKET

    def presign_get(self, key: str, ttl_seconds: int | None = None) -> str:
        expires_in = ttl_seconds or settings.S3_PRESIGNED_TTL_SECONDS
        return self._s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def presign_put(self, key: str, ttl_seconds: int | None = None) -> str:
        expires_in = ttl_seconds or settings.S3_PRESIGNED_TTL_SECONDS
        return self._s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def put_object(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        self._s3.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)

    def get_object(self, key: str) -> bytes:
        """Скачать объект из S3."""
        response = self._s3.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    def ensure_bucket(self) -> None:
        try:
            self._s3.head_bucket(Bucket=self._bucket)
        except ClientError:
            # Пытаемся создать бакет, если отсутствует (MinIO совместим)
            try:
                self._s3.create_bucket(Bucket=self._bucket)
            except ClientError:
                # Если гонка — игнорируем ошибку создания
                pass
