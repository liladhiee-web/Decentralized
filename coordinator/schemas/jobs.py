"""
Pydantic schemas for submitting, monitoring, and managing AI inference and training jobs.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.constants import JobStatus, JobType


class SubmitInferenceTextRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model_id: UUID | None = Field(default=None, description="Registered model manifest ID")
    model_name: str | None = Field(
        default=None,
        description="Model repository or manifest name, e.g. 'meta-llama/Llama-3-8B-Instruct'",
    )
    prompt: str = Field(..., min_length=1, max_length=65536, description="User text input prompt")
    max_tokens: int = Field(default=512, ge=1, le=8192)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    stream: bool = Field(default=False, description="Whether to stream response tokens via SSE")
    stop_sequences: list[str] = Field(default_factory=list)
    min_vram_mb: int = Field(default=16384, ge=4096, description="Required GPU VRAM")


class SubmitInferenceImageRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model_id: UUID | None = None
    model_name: str | None = Field(default="stabilityai/stable-diffusion-xl-base-1.0")
    prompt: str = Field(..., min_length=1, max_length=2048)
    negative_prompt: str | None = Field(default=None, max_length=2048)
    width: int = Field(default=1024, ge=256, le=2048)
    height: int = Field(default=1024, ge=256, le=2048)
    num_inference_steps: int = Field(default=30, ge=1, le=100)
    guidance_scale: float = Field(default=7.5, ge=1.0, le=20.0)
    seed: int | None = None
    min_vram_mb: int = Field(default=12288, ge=6144)


class SubmitTrainingLoraRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model_id: UUID | None = None
    model_name: str = Field(..., description="Base model name, e.g. 'mistralai/Mistral-7B-v0.1'")
    dataset_id: UUID = Field(..., description="Uploaded fine-tuning dataset ID")
    lora_r: int = Field(default=16, ge=4, le=128, description="LoRA rank dimension")
    lora_alpha: int = Field(default=32, ge=8, le=256, description="LoRA scaling alpha")
    target_modules: list[str] = Field(
        default_factory=lambda: ["q_proj", "v_proj", "k_proj", "o_proj"]
    )
    epochs: int = Field(default=3, ge=1, le=20)
    learning_rate: float = Field(default=2e-4, gt=0.0, lt=1e-1)
    batch_size: int = Field(default=4, ge=1, le=64)
    min_vram_mb: int = Field(default=24576, ge=8192)


class JobEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    details: dict[str, Any]
    timestamp: datetime


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    assigned_worker_id: UUID | None
    type: JobType
    status: JobStatus
    priority: int
    model_id: UUID | None
    dataset_id: UUID | None
    execution_cost_credits: float
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class JobDetailResponse(JobResponse):
    input_parameters: dict[str, Any]
    resource_requirements: dict[str, Any]
    events: list[JobEventResponse] = Field(default_factory=list)


class JobListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    jobs: list[JobResponse]
