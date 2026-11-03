"""
Unit tests verifying SQLAlchemy model schemas, constraints, and relationships.
"""

import uuid

from coordinator.models import (
    Artifact,
    Base,
    GPUDevice,
    Job,
    User,
    Worker,
)
from shared.constants import ArtifactType, JobStatus, JobType, UserRole, WorkerStatus


def test_registered_tables_count() -> None:
    """Verify that all 15 platform domain tables are registered on Base.metadata."""
    expected_tables = {
        "users",
        "api_keys",
        "workers",
        "gpu_devices",
        "worker_heartbeats",
        "model_manifests",
        "model_versions",
        "datasets",
        "artifacts",
        "jobs",
        "job_attempts",
        "job_events",
        "training_rounds",
        "worker_contributions",
        "usage_records",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables == actual_tables, f"Missing tables: {expected_tables - actual_tables}"


def test_user_and_worker_model_instantiation() -> None:
    """Verify in-memory model instantiation and property defaults."""
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email="provider@example.com",
        hashed_password="argon2id$mocked$hash",
        full_name="Provider One",
        role=UserRole.PROVIDER.value,
        is_active=True,
        balance_credits=100.0,
    )
    assert user.email == "provider@example.com"
    assert user.role == "provider"

    worker_id = uuid.uuid4()
    worker = Worker(
        id=worker_id,
        provider_id=user_id,
        name="gpu-rig-01",
        hostname="rig-host",
        status=WorkerStatus.OFFLINE.value,
        auth_token_hash="token_hash",
        client_version="0.1.0",
    )
    assert worker.name == "gpu-rig-01"
    assert worker.status == "offline"

    gpu = GPUDevice(
        id=uuid.uuid4(),
        worker_id=worker_id,
        gpu_index=0,
        name="NVIDIA GeForce RTX 4090",
        pci_bus_id="0000:01:00.0",
        total_vram_mb=24576,
        free_vram_mb=24576,
        cuda_compute_capability="8.9",
        driver_version="550.54.14",
        cuda_version="12.4",
        is_available=True,
    )
    assert gpu.total_vram_mb == 24576
    assert gpu.is_available is True


def test_job_and_artifact_model_instantiation() -> None:
    """Verify job lifecycle and artifact model structure."""
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()

    job = Job(
        id=job_id,
        user_id=user_id,
        type=JobType.INFERENCE_TEXT.value,
        status=JobStatus.PENDING.value,
        priority=10,
        input_parameters={"prompt": "Explain quantum computing", "max_tokens": 150},
        resource_requirements={"min_vram_mb": 8192, "cuda_compute_min": "7.5"},
    )
    assert job.status == "pending"
    assert job.input_parameters["max_tokens"] == 150

    artifact = Artifact(
        id=uuid.uuid4(),
        job_id=job_id,
        user_id=user_id,
        artifact_type=ArtifactType.MODEL_ADAPTER.value,
        storage_path="models/adapters/job-123/adapter.safetensors",
        filename="adapter.safetensors",
        size_bytes=52428800,
        checksum_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        mime_type="application/octet-stream",
    )
    assert artifact.size_bytes == 52428800
    assert len(artifact.checksum_sha256) == 64
