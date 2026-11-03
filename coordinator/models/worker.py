"""
Worker compute nodes, GPU devices, and telemetry heartbeat models.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from coordinator.database import Base
from coordinator.models.base import TimestampMixin, UUIDMixin
from shared.constants import WorkerStatus

if TYPE_CHECKING:
    from coordinator.models.job import Job
    from coordinator.models.training import WorkerContribution
    from coordinator.models.usage import UsageRecord
    from coordinator.models.user import User


class Worker(Base, UUIDMixin, TimestampMixin):
    """Registered compute worker node operated by a third-party GPU provider."""

    __tablename__ = "workers"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default=WorkerStatus.OFFLINE.value,
        index=True,
        nullable=False,
    )
    auth_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    public_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    client_version: Mapped[str] = mapped_column(String(64), default="0.1.0", nullable=False)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=True,
    )
    total_jobs_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_jobs_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    provider: Mapped["User"] = relationship("User", back_populates="workers")
    gpu_devices: Mapped[list["GPUDevice"]] = relationship(
        "GPUDevice", back_populates="worker", cascade="all, delete-orphan"
    )
    heartbeats: Mapped[list["WorkerHeartbeat"]] = relationship(
        "WorkerHeartbeat", back_populates="worker", cascade="all, delete-orphan"
    )
    assigned_jobs: Mapped[list["Job"]] = relationship("Job", back_populates="assigned_worker")
    contributions: Mapped[list["WorkerContribution"]] = relationship(
        "WorkerContribution", back_populates="worker"
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        "UsageRecord", back_populates="worker"
    )


class GPUDevice(Base, UUIDMixin):
    """Discrete physical GPU device installed on a worker node."""

    __tablename__ = "gpu_devices"

    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    gpu_index: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    pci_bus_id: Mapped[str] = mapped_column(String(64), nullable=False)
    total_vram_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    free_vram_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    cuda_compute_capability: Mapped[str] = mapped_column(String(16), nullable=False)
    driver_version: Mapped[str] = mapped_column(String(64), nullable=False)
    cuda_version: Mapped[str] = mapped_column(String(32), nullable=False)
    temperature_celsius: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    power_draw_watts: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    utilization_gpu_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    utilization_mem_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    worker: Mapped["Worker"] = relationship("Worker", back_populates="gpu_devices")


class WorkerHeartbeat(Base, UUIDMixin):
    """Time-series telemetry heartbeat event record."""

    __tablename__ = "worker_heartbeats"

    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cpu_utilization_percent: Mapped[float] = mapped_column(Float, nullable=False)
    ram_total_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    ram_free_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    disk_free_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    gpu_metrics: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )

    # Relationships
    worker: Mapped["Worker"] = relationship("Worker", back_populates="heartbeats")
