"""
CLI Streaming and Resumable Artifact Upload Utilities.
Provides progress bars and SHA-256 calculation for large model weights and dataset transfers.
"""

import hashlib
from collections.abc import Generator
from pathlib import Path

import httpx
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)


def calculate_file_sha256(file_path: Path) -> tuple[str, int]:
    """Compute SHA-256 digest and file size with progress display."""
    total_bytes = file_path.stat().st_size
    hasher = hashlib.sha256()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task(f"Hashing {file_path.name}", total=total_bytes)
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(1048576)  # 1 MB chunk
                if not chunk:
                    break
                hasher.update(chunk)
                progress.update(task, advance=len(chunk))

    return hasher.hexdigest(), total_bytes


def upload_file_with_progress(upload_url: str, file_path: Path) -> None:
    """Upload a file to a pre-signed S3/MinIO PUT URL with an interactive Rich progress bar."""
    total_bytes = file_path.stat().st_size

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task(f"Uploading {file_path.name}", total=total_bytes)

        def read_in_chunks() -> Generator[bytes, None, None]:
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(1048576)  # 1 MB chunk
                    if not chunk:
                        break
                    progress.update(task, advance=len(chunk))
                    yield chunk

        with httpx.Client(timeout=3600.0) as client:
            response = client.put(
                upload_url,
                content=read_in_chunks(),
                headers={"Content-Length": str(total_bytes)},
            )
            if response.status_code not in [200, 204]:
                raise RuntimeError(f"Upload failed: HTTP {response.status_code} ({response.text})")
