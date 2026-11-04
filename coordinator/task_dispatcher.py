"""
Task Dispatcher Subsystem.
Coordinates with the GPU Scheduler to match pending jobs to active workers,
constructs signed artifact transfer URLs, and transmits task specifications over WebSocket.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from coordinator.config import get_settings
from coordinator.models.job import Job, JobAttempt, JobEvent
from coordinator.models.worker import Worker
from coordinator.scheduler import get_scheduler
from coordinator.storage import get_storage_service
from coordinator.websocket.manager import get_connection_manager
from shared.constants import JobStatus, WorkerStatus
from shared.protocol import TaskAssignMessage, TaskCancelMessage
from shared.schemas import ArtifactReference, TaskSpecification

logger = logging.getLogger(__name__)
settings = get_settings()


class TaskDispatcher:
    """Orchestrates job state transitions, scheduling invocation, and worker dispatch."""

    def __init__(self) -> None:
        self.scheduler = get_scheduler()
        self.storage = get_storage_service()
        self.ws_manager = get_connection_manager()

    async def dispatch_job(self, job_id: UUID, db: AsyncSession) -> bool:
        """
        Attempt to schedule and dispatch a PENDING job to an active, eligible worker.
        Returns True if successfully dispatched, False otherwise.
        """
        result = await db.execute(
            select(Job)
            .where(Job.id == job_id)
            .options(
                selectinload(Job.model),
                selectinload(Job.dataset),
            )
        )
        job = result.scalar_one_or_none()

        if not job or job.status != JobStatus.PENDING.value:
            return False

        # Extract requirements
        reqs = job.resource_requirements or {}
        min_vram = reqs.get("min_vram_mb", 8192)
        min_compute = reqs.get("cuda_compute_min", "7.0")
        model_name = job.input_parameters.get("model_name") or (
            job.model.name if job.model else None
        )

        # Query scheduler
        decision = await self.scheduler.select_worker_for_inference(
            db=db,
            min_vram_mb=min_vram,
            min_cuda_compute=min_compute,
            model_name=model_name,
        )

        if not decision:
            logger.info(
                "No matching worker available for job %s; remaining in PENDING queue", job.id
            )
            return False

        # Verify active WebSocket connection is open
        if not self.ws_manager.is_connected(decision.worker_id):
            logger.warning(
                "Scheduled worker %s (%s) has no active WebSocket connection; skipping",
                decision.worker_id,
                decision.worker_name,
            )
            return False

        # Generate pre-signed PUT URL for worker to upload final output artifact
        if (
            "127.0.0.1" in settings.MINIO_PUBLIC_ENDPOINT
            or "localhost" in settings.MINIO_PUBLIC_ENDPOINT
        ):
            output_upload_url = f"/api/v1/jobs/{job.id}/upload"
        else:
            output_key = f"jobs/{job.id}/output.safetensors"
            output_upload_url = self.storage.generate_presigned_upload_url(
                bucket_name=settings.MINIO_BUCKET_ARTIFACTS,
                object_name=output_key,
                expiry_seconds=settings.MINIO_PRESIGNED_URL_EXPIRY_SECONDS,
            )

        # Generate pre-signed GET URLs for any required model/dataset artifacts
        model_artifacts: list[ArtifactReference] = []
        if job.model and hasattr(job.model, "versions") and job.model.versions:
            ver = job.model.versions[0]
            dl_url = self.storage.generate_presigned_download_url(
                bucket_name=settings.MINIO_BUCKET_MODELS,
                object_name=ver.storage_path,
            )
            model_artifacts.append(
                ArtifactReference(
                    id=ver.id,
                    artifact_type=ver.format,  # type: ignore[arg-type]
                    download_url=dl_url,
                    checksum_sha256=ver.checksum_sha256,
                    size_bytes=ver.size_bytes,
                    filename=f"{job.model.name}.safetensors",
                )
            )

        dataset_artifacts: list[ArtifactReference] = []
        if job.dataset:
            dl_url = self.storage.generate_presigned_download_url(
                bucket_name=settings.MINIO_BUCKET_DATASETS,
                object_name=job.dataset.storage_path,
            )
            dataset_artifacts.append(
                ArtifactReference(
                    id=job.dataset.id,
                    artifact_type="dataset",  # type: ignore[arg-type]
                    download_url=dl_url,
                    checksum_sha256=job.dataset.checksum_sha256,
                    size_bytes=job.dataset.size_bytes,
                    filename=f"{job.dataset.name}.jsonl",
                )
            )

        # Build task specification payload
        task_spec = TaskSpecification(
            job_id=job.id,
            job_type=job.type,  # type: ignore[arg-type]
            timeout_seconds=3600,
            model_artifacts=model_artifacts,
            dataset_artifacts=dataset_artifacts,
            parameters=job.input_parameters,
            resource_limits={
                "max_vram_mb": decision.allocated_vram_mb,
                "max_cpus": 4,
            },
            result_upload_url=output_upload_url,
        )

        assign_msg = TaskAssignMessage(task=task_spec)

        # Transmit task assignment frame to worker
        sent = await self.ws_manager.send_message(decision.worker_id, assign_msg)
        if not sent:
            logger.error("Failed to transmit task frame to worker %s", decision.worker_id)
            return False

        # Transition job state in database
        now = datetime.now(UTC)
        job.assigned_worker_id = decision.worker_id
        job.status = JobStatus.DISPATCHED.value
        job.started_at = now
        job.execution_cost_credits = decision.estimated_cost_credits

        # Create execution attempt record
        attempt = JobAttempt(
            job_id=job.id,
            worker_id=decision.worker_id,
            attempt_number=1,
            status=JobStatus.DISPATCHED.value,
        )
        db.add(attempt)

        # Create audit event log
        event = JobEvent(
            job_id=job.id,
            event_type="dispatched",
            details={
                "worker_id": str(decision.worker_id),
                "worker_name": decision.worker_name,
                "gpu_name": decision.gpu_name,
                "score": decision.score,
            },
        )
        db.add(event)

        # Update worker state
        worker_res = await db.execute(select(Worker).where(Worker.id == decision.worker_id))
        worker = worker_res.scalar_one_or_none()
        if worker:
            worker.status = WorkerStatus.BUSY.value

        await db.commit()
        logger.info("Successfully dispatched job %s to worker %s", job.id, decision.worker_name)
        return True

    async def dispatch_pending_jobs(self, db: AsyncSession) -> int:
        """Scan and dispatch any pending jobs in priority order."""
        result = await db.execute(
            select(Job.id)
            .where(Job.status == JobStatus.PENDING.value)
            .order_by(Job.priority.desc(), Job.created_at.asc())
        )
        pending_ids = result.scalars().all()
        dispatched_count = 0
        for jid in pending_ids:
            if await self.dispatch_job(jid, db):
                dispatched_count += 1
        return dispatched_count

    async def cancel_job(
        self, job_id: UUID, db: AsyncSession, reason: str = "User requested cancellation"
    ) -> bool:
        """Cancel an in-flight or pending job and notify assigned worker."""
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()

        if not job or job.status in [
            JobStatus.COMPLETED.value,
            JobStatus.FAILED.value,
            JobStatus.CANCELLED.value,
        ]:
            return False

        # If job is already assigned to a live worker, send cancel signal
        if job.assigned_worker_id and self.ws_manager.is_connected(job.assigned_worker_id):
            cancel_msg = TaskCancelMessage(job_id=job.id, reason=reason)
            await self.ws_manager.send_message(job.assigned_worker_id, cancel_msg)

        job.status = JobStatus.CANCELLED.value
        job.completed_at = datetime.now(UTC)
        job.error_message = f"Cancelled: {reason}"

        event = JobEvent(
            job_id=job.id,
            event_type="cancelled",
            details={"reason": reason},
        )
        db.add(event)
        await db.commit()
        return True


# Dispatcher singleton
dispatcher = TaskDispatcher()


def get_task_dispatcher() -> TaskDispatcher:
    """Return task dispatcher singleton."""
    return dispatcher
