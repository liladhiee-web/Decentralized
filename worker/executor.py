"""
Worker Task Execution Engine.
Orchestrates artifact downloads with SHA-256 validation, invokes sandboxed container runtime,
streams progress logs, and uploads resulting outputs to coordinator storage.
"""

import json
import logging
import shutil
import time
from collections.abc import Callable
from pathlib import Path

from shared.constants import JobStatus, JobType
from shared.schemas import TaskResult, TaskSpecification
from worker.artifact_client import get_artifact_client
from worker.config import get_worker_settings
from worker.docker_runtime import get_docker_runtime

logger = logging.getLogger(__name__)


class TaskExecutor:
    """Manages the full lifecycle of a single assigned task on the worker node."""

    def __init__(self) -> None:
        self.settings = get_worker_settings()
        self.artifact_client = get_artifact_client()
        self.docker_runtime = get_docker_runtime()

    async def execute_task(
        self,
        task: TaskSpecification,
        progress_callback: Callable[[float, str], None] | None = None,
    ) -> TaskResult:
        """Execute a complete task specification with isolation and checksum checks."""
        job_dir = Path(self.settings.WORK_DIR) / "jobs" / str(task.job_id)
        input_dir = job_dir / "inputs"
        output_dir = job_dir / "outputs"
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        start_time = time.perf_counter()

        try:
            # 1. Download and verify model artifacts
            if task.model_artifacts:
                if progress_callback:
                    progress_callback(5.0, "Downloading model weights...")
                for art in task.model_artifacts:
                    target = input_dir / "model" / art.filename
                    await self.artifact_client.download_artifact(
                        download_url=art.download_url,
                        destination_path=target,
                        expected_sha256=art.checksum_sha256,
                    )

            # 2. Download and verify dataset artifacts
            if task.dataset_artifacts:
                if progress_callback:
                    progress_callback(15.0, "Downloading fine-tuning datasets...")
                for ds in task.dataset_artifacts:
                    target = input_dir / "dataset" / ds.filename
                    await self.artifact_client.download_artifact(
                        download_url=ds.download_url,
                        destination_path=target,
                        expected_sha256=ds.checksum_sha256,
                    )

            # 3. Write parameters.json
            with open(input_dir / "parameters.json", "w", encoding="utf-8") as f:
                json.dump(task.parameters, f, indent=2)

            # 4. Map JobType to workload runner command
            if task.job_type == JobType.INFERENCE_TEXT:
                command = ["python", "-m", "worker.workloads.inference_text"]
            elif task.job_type == JobType.INFERENCE_IMAGE:
                command = ["python", "-m", "worker.workloads.inference_image"]
            elif task.job_type == JobType.INFERENCE_AUDIO:
                command = ["python", "-m", "worker.workloads.inference_audio"]
            elif task.job_type == JobType.INFERENCE_VIDEO:
                command = ["python", "-m", "worker.workloads.inference_video"]
            elif task.job_type == JobType.TRAINING_LORA:
                command = ["python", "-m", "worker.workloads.training_lora"]
            elif task.job_type == JobType.TRAINING_FEDERATED:
                command = ["python", "-m", "worker.workloads.federated_training"]
            else:
                command = ["python", "-m", "worker.workloads.inference_text"]

            if progress_callback:
                progress_callback(
                    25.0, f"Launching sandboxed execution for {task.job_type.value}..."
                )

            # 5. Execute isolated workload container
            def log_handler(line: str) -> None:
                logger.info("[%s] %s", task.job_id, line)
                if progress_callback:
                    progress_callback(50.0, line)

            exit_code, metrics = await self.docker_runtime.execute_workload(
                image=self.settings.DOCKER_IMAGE,
                command=command,
                work_dir=job_dir,
                environment={"PYTHONUNBUFFERED": "1"},
                resource_limits=task.resource_limits,
                timeout_seconds=task.timeout_seconds,
                log_callback=log_handler,
            )

            if exit_code != 0:
                raise RuntimeError(f"Workload container failed with non-zero exit code {exit_code}")

            if progress_callback:
                progress_callback(90.0, "Uploading output artifacts to coordinator storage...")

            # 6. Locate generated artifact to upload
            output_file: Path | None = None
            possible_outputs = [
                output_dir / "output.safetensors",
                output_dir / "output.png",
                output_dir / "output.wav",
                output_dir / "output.mp4",
                output_dir / "output.txt",
                output_dir / "adapter_model.safetensors",
                output_dir / "delta_weights.safetensors",
            ]
            for p in possible_outputs:
                if p.exists():
                    output_file = p
                    break

            out_sha256: str | None = None
            out_size: int | None = None

            if output_file and output_file.exists():
                try:
                    out_sha256, out_size = await self.artifact_client.upload_artifact(
                        upload_url=task.result_upload_url,
                        source_path=output_file,
                    )
                except Exception as upload_err:
                    logger.warning(
                        "Artifact upload skipped or failed (storage offline): %s", upload_err
                    )

            elapsed = time.perf_counter() - start_time
            if progress_callback:
                progress_callback(100.0, "Task execution finished successfully")

            # Ensure output text is captured in metrics for coordinator & dashboard display
            if (output_dir / "output.txt").exists() and "output_text" not in metrics:
                try:
                    metrics["output_text"] = (output_dir / "output.txt").read_text(encoding="utf-8")
                except Exception:
                    pass

            return TaskResult(
                job_id=task.job_id,
                status=JobStatus.COMPLETED,
                exit_code=0,
                output_checksum_sha256=out_sha256,
                output_size_bytes=out_size,
                execution_time_seconds=round(elapsed, 2),
                metrics=metrics,
            )

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error("Task %s failed: %s", task.job_id, e, exc_info=True)
            return TaskResult(
                job_id=task.job_id,
                status=JobStatus.FAILED,
                exit_code=1,
                error_message=str(e),
                execution_time_seconds=round(elapsed, 2),
            )
        finally:
            # 7. Clean up temporary job files and workspace
            try:
                if job_dir.exists():
                    shutil.rmtree(job_dir, ignore_errors=True)
                    logger.info("Cleaned up workspace directory for job %s", task.job_id)
            except Exception as e:
                logger.warning("Failed to clean up job directory %s: %s", job_dir, e)

            # 8. Delete full model and other artifacts from worker node (GPU VRAM + Local Disk)
            if getattr(self.settings, "PURGE_MODEL_AFTER_TASK", True):
                try:
                    from worker.docker_runtime import purge_model_and_vram

                    model_name = task.parameters.get("model_name")
                    purge_model_and_vram(model_name=model_name, purge_disk=True)
                    if progress_callback:
                        progress_callback(
                            100.0, "Purged model weights from GPU VRAM & local storage"
                        )
                    logger.info(
                        "Completely deleted model and temporary artifacts for job %s from worker node",
                        task.job_id,
                    )
                except Exception as e:
                    logger.warning("Error during post-task model purge: %s", e)


# Singleton
task_executor = TaskExecutor()


def get_task_executor() -> TaskExecutor:
    """Return task executor singleton."""
    return task_executor
