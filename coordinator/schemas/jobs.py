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
    min_vram_mb: int = Field(default=2048, ge=512, description="Required GPU VRAM")


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
    min_vram_mb: int = Field(default=4096, ge=1024)


class SubmitInferenceAudioRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model_id: UUID | None = None
    model_name: str | None = Field(
        default="openai/whisper-tiny",
        description="Audio model identifier, e.g. 'openai/whisper-base' or 'suno/bark-small'",
    )
    prompt: str = Field(
        ..., min_length=1, max_length=8192, description="Audio prompt or input transcript"
    )
    task_type: str = Field(
        default="transcribe", description="'transcribe' for STT or 'synthesize' for TTS"
    )
    min_vram_mb: int = Field(default=2048, ge=512)


class SubmitInferenceVideoRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model_id: UUID | None = None
    model_name: str | None = Field(
        default="stabilityai/stable-video-diffusion-img2vid",
        description="Video synthesis model identifier",
    )
    prompt: str = Field(..., min_length=1, max_length=2048)
    num_frames: int = Field(default=14, ge=4, le=60)
    fps: int = Field(default=6, ge=1, le=30)
    min_vram_mb: int = Field(default=8192, ge=2048)


class SubmitTrainingLoraRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    model_id: UUID | None = None
    model_name: str = Field(
        default="Qwen/Qwen2.5-0.5B",
        description="Base Hugging Face model repository name, e.g. 'Qwen/Qwen2.5-0.5B'",
    )
    dataset_id: UUID | None = Field(default=None, description="Optional local dataset ID")
    dataset_name: str = Field(
        default="tatsu-lab/alpaca",
        description="Hugging Face dataset repository name, e.g. 'tatsu-lab/alpaca'",
    )
    num_batches: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Number of distributed batch shards to divide the training into",
    )
    is_distributed: bool = Field(
        default=True,
        description="Whether to partition the dataset into discrete batches for distributed workers",
    )
    lora_r: int = Field(default=16, ge=4, le=128, description="LoRA rank dimension")
    lora_alpha: int = Field(default=32, ge=8, le=256, description="LoRA scaling alpha")
    target_modules: list[str] = Field(
        default_factory=lambda: ["q_proj", "v_proj", "k_proj", "o_proj"]
    )
    epochs: int = Field(default=3, ge=1, le=20)
    learning_rate: float = Field(default=2e-4, gt=0.0, lt=1e-1)
    batch_size: int = Field(default=4, ge=1, le=64)
    min_vram_mb: int = Field(default=4096, ge=1024)


class TrainableBatchResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    batch_id: str
    parent_job_id: str
    model_name: str
    dataset_name: str
    batch_index: int
    total_batches: int
    dataset_slice: str
    status: str  # available, in_progress, completed
    assigned_worker_id: str | None = None
    worker_name: str | None = None
    reward_credits: float = 2.5
    min_vram_mb: int = 4096
    loss: float | None = None


class DistributedTrainingJobResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    model_name: str
    dataset_name: str
    status: str
    num_batches: int
    completed_batches: int
    progress_percent: float
    output_text: str | None = None
    batches: list[TrainableBatchResponse] = Field(default_factory=list)
    created_at: datetime


class ClaimBatchRequest(BaseModel):
    worker_id: UUID


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
    output_text: str | None = None
    execution_metrics: dict[str, Any] | None = None
    events: list[JobEventResponse] = Field(default_factory=list)


class JobListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    jobs: list[JobResponse]
