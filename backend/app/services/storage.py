import os
import abc
from pathlib import Path
from typing import Optional
import aiofiles

from app.core.config import settings


class StorageService(abc.ABC):
    """Abstract storage service interface."""

    @abc.abstractmethod
    async def save_file(self, file_bytes: bytes, relative_path: str, content_type: Optional[str] = None) -> str:
        """Save file bytes and return the relative storage path."""
        pass

    @abc.abstractmethod
    async def get_file(self, relative_path: str) -> bytes:
        """Read and return file bytes from storage."""
        pass

    @abc.abstractmethod
    async def delete_file(self, relative_path: str) -> bool:
        """Delete a file from storage."""
        pass

    @abc.abstractmethod
    async def file_exists(self, relative_path: str) -> bool:
        """Check if a file exists in storage."""
        pass


class LocalStorageService(StorageService):
    """Local filesystem storage implementation with path traversal protection."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or settings.LOCAL_STORAGE_DIR).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Path:
        clean_path = Path(relative_path).as_posix().lstrip("/")
        full_path = (self.base_dir / clean_path).resolve()
        # Prevent directory traversal attacks
        if not str(full_path).startswith(str(self.base_dir)):
            raise ValueError(f"Illegal file path traversal detected: {relative_path}")
        return full_path

    async def save_file(self, file_bytes: bytes, relative_path: str, content_type: Optional[str] = None) -> str:
        target_path = self._resolve_safe_path(relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(target_path, "wb") as f:
            await f.write(file_bytes)
        return relative_path

    async def get_file(self, relative_path: str) -> bytes:
        target_path = self._resolve_safe_path(relative_path)
        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
        async with aiofiles.open(target_path, "rb") as f:
            return await f.read()

    async def delete_file(self, relative_path: str) -> bool:
        target_path = self._resolve_safe_path(relative_path)
        if target_path.exists() and target_path.is_file():
            target_path.unlink()
            return True
        return False

    async def file_exists(self, relative_path: str) -> bool:
        target_path = self._resolve_safe_path(relative_path)
        return target_path.exists() and target_path.is_file()


class S3StorageService(StorageService):
    """S3-compatible object storage implementation (MinIO / AWS S3)."""

    def __init__(self):
        import boto3
        from botocore.config import Config

        self.bucket = settings.S3_BUCKET_NAME
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=Config(signature_version="s3v4"),
        )
        # Ensure bucket exists
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self.s3_client.create_bucket(Bucket=self.bucket)
            except Exception:
                pass

    async def save_file(self, file_bytes: bytes, relative_path: str, content_type: Optional[str] = None) -> str:
        clean_key = relative_path.lstrip("/")
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        self.s3_client.put_object(
            Bucket=self.bucket,
            Key=clean_key,
            Body=file_bytes,
            **extra_args,
        )
        return clean_key

    async def get_file(self, relative_path: str) -> bytes:
        clean_key = relative_path.lstrip("/")
        response = self.s3_client.get_object(Bucket=self.bucket, Key=clean_key)
        return response["Body"].read()

    async def delete_file(self, relative_path: str) -> bool:
        clean_key = relative_path.lstrip("/")
        self.s3_client.delete_object(Bucket=self.bucket, Key=clean_key)
        return True

    async def file_exists(self, relative_path: str) -> bool:
        clean_key = relative_path.lstrip("/")
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=clean_key)
            return True
        except Exception:
            return False


def get_storage_service() -> StorageService:
    """Factory dependency returning the active storage backend."""
    if settings.STORAGE_BACKEND.lower() == "s3":
        return S3StorageService()
    return LocalStorageService()

