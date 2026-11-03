"""
Unit tests for Worker ArtifactClient download/upload and SHA-256 verification.
"""

import hashlib
from pathlib import Path

import httpx
import pytest

from worker.artifact_client import ArtifactClient, ChecksumMismatchError


@pytest.mark.asyncio
async def test_artifact_download_checksum_validation(tmp_path: Path) -> None:
    """Verify download verifies expected SHA-256 and detects mismatched payloads."""
    client = ArtifactClient()
    dest = tmp_path / "test_file.txt"
    payload = b"Sample neural network weights chunk data 12345"
    correct_hash = hashlib.sha256(payload).hexdigest()
    bad_hash = "0000000000000000000000000000000000000000000000000000000000000000"

    # Mock HTTP transport
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload, headers={"Content-Length": str(len(payload))})

    real_client_cls = httpx.AsyncClient
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            httpx,
            "AsyncClient",
            lambda **kw: real_client_cls(transport=httpx.MockTransport(mock_handler)),
        )

        # 1. Successful download with matching SHA-256
        saved_path = await client.download_artifact(
            download_url="http://mock-storage/weights.safetensors",
            destination_path=dest,
            expected_sha256=correct_hash,
        )
        assert saved_path.exists()
        assert saved_path.read_bytes() == payload

        # 2. Failed download with tampered/mismatched SHA-256
        with pytest.raises(ChecksumMismatchError):
            await client.download_artifact(
                download_url="http://mock-storage/weights.safetensors",
                destination_path=dest,
                expected_sha256=bad_hash,
            )

        # File must be deleted on checksum failure
        assert not dest.exists()
