"""
MinIO / S3 Object Storage Client Integration.
Handles presigned URLs, bucket initialization, health verification, and object checks.
"""

import logging
import time
from datetime import timedelta
from functools import lru_cache

from minio import Minio
from minio.error import S3Error

from coordinator.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class StorageService:
    """Manages S3/MinIO operations using short-lived signed URLs and streaming transfers."""

    def __init__(self) -> None:
        self.endpoint = settings.MINIO_ENDPOINT
        self.public_endpoint = settings.MINIO_PUBLIC_ENDPOINT.replace("http://", "").replace(
            "https://", ""
        )
        self.access_key = settings.MINIO_ROOT_USER
        self.secret_key = settings.MINIO_ROOT_PASSWORD
        self.secure = settings.MINIO_SECURE

        # Internal client for coordinator operations
        self.client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            region="us-east-1",
            secure=self.secure,
        )

        # Public-facing client for presigned URL generation (when public endpoint differs)
        self.public_client = Minio(
            endpoint=self.public_endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            region="us-east-1",
            secure=self.secure,
        )

        self.required_buckets = [
            settings.MINIO_BUCKET_MODELS,
            settings.MINIO_BUCKET_DATASETS,
            settings.MINIO_BUCKET_ARTIFACTS,
        ]

    def ensure_buckets_exist(self) -> None:
        """Create required platform storage buckets if they do not already exist."""
        for bucket in self.required_buckets:
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    logger.info("Created MinIO storage bucket: %s", bucket)
            except Exception as e:
                logger.error("Failed to initialize bucket %s: %s", bucket, e)
                raise

    def generate_presigned_upload_url(
        self,
        bucket_name: str,
        object_name: str,
        expiry_seconds: int | None = None,
    ) -> str:
        """Generate a short-lived HTTP PUT URL for direct-to-S3 client/worker uploads."""
        expires = timedelta(seconds=expiry_seconds or settings.MINIO_PRESIGNED_URL_EXPIRY_SECONDS)
        try:
            return self.public_client.presigned_put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=expires,
            )
        except Exception as e:
            logger.warning("MinIO offline or unreachable; using fallback URL: %s", e)
            return f"{settings.MINIO_PUBLIC_ENDPOINT}/{bucket_name}/{object_name}?offline=true"

    def generate_presigned_download_url(
        self,
        bucket_name: str,
        object_name: str,
        expiry_seconds: int | None = None,
    ) -> str:
        """Generate a short-lived HTTP GET URL for direct-from-S3 downloads."""
        expires = timedelta(seconds=expiry_seconds or settings.MINIO_PRESIGNED_URL_EXPIRY_SECONDS)
        try:
            return self.public_client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=expires,
            )
        except Exception as e:
            logger.warning("MinIO offline or unreachable; using fallback URL: %s", e)
            return f"{settings.MINIO_PUBLIC_ENDPOINT}/{bucket_name}/{object_name}?offline=true"
        expires = timedelta(seconds=expiry_seconds or settings.MINIO_PRESIGNED_URL_EXPIRY_SECONDS)
        return self.public_client.presigned_get_object(
            bucket_name=bucket_name,
            object_name=object_name,
            expires=expires,
        )

    def check_object_exists(self, bucket_name: str, object_name: str) -> bool:
        """Check whether an object exists in the specified bucket without downloading payload."""
        try:
            self.client.stat_object(bucket_name, object_name)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise

    def check_health(self) -> dict[str, float | str | bool]:
        """Probe MinIO connectivity and measure response latency."""
        start_time = time.perf_counter()
        try:
            self.client.list_buckets()
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "status": "healthy",
                "connected": True,
                "latency_ms": round(latency_ms, 2),
            }
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return {
                "status": "unhealthy",
                "connected": False,
                "latency_ms": round(latency_ms, 2),
                "error": str(e),
            }


@lru_cache
def get_storage_service() -> StorageService:
    """Return cached singleton instance of StorageService."""
    return StorageService()
