"""
Standalone Worker Compute Daemon.
Initiates outbound TLS WebSocket connection to central coordinator,
handles hardware telemetry reporting, sandboxed task execution, and automatic recovery.
"""

import asyncio
import json
import logging
import signal
import socket
import sys
from uuid import UUID, uuid4

import websockets
from websockets.exceptions import ConnectionClosed

from shared.constants import JobStatus, WebSocketMessageType
from shared.protocol import (
    BaseWSMessage,
    TaskAckMessage,
    TaskAssignMessage,
    TaskCancelMessage,
    TaskCompleteMessage,
    TaskFailedMessage,
    TaskProgressMessage,
    WorkerAuthMessage,
)
from worker.config import get_worker_settings
from worker.executor import get_task_executor
from worker.gpu_monitor import get_gpu_monitor
from worker.heartbeat import HeartbeatManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [worker-agent] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("worker-agent")


class WorkerAgent:
    """Outbound community compute daemon process."""

    def __init__(self) -> None:
        self.settings = get_worker_settings()
        self.gpu_monitor = get_gpu_monitor()
        self.executor = get_task_executor()
        self.worker_id = self.settings.WORKER_ID or uuid4()
        self.hostname = socket.gethostname()
        self.running = True
        self.active_task_job_id: UUID | None = None
        self.current_execution_task: asyncio.Task | None = None

    def stop(self) -> None:
        """Signal agent to terminate connection loops."""
        logger.info("Termination signal received; shutting down worker agent...")
        self.running = False
        self.gpu_monitor.shutdown()

    async def run(self) -> None:
        """Main connection and reconnection lifecycle loop."""
        reconnect_delay = 2.0
        max_delay = float(self.settings.MAX_RECONNECT_DELAY_SECONDS)

        ws_url = self.settings.get_ws_url()
        logger.info("Worker Agent starting for Worker ID: %s", self.worker_id)
        logger.info("Target Coordinator WebSocket: %s", ws_url)

        while self.running:
            try:
                logger.info("Attempting outbound connection to coordinator at %s...", ws_url)
                async with websockets.connect(
                    ws_url,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=10,
                ) as ws:
                    reconnect_delay = 2.0  # Reset backoff on successful connection
                    logger.info("Connected to Coordinator. Initiating handshake...")

                    # 1. Perform Authentication Handshake
                    telemetry = self.gpu_monitor.collect_telemetry()
                    auth_frame = WorkerAuthMessage(
                        worker_id=self.worker_id,
                        token=self.settings.WORKER_TOKEN,
                        hostname=self.hostname,
                        client_version=self.settings.CLIENT_VERSION,
                        telemetry=telemetry,
                    )
                    await ws.send(auth_frame.model_dump_json())

                    auth_ack_raw = await asyncio.wait_for(ws.recv(), timeout=15.0)
                    auth_ack = json.loads(auth_ack_raw)

                    if auth_ack.get(
                        "type"
                    ) != WebSocketMessageType.WORKER_AUTH_ACK or not auth_ack.get("success"):
                        logger.error(
                            "Authentication rejected by coordinator: %s", auth_ack.get("message")
                        )
                        await asyncio.sleep(5.0)
                        continue

                    logger.info(
                        "Worker successfully authenticated with coordinator session %s",
                        auth_ack.get("session_id"),
                    )

                    # 2. Start Background Heartbeat Loop
                    async def send_heartbeat_frame(msg: BaseWSMessage) -> None:
                        await ws.send(msg.model_dump_json())

                    hb_manager = HeartbeatManager(
                        worker_id=self.worker_id,
                        send_fn=send_heartbeat_frame,
                    )
                    hb_manager.start()

                    # 3. Message Processing Loop
                    try:
                        async for raw_message in ws:
                            if not self.running:
                                break
                            msg = json.loads(raw_message)
                            msg_type = msg.get("type")

                            if msg_type == WebSocketMessageType.TASK_ASSIGN:
                                task_msg = TaskAssignMessage.model_validate(msg)
                                asyncio.create_task(
                                    self._handle_task_assignment(task_msg, ws, hb_manager)
                                )

                            elif msg_type == WebSocketMessageType.TASK_CANCEL:
                                cancel_msg = TaskCancelMessage.model_validate(msg)
                                self._handle_task_cancellation(cancel_msg)

                            elif msg_type == WebSocketMessageType.WORKER_HEARTBEAT_ACK:
                                pass  # Heartbeat acknowledged

                    finally:
                        await hb_manager.stop()

            except (TimeoutError, ConnectionClosed, OSError) as e:
                if not self.running:
                    break
                logger.warning(
                    "Connection to coordinator lost (%s). Reconnecting in %.1fs...",
                    e,
                    reconnect_delay,
                )
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 1.5, max_delay)
            except Exception as e:
                if not self.running:
                    break
                logger.error("Unexpected error in worker loop: %s", e, exc_info=True)
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 1.5, max_delay)

    async def _handle_task_assignment(
        self,
        task_msg: TaskAssignMessage,
        ws: websockets.WebSocketClientProtocol,
        hb_manager: HeartbeatManager,
    ) -> None:
        """Handle incoming task assignment."""
        task = task_msg.task
        self.active_task_job_id = task.job_id
        hb_manager.set_current_job(task.job_id)

        # Send ACK
        ack = TaskAckMessage(job_id=task.job_id, accepted=True)
        await ws.send(ack.model_dump_json())
        logger.info("Accepted task %s (%s)", task.job_id, task.job_type.value)

        # Progress callback sending stream frames
        async def progress_sender(pct: float, log_line: str) -> None:
            prog_frame = TaskProgressMessage(
                job_id=task.job_id,
                progress_percent=pct,
                log_line=log_line,
            )
            try:
                await ws.send(prog_frame.model_dump_json())
            except Exception:
                pass

        def sync_progress(pct: float, line: str) -> None:
            asyncio.create_task(progress_sender(pct, line))

        # Execute workload
        try:
            self.current_execution_task = asyncio.create_task(
                self.executor.execute_task(task, progress_callback=sync_progress)
            )
            result = await self.current_execution_task

            if result.status == JobStatus.COMPLETED:
                complete_msg = TaskCompleteMessage(result=result)
                await ws.send(complete_msg.model_dump_json())
                logger.info(
                    "Task %s completed successfully in %.2fs",
                    task.job_id,
                    result.execution_time_seconds,
                )
            else:
                fail_msg = TaskFailedMessage(
                    job_id=task.job_id,
                    error_message=result.error_message or "Task execution failed",
                )
                await ws.send(fail_msg.model_dump_json())
                logger.warning("Task %s reported failure: %s", task.job_id, result.error_message)

        except asyncio.CancelledError:
            logger.info("Task %s execution was cancelled", task.job_id)
        except Exception as e:
            logger.error("Error executing task %s: %s", task.job_id, e)
            fail_msg = TaskFailedMessage(job_id=task.job_id, error_message=str(e))
            await ws.send(fail_msg.model_dump_json())
        finally:
            self.active_task_job_id = None
            self.current_execution_task = None
            hb_manager.set_current_job(None)

    def _handle_task_cancellation(self, cancel_msg: TaskCancelMessage) -> None:
        """Cancel current task execution if matching job ID."""
        if self.active_task_job_id == cancel_msg.job_id and self.current_execution_task:
            logger.info("Cancelling active task %s: %s", cancel_msg.job_id, cancel_msg.reason)
            self.current_execution_task.cancel()


def main() -> None:
    """Worker daemon CLI entrypoint."""
    agent = WorkerAgent()

    loop = asyncio.get_event_loop()

    # Register OS signals for graceful termination
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, agent.stop)
        except NotImplementedError:
            # Signal handling on Windows
            signal.signal(sig, lambda s, f: agent.stop())

    try:
        loop.run_until_complete(agent.run())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
