"""
AI compute job lifecycle models, dispatch attempts, and audit event logs.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from coordinator.database import Base
from coordinator.models.base import TimestampMixin, UUIDMixin
from shared.constants import JobStatus, JobType

if TYPE_CHECKING:
    from coordinator.models.artifact import Artifact, Dataset, ModelManifest
    from coordinator.models.training import TrainingRound
    from coordinator.models.usage import UsageRecord
    from coordinator.models.user import User
    from coordinator.models.worker import Worker


class Job(Base, UUIDMixin, TimestampMixin):
    """Core job state machine model representing an inference or training task."""

    __tablename__ = "jobs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_worker_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type: Mapped[str] = mapped_column(
        String(32),
        default=JobType.INFERENCE_TEXT.value,
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=JobStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    priority: Mapped[int] = mapped_column(Integer, default=10, nullable=False, index=True)
    model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_manifests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    input_parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    resource_requirements: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=lambda: {"min_vram_mb": 8192, "cuda_compute_min": "7.0"},
        nullable=False,
    )
    execution_cost_credits: Mapped[float] = mapped_column(
        Numeric(14, 4), default=0.0000, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="jobs")
    assigned_worker: Mapped["Worker | None"] = relationship(
        "Worker", back_populates="assigned_jobs"
    )
    model: Mapped["ModelManifest | None"] = relationship("ModelManifest", back_populates="jobs")
    dataset: Mapped["Dataset | None"] = relationship("Dataset", back_populates="jobs")
    attempts: Mapped[list["JobAttempt"]] = relationship(
        "JobAttempt", back_populates="job", cascade="all, delete-orphan"
    )
    events: Mapped[list["JobEvent"]] = relationship(
        "JobEvent", back_populates="job", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["Artifact"]] = relationship("Artifact", back_populates="job")
    usage_records: Mapped[list["UsageRecord"]] = relationship("UsageRecord", back_populates="job")
    training_rounds: Mapped[list["TrainingRound"]] = relationship(
        "TrainingRound", back_populates="job", cascade="all, delete-orphan"
    )


class JobAttempt(Base, UUIDMixin):
    """Tracks each execution attempt on a specific worker for failure handling and retries."""

    __tablename__ = "job_attempts"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.RUNNING.value, nullable=False)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="attempts")


class JobEvent(Base, UUIDMixin):
    """Immutable audit trail event during job execution."""

    __tablename__ = "job_events"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="events")
