"""
Metering, billing-ready resource usage, and provider settlement audit records.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from coordinator.database import Base
from coordinator.models.base import UUIDMixin

if TYPE_CHECKING:
    from coordinator.models.job import Job
    from coordinator.models.user import User
    from coordinator.models.worker import Worker


class UsageRecord(Base, UUIDMixin):
    """Immutable metering record for compute time, VRAM allocation, and financial settlement."""

    __tablename__ = "usage_records"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gpu_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    vram_allocated_mb: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    billed_amount: Mapped[float] = mapped_column(Numeric(14, 4), default=0.0000, nullable=False)
    provider_payout_amount: Mapped[float] = mapped_column(
        Numeric(14, 4), default=0.0000, nullable=False
    )
    billing_status: Mapped[str] = mapped_column(String(32), default="settled", nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="usage_records")
    worker: Mapped["Worker"] = relationship("Worker", back_populates="usage_records")
    job: Mapped["Job"] = relationship("Job", back_populates="usage_records")
