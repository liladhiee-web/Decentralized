"""
Pydantic API request and response schemas module.
"""

from coordinator.schemas.artifacts import (
    ArtifactResponse,
    DatasetCreateRequest,
    DatasetResponse,
    ModelManifestCreateRequest,
    ModelManifestResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
)
from coordinator.schemas.auth import (
    APIKeyCreateRequest,
    APIKeyResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from coordinator.schemas.jobs import (
    ClaimBatchRequest,
    DistributedTrainingJobResponse,
    JobDetailResponse,
    JobEventResponse,
    JobListResponse,
    JobResponse,
    SubmitInferenceAudioRequest,
    SubmitInferenceImageRequest,
    SubmitInferenceTextRequest,
    SubmitInferenceVideoRequest,
    SubmitTrainingLoraRequest,
    TrainableBatchResponse,
)
from coordinator.schemas.workers import (
    GPUDeviceResponse,
    WorkerRegisterRequest,
    WorkerRegisterResponse,
    WorkerResponse,
    WorkerStatusUpdateRequest,
)

__all__ = [
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "UserResponse",
    "APIKeyCreateRequest",
    "APIKeyResponse",
    "GPUDeviceResponse",
    "WorkerRegisterRequest",
    "WorkerRegisterResponse",
    "WorkerResponse",
    "WorkerStatusUpdateRequest",
    "SubmitInferenceTextRequest",
    "SubmitInferenceImageRequest",
    "SubmitInferenceAudioRequest",
    "SubmitInferenceVideoRequest",
    "SubmitTrainingLoraRequest",
    "ClaimBatchRequest",
    "DistributedTrainingJobResponse",
    "TrainableBatchResponse",
    "JobResponse",
    "JobDetailResponse",
    "JobListResponse",
    "JobEventResponse",
    "ModelManifestCreateRequest",
    "ModelManifestResponse",
    "DatasetCreateRequest",
    "DatasetResponse",
    "ArtifactResponse",
    "PresignedUploadRequest",
    "PresignedUploadResponse",
]
