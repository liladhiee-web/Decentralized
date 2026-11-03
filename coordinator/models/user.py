"""
User and API Key database models.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from coordinator.database import Base
from coordinator.models.base import TimestampMixin, UUIDMixin
from shared.constants import UserRole

if TYPE_CHECKING:
    from coordinator.models.artifact import Artifact, Dataset, ModelManifest
    from coordinator.models.job import Job
    from coordinator.models.usage import UsageRecord
    from coordinator.models.worker import Worker


class User(Base, UUIDMixin, TimestampMixin):
    """Platform user account for job submitters, providers, or administrators."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(32), default=UserRole.USER.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    balance_credits: Mapped[float] = mapped_column(Numeric(14, 4), default=0.0000, nullable=False)

    # Relationships
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey", back_populates="user", cascade="all, delete-orphan"
    )
    workers: Mapped[list["Worker"]] = relationship("Worker", back_populates="provider")
    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="user")
    model_manifests: Mapped[list["ModelManifest"]] = relationship(
        "ModelManifest", back_populates="user"
    )
    datasets: Mapped[list["Dataset"]] = relationship("Dataset", back_populates="user")
    artifacts: Mapped[list["Artifact"]] = relationship("Artifact", back_populates="user")
    usage_records: Mapped[list["UsageRecord"]] = relationship("UsageRecord", back_populates="user")


class APIKey(Base, UUIDMixin):
    """Long-lived authentication API keys for CLI and automated client access."""

    __tablename__ = "api_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")
