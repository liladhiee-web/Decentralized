"""
Federated and multi-worker distributed training round coordination models.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from coordinator.database import Base
from coordinator.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from coordinator.models.job import Job
    from coordinator.models.worker import Worker


class TrainingRound(Base, UUIDMixin, TimestampMixin):
    """Orchestrates an aggregation round across multiple workers in federated LoRA training."""

    __tablename__ = "training_rounds"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    target_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    achieved_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    aggregate_storage_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="training_rounds")
    contributions: Mapped[list["WorkerContribution"]] = relationship(
        "WorkerContribution", back_populates="round", cascade="all, delete-orphan"
    )


class WorkerContribution(Base, UUIDMixin):
    """Individual LoRA weight-delta contribution submitted by a worker for a training round."""

    __tablename__ = "worker_contributions"

    round_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    num_samples_processed: Mapped[int] = mapped_column(Integer, nullable=False)
    delta_weight_storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    validation_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    round: Mapped["TrainingRound"] = relationship("TrainingRound", back_populates="contributions")
    worker: Mapped["Worker"] = relationship("Worker", back_populates="contributions")
