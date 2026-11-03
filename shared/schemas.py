"""
Shared Pydantic data schemas used across Coordinator, Worker Agent, and CLI.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.constants import ArtifactType, JobStatus, JobType


class GPUInfo(BaseModel):
    """Static and dynamic telemetry report for a physical GPU device."""

    model_config = ConfigDict(extra="ignore")

    index: int = Field(..., description="GPU device index (e.g. 0)")
    name: str = Field(..., description="Device commercial model name, e.g. NVIDIA RTX 4090")
    pci_bus_id: str = Field(..., description="PCI Bus Identifier")
    total_vram_mb: int = Field(..., ge=0, description="Total physical VRAM in megabytes")
    free_vram_mb: int = Field(..., ge=0, description="Current free VRAM in megabytes")
    cuda_compute_capability: str = Field(
        ..., description="Major.minor compute capability, e.g. 8.9"
    )
    driver_version: str = Field(..., description="NVIDIA kernel driver version")
    cuda_version: str = Field(..., description="Supported CUDA runtime version")
    temperature_celsius: float = Field(
        default=0.0, description="Current die temperature in Celsius"
    )
    power_draw_watts: float = Field(default=0.0, description="Current power draw in Watts")
    utilization_gpu_percent: int = Field(
        default=0, ge=0, le=100, description="GPU core utilization"
    )
    utilization_mem_percent: int = Field(
        default=0, ge=0, le=100, description="Memory controller utilization"
    )
    is_available: bool = Field(
        default=True, description="Whether device is available for workloads"
    )


class SystemTelemetry(BaseModel):
    """Worker host hardware resource telemetry."""

    model_config = ConfigDict(extra="ignore")

    cpu_utilization_percent: float = Field(..., ge=0.0, le=100.0)
    ram_total_mb: int = Field(..., ge=0)
    ram_free_mb: int = Field(..., ge=0)
    disk_free_mb: int = Field(..., ge=0)
    gpus: list[GPUInfo] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ArtifactReference(BaseModel):
    """Reference to an object stored in S3/MinIO with security checksum."""

    model_config = ConfigDict(extra="ignore")

    id: UUID
    artifact_type: ArtifactType
    download_url: str = Field(..., description="Pre-signed, time-limited download URL")
    checksum_sha256: str = Field(..., description="Hex SHA-256 digest for integrity verification")
    size_bytes: int = Field(..., ge=0)
    filename: str


class TaskSpecification(BaseModel):
    """Specification dispatched from Coordinator to Worker to execute a workload."""

    model_config = ConfigDict(extra="ignore")

    job_id: UUID
    job_type: JobType
    timeout_seconds: int = Field(default=3600, ge=10)
    model_artifacts: list[ArtifactReference] = Field(default_factory=list)
    dataset_artifacts: list[ArtifactReference] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    resource_limits: dict[str, Any] = Field(
        default_factory=lambda: {
            "max_vram_mb": 24576,
            "max_ram_mb": 32768,
            "max_cpus": 4,
        }
    )
    result_upload_url: str = Field(..., description="Pre-signed PUT URL for uploading output")


class TaskResult(BaseModel):
    """Final result emitted by Worker when job completes or fails."""

    model_config = ConfigDict(extra="ignore")

    job_id: UUID
    status: JobStatus
    exit_code: int = 0
    error_message: str | None = None
    output_checksum_sha256: str | None = None
    output_size_bytes: int | None = None
    execution_time_seconds: float = 0.0
    metrics: dict[str, Any] = Field(default_factory=dict)
