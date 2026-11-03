"""
WebSocket Worker Connection Manager.
Maintains persistent bidirectional control channels with community GPU workers,
processes heartbeats and GPU telemetry, routes task assignments, and streams execution progress.
"""

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from coordinator.auth.security import verify_worker_token
from coordinator.database import get_db_context
from coordinator.models.artifact import Artifact
from coordinator.models.job import Job, JobEvent
from coordinator.models.usage import UsageRecord
from coordinator.models.worker import GPUDevice, Worker, WorkerHeartbeat
from shared.constants import ArtifactType, JobStatus, WebSocketMessageType, WorkerStatus
from shared.protocol import (
    BaseWSMessage,
    SystemErrorMessage,
    TaskAckMessage,
    TaskCompleteMessage,
    TaskFailedMessage,
    TaskProgressMessage,
    WorkerAuthAckMessage,
    WorkerAuthMessage,
    WorkerHeartbeatAckMessage,
    WorkerHeartbeatMessage,
)

logger = logging.getLogger(__name__)


class WorkerConnectionManager:
    """Manages active WebSocket connections to community GPU worker daemons."""

    def __init__(self) -> None:
        # In-memory mapping of worker_id -> WebSocket
        self.active_connections: dict[UUID, WebSocket] = {}
        # In-memory mapping of job_id -> list of subscriber queues for SSE / live streaming
        self.job_progress_subscribers: dict[UUID, list[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def register_connection(self, worker_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            self.active_connections[worker_id] = websocket
            logger.info("Worker %s registered on WebSocket control channel", worker_id)

    async def unregister_connection(self, worker_id: UUID) -> None:
        async with self._lock:
            if worker_id in self.active_connections:
                del self.active_connections[worker_id]
                logger.info("Worker %s disconnected from WebSocket control channel", worker_id)

    def is_connected(self, worker_id: UUID) -> bool:
        return worker_id in self.active_connections

    async def send_message(self, worker_id: UUID, message: BaseWSMessage) -> bool:
        """Send a typed WebSocket message envelope to an active worker."""
        ws = self.active_connections.get(worker_id)
        if not ws:
            logger.warning("Attempted to send frame to disconnected worker %s", worker_id)
            return False
        try:
            await ws.send_text(message.model_dump_json())
            return True
        except Exception as e:
            logger.error("Failed to send frame to worker %s: %s", worker_id, e)
            await self.unregister_connection(worker_id)
            return False

    async def subscribe_job_progress(self, job_id: UUID) -> asyncio.Queue:
        """Subscribe to real-time progress events for a specific job."""
        async with self._lock:
            q: asyncio.Queue = asyncio.Queue()
            if job_id not in self.job_progress_subscribers:
                self.job_progress_subscribers[job_id] = []
            self.job_progress_subscribers[job_id].append(q)
            return q

    async def unsubscribe_job_progress(self, job_id: UUID, q: asyncio.Queue) -> None:
        async with self._lock:
            if job_id in self.job_progress_subscribers:
                if q in self.job_progress_subscribers[job_id]:
                    self.job_progress_subscribers[job_id].remove(q)
                if not self.job_progress_subscribers[job_id]:
                    del self.job_progress_subscribers[job_id]

    async def broadcast_job_event(self, job_id: UUID, event_data: dict[str, Any]) -> None:
        """Broadcast a progress event or log line to all active listeners."""
        subscribers = self.job_progress_subscribers.get(job_id, [])
        for q in subscribers:
            await q.put(event_data)

    async def handle_worker_lifecycle(self, websocket: WebSocket) -> None:
        """Main lifecycle loop handling an incoming worker WebSocket connection."""
        await websocket.accept()
        authenticated_worker_id: UUID | None = None

        try:
            # 1. Await Initial Authentication Frame
            auth_raw = await asyncio.wait_for(websocket.receive_text(), timeout=15.0)
            auth_data = json.loads(auth_raw)
            auth_msg = WorkerAuthMessage.model_validate(auth_data)

            # Authenticate against database
            async with get_db_context() as db:
                result = await db.execute(
                    select(Worker)
                    .where(Worker.id == auth_msg.worker_id)
                    .options(selectinload(Worker.gpu_devices))
                )
                worker = result.scalar_one_or_none()

                if not worker or not verify_worker_token(auth_msg.token, worker.auth_token_hash):
                    logger.warning(
                        "Rejected worker auth for ID %s: Invalid token", auth_msg.worker_id
                    )
                    err_resp = SystemErrorMessage(
                        error_code="AUTH_FAILED",
                        message="Worker authentication token is invalid or worker does not exist",
                    )
                    await websocket.send_text(err_resp.model_dump_json())
                    await websocket.close(code=1008)
                    return

                # Update worker state
                worker.status = WorkerStatus.IDLE.value
                worker.hostname = auth_msg.hostname
                worker.client_version = auth_msg.client_version
                worker.last_heartbeat_at = datetime.now(UTC)

                # Upsert reported GPU devices
                existing_gpus = {g.gpu_index: g for g in worker.gpu_devices}
                for gpu_info in auth_msg.telemetry.gpus:
                    if gpu_info.index in existing_gpus:
                        dev = existing_gpus[gpu_info.index]
                        dev.name = gpu_info.name
                        dev.pci_bus_id = gpu_info.pci_bus_id
                        dev.total_vram_mb = gpu_info.total_vram_mb
                        dev.free_vram_mb = gpu_info.free_vram_mb
                        dev.cuda_compute_capability = gpu_info.cuda_compute_capability
                        dev.driver_version = gpu_info.driver_version
                        dev.cuda_version = gpu_info.cuda_version
                        dev.temperature_celsius = gpu_info.temperature_celsius
                        dev.power_draw_watts = gpu_info.power_draw_watts
                        dev.utilization_gpu_percent = gpu_info.utilization_gpu_percent
                        dev.utilization_mem_percent = gpu_info.utilization_mem_percent
                        dev.is_available = gpu_info.is_available
                    else:
                        new_dev = GPUDevice(
                            worker_id=worker.id,
                            gpu_index=gpu_info.index,
                            name=gpu_info.name,
                            pci_bus_id=gpu_info.pci_bus_id,
                            total_vram_mb=gpu_info.total_vram_mb,
                            free_vram_mb=gpu_info.free_vram_mb,
                            cuda_compute_capability=gpu_info.cuda_compute_capability,
                            driver_version=gpu_info.driver_version,
                            cuda_version=gpu_info.cuda_version,
                            temperature_celsius=gpu_info.temperature_celsius,
                            power_draw_watts=gpu_info.power_draw_watts,
                            utilization_gpu_percent=gpu_info.utilization_gpu_percent,
                            utilization_mem_percent=gpu_info.utilization_mem_percent,
                            is_available=gpu_info.is_available,
                        )
                        db.add(new_dev)

                await db.commit()

            authenticated_worker_id = auth_msg.worker_id
            await self.register_connection(authenticated_worker_id, websocket)

            # Send Auth Ack
            ack_msg = WorkerAuthAckMessage(
                success=True,
                session_id=str(authenticated_worker_id),
                heartbeat_interval_seconds=15,
                message="Worker authenticated successfully",
            )
            await websocket.send_text(ack_msg.model_dump_json())

            # 2. Continuous Message Loop
            while True:
                msg_raw = await websocket.receive_text()
                msg_dict = json.loads(msg_raw)
                msg_type = msg_dict.get("type")

                if msg_type == WebSocketMessageType.WORKER_HEARTBEAT:
                    hb = WorkerHeartbeatMessage.model_validate(msg_dict)
                    await self._process_heartbeat(hb)
                    # Respond with ack
                    hb_ack = WorkerHeartbeatAckMessage(acknowledged=True)
                    await websocket.send_text(hb_ack.model_dump_json())

                elif msg_type == WebSocketMessageType.TASK_ACK:
                    ack = TaskAckMessage.model_validate(msg_dict)
                    await self._process_task_ack(ack)

                elif msg_type == WebSocketMessageType.TASK_PROGRESS:
                    prog = TaskProgressMessage.model_validate(msg_dict)
                    await self._process_task_progress(prog)

                elif msg_type == WebSocketMessageType.TASK_COMPLETE:
                    comp = TaskCompleteMessage.model_validate(msg_dict)
                    await self._process_task_complete(comp, authenticated_worker_id)

                elif msg_type == WebSocketMessageType.TASK_FAILED:
                    fail = TaskFailedMessage.model_validate(msg_dict)
                    await self._process_task_failed(fail, authenticated_worker_id)

        except (TimeoutError, WebSocketDisconnect):
            logger.info("Worker %s disconnected", authenticated_worker_id)
        except Exception as e:
            logger.error(
                "Error in worker WebSocket loop for %s: %s",
                authenticated_worker_id,
                e,
                exc_info=True,
            )
        finally:
            if authenticated_worker_id:
                await self.unregister_connection(authenticated_worker_id)
                # Mark worker offline in DB
                async with get_db_context() as db:
                    result = await db.execute(
                        select(Worker).where(Worker.id == authenticated_worker_id)
                    )
                    w = result.scalar_one_or_none()
                    if w:
                        w.status = WorkerStatus.OFFLINE.value
                        await db.commit()

    async def _process_heartbeat(self, hb: WorkerHeartbeatMessage) -> None:
        """Update worker liveness and persist telemetry snapshot in database."""
        async with get_db_context() as db:
            result = await db.execute(
                select(Worker)
                .where(Worker.id == hb.worker_id)
                .options(selectinload(Worker.gpu_devices))
            )
            worker = result.scalar_one_or_none()
            if not worker:
                return

            worker.last_heartbeat_at = datetime.now(UTC)
            if worker.status == WorkerStatus.OFFLINE.value:
                worker.status = WorkerStatus.IDLE.value

            # Record telemetry heartbeat
            gpu_data = [g.model_dump() for g in hb.telemetry.gpus]
            heartbeat_record = WorkerHeartbeat(
                worker_id=worker.id,
                cpu_utilization_percent=hb.telemetry.cpu_utilization_percent,
                ram_total_mb=hb.telemetry.ram_total_mb,
                ram_free_mb=hb.telemetry.ram_free_mb,
                disk_free_mb=hb.telemetry.disk_free_mb,
                gpu_metrics=gpu_data,
            )
            db.add(heartbeat_record)

            # Update live GPU metrics
            existing_gpus = {g.gpu_index: g for g in worker.gpu_devices}
            for gpu_info in hb.telemetry.gpus:
                if gpu_info.index in existing_gpus:
                    dev = existing_gpus[gpu_info.index]
                    dev.free_vram_mb = gpu_info.free_vram_mb
                    dev.temperature_celsius = gpu_info.temperature_celsius
                    dev.power_draw_watts = gpu_info.power_draw_watts
                    dev.utilization_gpu_percent = gpu_info.utilization_gpu_percent
                    dev.utilization_mem_percent = gpu_info.utilization_mem_percent

            await db.commit()

    async def _process_task_ack(self, ack: TaskAckMessage) -> None:
        """Record task receipt acknowledgement from worker."""
        async with get_db_context() as db:
            result = await db.execute(select(Job).where(Job.id == ack.job_id))
            job = result.scalar_one_or_none()
            if not job:
                return

            if ack.accepted:
                job.status = JobStatus.RUNNING.value
                event = JobEvent(
                    job_id=job.id,
                    event_type="accepted_by_worker",
                    details={"accepted": True},
                )
            else:
                job.status = JobStatus.FAILED.value
                job.error_message = f"Worker rejected task: {ack.reason}"
                event = JobEvent(
                    job_id=job.id,
                    event_type="rejected_by_worker",
                    details={"reason": ack.reason},
                )
            db.add(event)
            await db.commit()

    async def _process_task_progress(self, prog: TaskProgressMessage) -> None:
        """Forward real-time progress update to subscribers."""
        event_payload = {
            "type": "progress",
            "job_id": str(prog.job_id),
            "progress_percent": prog.progress_percent,
            "current_step": prog.current_step,
            "total_steps": prog.total_steps,
            "metrics": prog.metrics,
            "log_line": prog.log_line,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        await self.broadcast_job_event(prog.job_id, event_payload)

    async def _process_task_complete(self, comp: TaskCompleteMessage, worker_id: UUID) -> None:
        """Record job completion, create output artifacts, and calculate billing records."""
        async with get_db_context() as db:
            result = await db.execute(
                select(Job)
                .where(Job.id == comp.result.job_id)
                .options(selectinload(Job.assigned_worker))
            )
            job = result.scalar_one_or_none()
            if not job:
                return

            now = datetime.now(UTC)
            job.status = JobStatus.COMPLETED.value
            job.completed_at = now

            # Increment worker statistics
            worker_result = await db.execute(select(Worker).where(Worker.id == worker_id))
            worker = worker_result.scalar_one_or_none()
            if worker:
                worker.total_jobs_completed += 1
                worker.status = WorkerStatus.IDLE.value

            # Create output Artifact record if output was generated
            if comp.result.output_checksum_sha256:
                artifact = Artifact(
                    job_id=job.id,
                    user_id=job.user_id,
                    artifact_type=ArtifactType.IMAGE_OUTPUT.value
                    if "image" in job.type
                    else ArtifactType.MODEL_ADAPTER.value,
                    storage_path=f"artifacts/{job.id}/output.safetensors",
                    filename="output.safetensors",
                    size_bytes=comp.result.output_size_bytes or 0,
                    checksum_sha256=comp.result.output_checksum_sha256,
                    metadata_json=comp.result.metrics,
                )
                db.add(artifact)

            # Record billing & usage metering
            exec_time = comp.result.execution_time_seconds
            vram_req = job.resource_requirements.get("min_vram_mb", 8192)
            billed_amount = float(job.execution_cost_credits)
            provider_payout = round(
                billed_amount * 0.85, 4
            )  # 85% revenue share to community provider

            usage = UsageRecord(
                user_id=job.user_id,
                worker_id=worker_id,
                job_id=job.id,
                gpu_seconds=exec_time,
                vram_allocated_mb=vram_req,
                billed_amount=billed_amount,
                provider_payout_amount=provider_payout,
                billing_status="settled",
            )
            db.add(usage)

            # Record completion audit event
            event = JobEvent(
                job_id=job.id,
                event_type="completed",
                details={
                    "execution_time_seconds": exec_time,
                    "metrics": comp.result.metrics,
                },
            )
            db.add(event)
            await db.commit()

        # Broadcast final completion event
        await self.broadcast_job_event(
            comp.result.job_id,
            {"type": "completed", "job_id": str(comp.result.job_id)},
        )

    async def _process_task_failed(self, fail: TaskFailedMessage, worker_id: UUID) -> None:
        """Handle task failure reported by worker."""
        async with get_db_context() as db:
            result = await db.execute(select(Job).where(Job.id == fail.job_id))
            job = result.scalar_one_or_none()
            if not job:
                return

            job.status = JobStatus.FAILED.value
            job.error_message = fail.error_message
            job.completed_at = datetime.now(UTC)

            worker_result = await db.execute(select(Worker).where(Worker.id == worker_id))
            worker = worker_result.scalar_one_or_none()
            if worker:
                worker.total_jobs_failed += 1
                worker.status = WorkerStatus.IDLE.value

            event = JobEvent(
                job_id=job.id,
                event_type="failed",
                details={"error": fail.error_message, "details": fail.details},
            )
            db.add(event)
            await db.commit()

        await self.broadcast_job_event(
            fail.job_id,
            {"type": "failed", "job_id": str(fail.job_id), "error": fail.error_message},
        )


# Singleton instance of manager
manager = WorkerConnectionManager()


def get_connection_manager() -> WorkerConnectionManager:
    """Return active WebSocket connection manager singleton."""
    return manager
