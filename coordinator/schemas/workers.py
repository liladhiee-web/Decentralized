"""
Pydantic schemas for GPU compute worker registration and telemetry reporting.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.constants import WorkerStatus


class GPUDeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    gpu_index: int
    name: str
    pci_bus_id: str
    total_vram_mb: int
    free_vram_mb: int
    cuda_compute_capability: str
    driver_version: str
    cuda_version: str
    temperature_celsius: float
    power_draw_watts: float
    utilization_gpu_percent: int
    utilization_mem_percent: int
    is_available: bool
    updated_at: datetime


class WorkerRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Unique worker hostname/label")
    hostname: str = Field(..., max_length=255)
    public_key: str | None = Field(default=None, max_length=1024)
    client_version: str = Field(default="0.1.0", max_length=64)


class WorkerRegisterResponse(BaseModel):
    worker_id: UUID
    name: str
    token: str = Field(..., description="Secret worker authentication token (shown only once)")
    websocket_url: str
    install_command: str


class WorkerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider_id: UUID
    name: str
    hostname: str
    status: WorkerStatus
    client_version: str
    last_heartbeat_at: datetime | None
    total_jobs_completed: int
    total_jobs_failed: int
    created_at: datetime
    gpu_devices: list[GPUDeviceResponse] = Field(default_factory=list)


class WorkerStatusUpdateRequest(BaseModel):
    status: WorkerStatus = Field(..., description="Set status: idle, draining, offline")
