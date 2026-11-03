"""
Re-export all database models to ensure centralized registration on Base.metadata.
"""

from coordinator.database import Base
from coordinator.models.artifact import Artifact, Dataset, ModelManifest, ModelVersion
from coordinator.models.base import TimestampMixin, UUIDMixin
from coordinator.models.job import Job, JobAttempt, JobEvent
from coordinator.models.training import TrainingRound, WorkerContribution
from coordinator.models.usage import UsageRecord
from coordinator.models.user import APIKey, User
from coordinator.models.worker import GPUDevice, Worker, WorkerHeartbeat

__all__ = [
    "Base",
    "UUIDMixin",
    "TimestampMixin",
    "User",
    "APIKey",
    "Worker",
    "GPUDevice",
    "WorkerHeartbeat",
    "Job",
    "JobAttempt",
    "JobEvent",
    "ModelManifest",
    "ModelVersion",
    "Dataset",
    "Artifact",
    "TrainingRound",
    "WorkerContribution",
    "UsageRecord",
]
