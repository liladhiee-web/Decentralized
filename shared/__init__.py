"""
Shared models, schemas, and protocol definitions for decentralized-ai-cloud.
"""

from shared.constants import (
    ArtifactType,
    JobStatus,
    JobType,
    UserRole,
    WebSocketMessageType,
    WorkerStatus,
)
from shared.protocol import (
    BaseWSMessage,
    SystemErrorMessage,
    TaskAckMessage,
    TaskAssignMessage,
    TaskCancelMessage,
    TaskCompleteMessage,
    TaskFailedMessage,
    TaskProgressMessage,
    WorkerAuthAckMessage,
    WorkerAuthMessage,
    WorkerHeartbeatAckMessage,
    WorkerHeartbeatMessage,
)
from shared.schemas import (
    ArtifactReference,
    GPUInfo,
    SystemTelemetry,
    TaskResult,
    TaskSpecification,
)

__all__ = [
    "UserRole",
    "WorkerStatus",
    "JobStatus",
    "JobType",
    "ArtifactType",
    "WebSocketMessageType",
    "GPUInfo",
    "SystemTelemetry",
    "ArtifactReference",
    "TaskSpecification",
    "TaskResult",
    "BaseWSMessage",
    "WorkerAuthMessage",
    "WorkerAuthAckMessage",
    "WorkerHeartbeatMessage",
    "WorkerHeartbeatAckMessage",
    "TaskAssignMessage",
    "TaskAckMessage",
    "TaskProgressMessage",
    "TaskCompleteMessage",
    "TaskFailedMessage",
    "TaskCancelMessage",
    "SystemErrorMessage",
]
