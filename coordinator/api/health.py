"""
Health check endpoints for container orchestrators, load balancers, and monitoring.
"""

from typing import Any

from fastapi import APIRouter, Response, status

from coordinator.config import get_settings
from coordinator.database import check_db_health
from coordinator.redis_client import check_redis_health
from coordinator.storage import get_storage_service

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])
settings = get_settings()


@router.get("/live", summary="Coordinator Liveness Probe")
async def liveness_probe() -> dict[str, str]:
    """Lightweight probe indicating the application process is running."""
    return {"status": "alive"}


@router.get("/ready", summary="Coordinator Readiness Probe")
async def readiness_probe(response: Response) -> dict[str, Any]:
    """
    Readiness probe verifying all dependent backends (Postgres, Redis, MinIO)
    are reachable before routing user/worker traffic.
    """
    db_status = await check_db_health()
    redis_status = await check_redis_health()

    storage_service = get_storage_service()
    storage_status = storage_service.check_health()

    is_ready = bool(
        db_status.get("connected")
        and redis_status.get("connected")
        and storage_status.get("connected")
    )

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "ready": is_ready,
        "database": db_status.get("connected", False),
        "redis": redis_status.get("connected", False),
        "storage": storage_status.get("connected", False),
    }


@router.get("", summary="Detailed Subsystem Diagnostics")
async def detailed_health(response: Response) -> dict[str, Any]:
    """
    Detailed health report including latencies, version information,
    and subsystem diagnostic states.
    """
    db_status = await check_db_health()
    redis_status = await check_redis_health()

    storage_service = get_storage_service()
    storage_status = storage_service.check_health()

    is_healthy = bool(
        db_status.get("status") == "healthy"
        and redis_status.get("status") == "healthy"
        and storage_status.get("status") == "healthy"
    )

    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if is_healthy else "degraded",
        "service": "decentralized-ai-cloud-coordinator",
        "environment": settings.ENVIRONMENT,
        "subsystems": {
            "postgresql": db_status,
            "redis": redis_status,
            "minio": storage_status,
        },
    }
