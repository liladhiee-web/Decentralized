"""
Artifact, Model Manifest, and Dataset Catalog Management API Endpoints.
Directs client uploads and downloads via short-lived pre-signed MinIO/S3 URLs.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from coordinator.auth.dependencies import get_api_key_or_user
from coordinator.config import get_settings
from coordinator.database import get_db
from coordinator.models.artifact import Artifact, Dataset, ModelManifest, ModelVersion
from coordinator.models.user import User
from coordinator.schemas.artifacts import (
    ArtifactResponse,
    DatasetCreateRequest,
    DatasetResponse,
    ModelManifestCreateRequest,
    ModelManifestResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
)
from coordinator.storage import get_storage_service
from shared.constants import UserRole

router = APIRouter(prefix="/artifacts", tags=["Models, Datasets & Artifacts"])
settings = get_settings()
storage = get_storage_service()


@router.post("/models", response_model=ModelManifestResponse, status_code=status.HTTP_201_CREATED)
async def create_model_manifest(
    payload: ModelManifestCreateRequest,
    current_user: User = Depends(get_api_key_or_user),
    db: AsyncSession = Depends(get_db),
) -> ModelManifest:
    """Register a new AI model manifest in the platform catalog."""
    existing = await db.execute(select(ModelManifest).where(ModelManifest.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Model manifest name already exists"
        )

    manifest = ModelManifest(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        architecture=payload.architecture,
        framework=payload.framework,
        format=payload.format,
        parameter_count=payload.parameter_count,
        default_vram_required_mb=payload.default_vram_required_mb,
        is_public=payload.is_public,
    )
    db.add(manifest)
    await db.commit()
    await db.refresh(manifest)
    return manifest


@router.get("/models", response_model=list[ModelManifestResponse])
async def list_model_manifests(
    current_user: User = Depends(get_api_key_or_user),
    db: AsyncSession = Depends(get_db),
) -> list[ModelManifest]:
    """List available public models and user-owned model manifests."""
    result = await db.execute(
        select(ModelManifest)
        .where((ModelManifest.is_public == True) | (ModelManifest.user_id == current_user.id))  # noqa: E712
        .order_by(ModelManifest.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/models/{model_id}/upload-url", response_model=PresignedUploadResponse)
async def get_model_upload_url(
    model_id: UUID,
    payload: PresignedUploadRequest,
    current_user: User = Depends(get_api_key_or_user),
    db: AsyncSession = Depends(get_db),
) -> PresignedUploadResponse:
    """Generate a short-lived pre-signed PUT URL for direct-to-S3 model weight uploads."""
    result = await db.execute(select(ModelManifest).where(ModelManifest.id == model_id))
    manifest = result.scalar_one_or_none()
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Model manifest not found"
        )

    if manifest.user_id != current_user.id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    storage_path = f"models/{manifest.name}/{payload.filename}"
    upload_url = storage.generate_presigned_upload_url(
        bucket_name=settings.MINIO_BUCKET_MODELS,
        object_name=storage_path,
        expiry_seconds=3600,
    )

    # Register initial draft version
    version = ModelVersion(
        model_id=manifest.id,
        version_tag="v1.0.0",
        storage_path=storage_path,
        checksum_sha256=payload.checksum_sha256,
        size_bytes=payload.size_bytes,
        is_ready=False,
    )
    db.add(version)
    await db.commit()

    return PresignedUploadResponse(
        upload_url=upload_url,
        storage_path=storage_path,
        expiry_seconds=3600,
    )


@router.post("/datasets", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    payload: DatasetCreateRequest,
    current_user: User = Depends(get_api_key_or_user),
    db: AsyncSession = Depends(get_db),
) -> Dataset:
    """Register a fine-tuning dataset record."""
    storage_path = f"datasets/{current_user.id}/{payload.name}.{payload.format}"
    dataset = Dataset(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        format=payload.format,
        num_records=payload.num_records,
        size_bytes=payload.size_bytes,
        storage_path=storage_path,
        checksum_sha256=payload.checksum_sha256,
        is_validated=False,
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.get("/datasets", response_model=list[DatasetResponse])
async def list_datasets(
    current_user: User = Depends(get_api_key_or_user),
    db: AsyncSession = Depends(get_db),
) -> list[Dataset]:
    """List datasets owned by current user."""
    result = await db.execute(
        select(Dataset)
        .where(Dataset.user_id == current_user.id)
        .order_by(Dataset.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/datasets/{dataset_id}/upload-url", response_model=PresignedUploadResponse)
async def get_dataset_upload_url(
    dataset_id: UUID,
    current_user: User = Depends(get_api_key_or_user),
    db: AsyncSession = Depends(get_db),
) -> PresignedUploadResponse:
    """Generate pre-signed PUT URL for uploading training dataset."""
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    if dataset.user_id != current_user.id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    upload_url = storage.generate_presigned_upload_url(
        bucket_name=settings.MINIO_BUCKET_DATASETS,
        object_name=dataset.storage_path,
        expiry_seconds=3600,
    )

    return PresignedUploadResponse(
        upload_url=upload_url,
        storage_path=dataset.storage_path,
        expiry_seconds=3600,
    )


@router.get("", response_model=list[ArtifactResponse])
async def list_artifacts(
    job_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_api_key_or_user),
    db: AsyncSession = Depends(get_db),
) -> list[ArtifactResponse]:
    """List generated execution artifacts (LoRA adapters, checkpoints, images)."""
    query = select(Artifact)
    if current_user.role != UserRole.ADMIN.value:
        query = query.where(Artifact.user_id == current_user.id)
    if job_id:
        query = query.where(Artifact.job_id == job_id)

    query = query.order_by(Artifact.created_at.desc())
    result = await db.execute(query)
    artifacts = list(result.scalars().all())

    responses: list[ArtifactResponse] = []
    for art in artifacts:
        resp = ArtifactResponse.model_validate(art)
        # Attach signed download URL
        resp.download_url = storage.generate_presigned_download_url(
            bucket_name=settings.MINIO_BUCKET_ARTIFACTS,
            object_name=art.storage_path,
        )
        responses.append(resp)

    return responses


@router.get("/{artifact_id}/download-url")
async def get_artifact_download_url(
    artifact_id: UUID,
    current_user: User = Depends(get_api_key_or_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Generate a time-limited pre-signed download URL for an artifact."""
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")

    if artifact.user_id != current_user.id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    url = storage.generate_presigned_download_url(
        bucket_name=settings.MINIO_BUCKET_ARTIFACTS,
        object_name=artifact.storage_path,
        expiry_seconds=3600,
    )
    return {
        "artifact_id": str(artifact.id),
        "filename": artifact.filename,
        "download_url": url,
        "checksum_sha256": artifact.checksum_sha256,
        "size_bytes": str(artifact.size_bytes),
    }
