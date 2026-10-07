"""S3-compatible storage backend (boto3).

Works against SeaweedFS (our local default), MinIO, AWS S3 and R2 - they all
speak the same API.

WHY the `asyncio.to_thread` wrappers: boto3 is synchronous. Calling it directly
from an `async def` would block the event loop for the whole upload, freezing
every other request in the process. Running it in a worker thread keeps the loop
free. (This is also why `async def` alone does not make something concurrent.)
"""

import asyncio
from functools import lru_cache
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ProviderError
from app.core.logging import get_logger
from app.services.storage.base import StorageBackend, StoredObject
from app.services.storage.urls import public_url

log = get_logger(__name__)


class S3Storage(StorageBackend):
    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.s3_bucket
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            # path-style addressing: bucket.localhost does not resolve, and
            # SeaweedFS/MinIO expect http://host/bucket/key anyway.
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    async def ensure_ready(self) -> None:
        def _ensure() -> None:
            try:
                self._client.head_bucket(Bucket=self.bucket)
            except ClientError:
                self._client.create_bucket(Bucket=self.bucket)

        try:
            await asyncio.to_thread(_ensure)
            log.info("storage_ready", bucket=self.bucket)
        except (ClientError, BotoCoreError) as exc:
            raise ProviderError(f"Storage is unavailable: {exc}", code="STORAGE_ERROR") from exc

    async def put_bytes(self, key: str, data: bytes, mime_type: str) -> StoredObject:
        def _put() -> None:
            self._client.put_object(
                Bucket=self.bucket, Key=key, Body=data, ContentType=mime_type
            )

        try:
            await asyncio.to_thread(_put)
        except (ClientError, BotoCoreError) as exc:
            raise ProviderError(f"Upload failed: {exc}", code="STORAGE_ERROR") from exc

        log.info("storage_put", key=key, size=len(data), mime_type=mime_type)
        url = public_url(key)
        assert url is not None
        return StoredObject(
            storage_key=key, size_bytes=len(data), mime_type=mime_type, public_url=url
        )

    async def get_bytes(self, key: str) -> bytes:
        def _get() -> bytes:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            return bytes(response["Body"].read())

        try:
            return await asyncio.to_thread(_get)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404"}:
                raise NotFoundError(f"Object {key} does not exist.",
                                    code="ASSET_FILE_NOT_FOUND") from exc
            raise ProviderError(f"Download failed: {exc}", code="STORAGE_ERROR") from exc

    async def delete(self, key: str) -> None:
        def _delete() -> None:
            self._client.delete_object(Bucket=self.bucket, Key=key)

        try:
            await asyncio.to_thread(_delete)
        except (ClientError, BotoCoreError) as exc:
            raise ProviderError(f"Delete failed: {exc}", code="STORAGE_ERROR") from exc

    async def exists(self, key: str) -> bool:
        def _head() -> bool:
            try:
                self._client.head_object(Bucket=self.bucket, Key=key)
                return True
            except ClientError:
                return False

        return await asyncio.to_thread(_head)

    async def presigned_url(self, key: str, expires_in: int = 3600) -> str:
        def _sign() -> str:
            return str(
                self._client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket, "Key": key},
                    ExpiresIn=expires_in,
                )
            )

        return await asyncio.to_thread(_sign)


@lru_cache
def get_storage() -> StorageBackend:
    """One client per process (boto3 clients are thread-safe and reusable)."""
    return S3Storage()
