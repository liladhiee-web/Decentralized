"""
Pydantic schemas for AI model manifests, datasets, and output artifacts.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.constants import ArtifactType


class ModelManifestCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    description: str | None = None
    architecture: str = Field(
        ..., max_length=64, description="Model architecture identifier (e.g. LlamaForCausalLM)"
    )
    framework: str = Field(default="transformers", max_length=32)
    format: str = Field(default="safetensors", max_length=32)
    parameter_count: int | None = Field(default=None, ge=1)
    default_vram_required_mb: int = Field(default=16384, ge=2048)
    is_public: bool = False


class ModelManifestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    description: str | None
    architecture: str
    framework: str
    format: str
    parameter_count: int | None
    default_vram_required_mb: int
    is_public: bool
    created_at: datetime


class DatasetCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    description: str | None = None
    format: str = Field(default="jsonl", max_length=32)
    num_records: int = Field(default=0, ge=0)
    size_bytes: int = Field(..., ge=1)
    checksum_sha256: str = Field(..., min_length=64, max_length=64)


class DatasetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    description: str | None
    format: str
    num_records: int
    size_bytes: int
    storage_path: str
    checksum_sha256: str
    is_validated: bool
    created_at: datetime


class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID | None
    user_id: UUID
    artifact_type: ArtifactType
    filename: str
    size_bytes: int
    checksum_sha256: str
    mime_type: str
    metadata_json: dict[str, Any]
    created_at: datetime
    download_url: str | None = None


class PresignedUploadRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    size_bytes: int = Field(..., ge=1)
    checksum_sha256: str = Field(..., min_length=64, max_length=64)
    content_type: str = Field(default="application/octet-stream")


class PresignedUploadResponse(BaseModel):
    upload_url: str
    storage_path: str
    expiry_seconds: int
    headers: dict[str, str] = Field(default_factory=dict)
