"""
Worker Artifact Client.
Handles streaming downloads and uploads via short-lived pre-signed MinIO/S3 URLs
with automatic SHA-256 integrity verification.
"""

import hashlib
import logging
from collections.abc import Callable
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class ChecksumMismatchError(Exception):
    """Raised when downloaded artifact checksum differs from coordinator manifest."""

    pass


class ArtifactClient:
    """Performs direct HTTP/S3 artifact transfers with SHA-256 validation."""

    def __init__(self, timeout_seconds: float = 3600.0) -> None:
        self.timeout = httpx.Timeout(timeout_seconds, connect=30.0)

    async def download_artifact(
        self,
        download_url: str,
        destination_path: Path,
        expected_sha256: str | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> Path:
        """
        Stream an artifact from a pre-signed GET URL to disk.
        Computes SHA-256 hash in flight and verifies against expected checksum.
        """
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        hasher = hashlib.sha256()
        downloaded_bytes = 0

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("GET", download_url) as response:
                if response.status_code != 200:
                    raise RuntimeError(
                        f"Failed to download artifact: HTTP {response.status_code} from {download_url}"
                    )

                total_bytes = int(response.headers.get("Content-Length", 0))

                with open(destination_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            hasher.update(chunk)
                            downloaded_bytes += len(chunk)
                            if progress_callback:
                                progress_callback(downloaded_bytes, total_bytes)

        computed_sha256 = hasher.hexdigest()

        if expected_sha256 and computed_sha256.lower() != expected_sha256.lower():
            # Delete corrupted or altered file immediately
            if destination_path.exists():
                destination_path.unlink()
            raise ChecksumMismatchError(
                f"Artifact checksum verification failed for {destination_path.name}: "
                f"expected {expected_sha256}, got {computed_sha256}"
            )

        logger.info(
            "Downloaded %s (%d bytes, SHA-256: %s)",
            destination_path.name,
            downloaded_bytes,
            computed_sha256[:12],
        )
        return destination_path

    async def upload_artifact(
        self,
        upload_url: str,
        source_path: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> tuple[str, int]:
        """
        Stream an artifact from disk to a pre-signed PUT URL.
        Returns: (sha256_hash, total_bytes_uploaded)
        """
        if not source_path.exists():
            raise FileNotFoundError(f"Source file {source_path} does not exist for upload")

        from worker.config import get_worker_settings

        worker_settings = get_worker_settings()
        http_base = worker_settings.get_http_url()

        # If upload_url is relative, prefix with coordinator's HTTP base
        if upload_url.startswith("/"):
            upload_url = f"{http_base.rstrip('/')}{upload_url}"
        elif ("127.0.0.1" in upload_url or "localhost" in upload_url) and not (
            "127.0.0.1" in http_base or "localhost" in http_base
        ):
            # Remote worker detected with localhost presigned URL: redirect through public coordinator tunnel!
            upload_url = f"{http_base.rstrip('/')}/api/v1/jobs/artifacts/upload"

        total_bytes = source_path.stat().st_size
        hasher = hashlib.sha256()

        # Compute SHA-256 and stream upload
        async def file_generator():
            uploaded = 0
            with open(source_path, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    hasher.update(chunk)
                    uploaded += len(chunk)
                    if progress_callback:
                        progress_callback(uploaded, total_bytes)
                    yield chunk

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # First pass: compute hash if needed or stream directly
            response = await client.put(
                upload_url,
                content=file_generator(),
                headers={"Content-Length": str(total_bytes)},
            )
            if response.status_code not in [200, 204]:
                raise RuntimeError(
                    f"Failed to upload artifact: HTTP {response.status_code} ({response.text})"
                )

        computed_sha256 = hasher.hexdigest()
        logger.info(
            "Uploaded %s (%d bytes, SHA-256: %s)",
            source_path.name,
            total_bytes,
            computed_sha256[:12],
        )
        return computed_sha256, total_bytes


# Singleton
artifact_client = ArtifactClient()


def get_artifact_client() -> ArtifactClient:
    """Return artifact client singleton."""
    return artifact_client
