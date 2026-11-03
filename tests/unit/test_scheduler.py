"""
Unit tests for the Resource-Aware GPU Scheduler.
"""

import uuid

from coordinator.models.worker import GPUDevice, Worker
from coordinator.scheduler import GPUScheduler
from shared.constants import WorkerStatus


def test_compute_capability_parsing() -> None:
    scheduler = GPUScheduler()
    assert scheduler._parse_compute_capability("8.9") == (8, 9)
    assert scheduler._parse_compute_capability("7.5") == (7, 5)
    assert scheduler._parse_compute_capability("8") == (8, 0)
    assert scheduler._parse_compute_capability("invalid") == (0, 0)


def test_candidate_scoring() -> None:
    scheduler = GPUScheduler()

    worker = Worker(
        id=uuid.uuid4(),
        provider_id=uuid.uuid4(),
        name="worker-alpha",
        hostname="rig-1",
        status=WorkerStatus.IDLE.value,
        auth_token_hash="hash",
        total_jobs_completed=100,
        total_jobs_failed=2,
    )

    gpu_good = GPUDevice(
        id=uuid.uuid4(),
        worker_id=worker.id,
        gpu_index=0,
        name="RTX 4090",
        pci_bus_id="0000:01:00.0",
        total_vram_mb=24576,
        free_vram_mb=24000,
        cuda_compute_capability="8.9",
        driver_version="550.54.14",
        cuda_version="12.4",
        temperature_celsius=45.0,
        power_draw_watts=100.0,
        utilization_gpu_percent=5,
        utilization_mem_percent=10,
        is_available=True,
    )

    gpu_hot_busy = GPUDevice(
        id=uuid.uuid4(),
        worker_id=worker.id,
        gpu_index=1,
        name="RTX 3090",
        pci_bus_id="0000:02:00.0",
        total_vram_mb=24576,
        free_vram_mb=4000,
        cuda_compute_capability="8.6",
        driver_version="550.54.14",
        cuda_version="12.4",
        temperature_celsius=88.0,
        power_draw_watts=350.0,
        utilization_gpu_percent=95,
        utilization_mem_percent=90,
        is_available=True,
    )

    score_good = scheduler._calculate_candidate_score(worker, gpu_good, min_vram_mb=16384)
    score_busy = scheduler._calculate_candidate_score(worker, gpu_hot_busy, min_vram_mb=16384)

    assert score_good > score_busy
    assert score_good > 70.0
    assert score_busy < 50.0
