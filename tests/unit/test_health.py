"""
Unit tests for Coordinator Health probes, root endpoints, and protocol envelopes.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from coordinator.main import app
from shared.constants import WebSocketMessageType
from shared.protocol import (
    WorkerAuthMessage,
)
from shared.schemas import GPUInfo, SystemTelemetry


@pytest.mark.asyncio
async def test_root_endpoint() -> None:
    """Verify discovery endpoint returns valid JSON platform metadata."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["platform"] == "Decentralized Community AI Compute Cloud"
        assert data["role"] == "Central Coordinator"
        assert data["version"] == "0.1.0"
        assert "X-Process-Time-Ms" in response.headers


@pytest.mark.asyncio
async def test_liveness_probe() -> None:
    """Verify liveness probe responds with 200 and alive status."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "alive"}


def test_shared_protocol_serialization() -> None:
    """Verify WebSocket protocol models serialize and deserialize correctly."""
    gpu = GPUInfo(
        index=0,
        name="NVIDIA RTX 4090",
        pci_bus_id="0000:01:00.0",
        total_vram_mb=24576,
        free_vram_mb=24000,
        cuda_compute_capability="8.9",
        driver_version="550.54.14",
        cuda_version="12.4",
        temperature_celsius=42.0,
        power_draw_watts=75.5,
        utilization_gpu_percent=5,
        utilization_mem_percent=10,
        is_available=True,
    )

    telemetry = SystemTelemetry(
        cpu_utilization_percent=12.5,
        ram_total_mb=65536,
        ram_free_mb=52000,
        disk_free_mb=500000,
        gpus=[gpu],
    )

    import uuid

    worker_id = uuid.uuid4()
    auth_msg = WorkerAuthMessage(
        worker_id=worker_id,
        token="test_token_hash",
        hostname="rig-alpha-01",
        client_version="0.1.0",
        telemetry=telemetry,
    )

    raw_json = auth_msg.model_dump_json()
    assert "rig-alpha-01" in raw_json
    assert "NVIDIA RTX 4090" in raw_json

    parsed = WorkerAuthMessage.model_validate_json(raw_json)
    assert parsed.type == WebSocketMessageType.WORKER_AUTH
    assert parsed.worker_id == worker_id
    assert len(parsed.telemetry.gpus) == 1
    assert parsed.telemetry.gpus[0].total_vram_mb == 24576
