"""
Typed WebSocket messaging protocol for Coordinator-to-Worker bidirectional communication.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.constants import WebSocketMessageType
from shared.schemas import SystemTelemetry, TaskResult, TaskSpecification


class BaseWSMessage(BaseModel):
    """Envelope base model for all WebSocket messages."""

    model_config = ConfigDict(extra="ignore")

    type: WebSocketMessageType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str | None = None


# Worker -> Coordinator: Handshake Authentication
class WorkerAuthMessage(BaseWSMessage):
    type: WebSocketMessageType = WebSocketMessageType.WORKER_AUTH
    worker_id: UUID
    token: str = Field(..., description="Worker secret token or signature")
    hostname: str
    client_version: str
    telemetry: SystemTelemetry


# Coordinator -> Worker: Handshake Acknowledgement
class WorkerAuthAckMessage(BaseWSMessage):
    type: WebSocketMessageType = WebSocketMessageType.WORKER_AUTH_ACK
    success: bool
    session_id: str
    heartbeat_interval_seconds: int = 15
    message: str = "Authenticated successfully"


# Worker -> Coordinator: Periodic Heartbeat
class WorkerHeartbeatMessage(BaseWSMessage):
    type: WebSocketMessageType = WebSocketMessageType.WORKER_HEARTBEAT
    worker_id: UUID
    telemetry: SystemTelemetry
    current_job_id: UUID | None = None


# Coordinator -> Worker: Periodic Heartbeat Acknowledgement
class WorkerHeartbeatAckMessage(BaseWSMessage):
    type: WebSocketMessageType = WebSocketMessageType.WORKER_HEARTBEAT_ACK
    acknowledged: bool = True
    server_time: datetime = Field(default_factory=datetime.utcnow)


# Coordinator -> Worker: Task Assignment
class TaskAssignMessage(BaseWSMessage):
    type: WebSocketMessageType = WebSocketMessageType.TASK_ASSIGN
    task: TaskSpecification


# Worker -> Coordinator: Task Receipt Acknowledgement
class TaskAckMessage(BaseWSMessage):
    type: WebSocketMessageType = WebSocketMessageType.TASK_ACK
    job_id: UUID
    accepted: bool
    reason: str | None = None


# Worker -> Coordinator: Task Progress Stream
class TaskProgressMessage(BaseWSMessage):
    type: WebSocketMessageType = WebSocketMessageType.TASK_PROGRESS
    job_id: UUID
    progress_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    current_step: int = 0
    total_steps: int = 0
    metrics: dict[str, Any] = Field(default_factory=dict)
    log_line: str | None = None


# Worker -> Coordinator: Task Completion
class TaskCompleteMessage(BaseWSMessage):
    type: WebSocketMessageType = WebSocketMessageType.TASK_COMPLETE
    result: TaskResult


# Worker -> Coordinator: Task Failure
class TaskFailedMessage(BaseWSMessage):
    type: WebSocketMessageType = WebSocketMessageType.TASK_FAILED
    job_id: UUID
    error_message: str
    details: dict[str, Any] = Field(default_factory=dict)


# Coordinator -> Worker: Task Cancellation
class TaskCancelMessage(BaseWSMessage):
    type: WebSocketMessageType = WebSocketMessageType.TASK_CANCEL
    job_id: UUID
    reason: str = "Cancelled by user or coordinator timeout"


# General System Error
class SystemErrorMessage(BaseWSMessage):
    type: WebSocketMessageType = WebSocketMessageType.SYSTEM_ERROR
    error_code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
