"""
Worker Heartbeat Manager.
Periodically interrogates host and GPU metrics, transmits telemetry to the coordinator,
and tracks connection liveness.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

from shared.protocol import WorkerHeartbeatMessage
from worker.config import get_worker_settings
from worker.gpu_monitor import get_gpu_monitor

logger = logging.getLogger(__name__)


class HeartbeatManager:
    """Manages periodic transmission of system metrics over the WebSocket control channel."""

    def __init__(
        self,
        worker_id: UUID,
        send_fn: Callable[[WorkerHeartbeatMessage], Awaitable[None]],
    ) -> None:
        self.worker_id = worker_id
        self.send_fn = send_fn
        self.settings = get_worker_settings()
        self.gpu_monitor = get_gpu_monitor()
        self._running = False
        self._task: asyncio.Task | None = None
        self.current_job_id: UUID | None = None

    def start(self) -> None:
        """Start the background heartbeat sender loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info(
            "Heartbeat loop started (interval: %ds)", self.settings.HEARTBEAT_INTERVAL_SECONDS
        )

    async def stop(self) -> None:
        """Gracefully terminate heartbeat loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Heartbeat loop stopped")

    def set_current_job(self, job_id: UUID | None) -> None:
        """Update current active job ID reported in heartbeats."""
        self.current_job_id = job_id

    async def _heartbeat_loop(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(self.settings.HEARTBEAT_INTERVAL_SECONDS)
                telemetry = self.gpu_monitor.collect_telemetry()
                msg = WorkerHeartbeatMessage(
                    worker_id=self.worker_id,
                    telemetry=telemetry,
                    current_job_id=self.current_job_id,
                )
                await self.send_fn(msg)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error during periodic heartbeat dispatch: %s", e)
