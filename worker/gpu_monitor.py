"""
Hardware Resource and GPU Telemetry Monitor.
Interrogates NVIDIA GPUs via pynvml and host metrics via psutil.
"""

import logging
import shutil
from pathlib import Path

import psutil
import pynvml

from shared.schemas import GPUInfo, SystemTelemetry
from worker.config import get_worker_settings

logger = logging.getLogger(__name__)


class GPUMonitor:
    """Collects real-time hardware telemetry and GPU metrics."""

    def __init__(self) -> None:
        self.settings = get_worker_settings()
        self.has_nvml = False
        self._init_nvml()

    def _init_nvml(self) -> None:
        """Attempt to initialize the NVIDIA Management Library."""
        try:
            pynvml.nvmlInit()
            self.has_nvml = True
            count = pynvml.nvmlDeviceGetCount()
            logger.info("NVML initialized successfully. Detected %d physical GPU(s).", count)
        except Exception as e:
            self.has_nvml = False
            logger.warning("NVML unavailable (%s). GPU monitoring disabled or simulated.", e)

    def shutdown(self) -> None:
        """Clean up NVML handles on shutdown."""
        if self.has_nvml:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass

    def collect_gpus(self) -> list[GPUInfo]:
        """Query all physical NVIDIA GPUs attached to this host."""
        gpus: list[GPUInfo] = []

        if not self.has_nvml:
            if self.settings.SIMULATE_GPU:
                # Return simulated GPU device for local testing and CI
                gpus.append(
                    GPUInfo(
                        index=0,
                        name="Simulated NVIDIA RTX 4090",
                        pci_bus_id="0000:01:00.0",
                        total_vram_mb=24576,
                        free_vram_mb=23000,
                        cuda_compute_capability="8.9",
                        driver_version="550.54.14",
                        cuda_version="12.4",
                        temperature_celsius=45.0,
                        power_draw_watts=75.0,
                        utilization_gpu_percent=10,
                        utilization_mem_percent=15,
                        is_available=True,
                    )
                )
            return gpus

        try:
            count = pynvml.nvmlDeviceGetCount()
            driver_version = pynvml.nvmlSystemGetDriverVersion()
            if isinstance(driver_version, bytes):
                driver_version = driver_version.decode("utf-8")

            cuda_driver_ver_raw = pynvml.nvmlSystemGetCudaDriverVersion()
            cuda_ver_str = f"{cuda_driver_ver_raw // 1000}.{(cuda_driver_ver_raw % 1000) // 10}"

            for idx in range(count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(idx)

                # Name
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode("utf-8")

                # Memory
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                total_vram_mb = int(mem_info.total / (1024 * 1024))
                free_vram_mb = int(mem_info.free / (1024 * 1024))

                # PCI Info
                pci_info = pynvml.nvmlDeviceGetPciInfo(handle)
                pci_bus = pci_info.busId
                if isinstance(pci_bus, bytes):
                    pci_bus = pci_bus.decode("utf-8")

                # Compute Capability
                major, minor = pynvml.nvmlDeviceGetCudaComputeCapability(handle)
                compute_cap = f"{major}.{minor}"

                # Temperature
                try:
                    temp = float(
                        pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    )
                except Exception:
                    temp = 0.0

                # Power
                try:
                    power = float(
                        pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
                    )  # milliwatts to watts
                except Exception:
                    power = 0.0

                # Utilization
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    util_gpu = int(util.gpu)
                    util_mem = int(util.memory)
                except Exception:
                    util_gpu = 0
                    util_mem = 0

                gpus.append(
                    GPUInfo(
                        index=idx,
                        name=name,
                        pci_bus_id=pci_bus,
                        total_vram_mb=total_vram_mb,
                        free_vram_mb=free_vram_mb,
                        cuda_compute_capability=compute_cap,
                        driver_version=str(driver_version),
                        cuda_version=cuda_ver_str,
                        temperature_celsius=temp,
                        power_draw_watts=power,
                        utilization_gpu_percent=util_gpu,
                        utilization_mem_percent=util_mem,
                        is_available=True,
                    )
                )
        except Exception as e:
            logger.error("Error collecting GPU telemetry: %s", e)

        return gpus

    def collect_telemetry(self) -> SystemTelemetry:
        """Capture a complete snapshot of host CPU, RAM, disk, and GPU metrics."""
        cpu_pct = psutil.cpu_percent(interval=0.1)
        vmem = psutil.virtual_memory()
        ram_total_mb = int(vmem.total / (1024 * 1024))
        ram_free_mb = int(vmem.available / (1024 * 1024))

        work_dir = Path(self.settings.WORK_DIR)
        work_dir.mkdir(parents=True, exist_ok=True)
        disk_usage = shutil.disk_usage(work_dir)
        disk_free_mb = int(disk_usage.free / (1024 * 1024))

        gpus = self.collect_gpus()

        return SystemTelemetry(
            cpu_utilization_percent=cpu_pct,
            ram_total_mb=ram_total_mb,
            ram_free_mb=ram_free_mb,
            disk_free_mb=disk_free_mb,
            gpus=gpus,
        )


# Singleton
gpu_monitor = GPUMonitor()


def get_gpu_monitor() -> GPUMonitor:
    """Return GPUMonitor singleton instance."""
    return gpu_monitor
