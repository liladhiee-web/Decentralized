"""
Shared domain constants, status enums, and protocol message types.
"""

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    USER = "user"
    PROVIDER = "provider"


class WorkerStatus(StrEnum):
    OFFLINE = "offline"
    IDLE = "idle"
    BUSY = "busy"
    DRAINING = "draining"
    ERROR = "error"


class JobStatus(StrEnum):
    PENDING = "pending"
    SCHEDULING = "scheduling"
    DISPATCHED = "dispatched"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class JobType(StrEnum):
    INFERENCE_TEXT = "inference_text"
    INFERENCE_IMAGE = "inference_image"
    INFERENCE_AUDIO = "inference_audio"
    INFERENCE_VIDEO = "inference_video"
    TRAINING_LORA = "training_lora"
    TRAINING_FEDERATED = "training_federated"


class ArtifactType(StrEnum):
    MODEL_ADAPTER = "model_adapter"
    IMAGE_OUTPUT = "image_output"
    AUDIO_OUTPUT = "audio_output"
    VIDEO_OUTPUT = "video_output"
    LOG_ARCHIVE = "log_archive"
    CHECKPOINT = "checkpoint"
    DATASET = "dataset"
    TENSOR_SHARD = "tensor_shard"


class WebSocketMessageType(StrEnum):
    # Handshake & Authentication
    WORKER_AUTH = "worker_auth"
    WORKER_AUTH_ACK = "worker_auth_ack"

    # Telemetry & Liveness
    WORKER_HEARTBEAT = "worker_heartbeat"
    WORKER_HEARTBEAT_ACK = "worker_heartbeat_ack"

    # Task Lifecycle Management
    TASK_ASSIGN = "task_assign"
    TASK_ACK = "task_ack"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    TASK_CANCEL = "task_cancel"

    # Diagnostic / System
    SYSTEM_ERROR = "system_error"
    SYSTEM_DRAIN = "system_drain"
