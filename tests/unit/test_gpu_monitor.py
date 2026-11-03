"""
Unit tests for Worker GPUMonitor and system telemetry collection.
"""

from worker.config import get_worker_settings
from worker.gpu_monitor import GPUMonitor


def test_gpu_monitor_telemetry_collection() -> None:
    """Verify hardware telemetry collection returns valid ranges."""
    monitor = GPUMonitor()
    telemetry = monitor.collect_telemetry()

    assert 0.0 <= telemetry.cpu_utilization_percent <= 100.0
    assert telemetry.ram_total_mb > 0
    assert telemetry.ram_free_mb > 0
    assert telemetry.disk_free_mb > 0


def test_gpu_monitor_simulation_mode() -> None:
    """Verify simulation mode produces structured GPU device telemetry."""
    settings = get_worker_settings()
    settings.SIMULATE_GPU = True

    monitor = GPUMonitor()
    # Force NVML to be inactive to trigger simulation
    monitor.has_nvml = False
    gpus = monitor.collect_gpus()

    assert len(gpus) == 1
    gpu = gpus[0]
    assert "Simulated" in gpu.name
    assert gpu.total_vram_mb == 24576
    assert gpu.free_vram_mb > 20000
    assert gpu.cuda_compute_capability == "8.9"
