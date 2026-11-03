"""
Unit tests for TaskExecutor workflow orchestration and output generation.
"""

from pathlib import Path
from uuid import uuid4

import pytest

from shared.constants import JobStatus, JobType
from shared.schemas import TaskSpecification
from worker.config import get_worker_settings
from worker.executor import TaskExecutor


@pytest.mark.asyncio
async def test_task_executor_simulated_inference(tmp_path: Path) -> None:
    """Verify TaskExecutor executes workload, collects metrics, and returns completed TaskResult."""
    settings = get_worker_settings()
    settings.WORK_DIR = tmp_path

    executor = TaskExecutor()

    # Mock artifact client upload so it doesn't need real HTTP server
    async def mock_upload(upload_url: str, source_path: Path, **kwargs):
        return "mocked_sha256_hash_12345678901234567890123456789012345678901234", 1024

    executor.artifact_client.upload_artifact = mock_upload  # type: ignore[assignment]

    task_spec = TaskSpecification(
        job_id=uuid4(),
        job_type=JobType.INFERENCE_TEXT,
        timeout_seconds=60,
        parameters={"prompt": "Test prompt", "max_tokens": 50},
        result_upload_url="http://mock-s3/upload/output.safetensors",
    )

    progress_events: list[tuple[float, str]] = []

    def on_progress(pct: float, msg: str) -> None:
        progress_events.append((pct, msg))

    result = await executor.execute_task(task_spec, progress_callback=on_progress)

    assert result.status == JobStatus.COMPLETED
    assert result.exit_code == 0
    assert result.execution_time_seconds >= 0.0
    assert result.output_checksum_sha256 is not None
    assert len(progress_events) >= 2
    assert progress_events[-1][0] == 100.0
