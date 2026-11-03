"""
Coordinator REST API module.
"""

from coordinator.api.artifacts import router as artifacts_router
from coordinator.api.auth import router as auth_router
from coordinator.api.health import router as health_router
from coordinator.api.jobs import router as jobs_router
from coordinator.api.workers import router as workers_router

__all__ = [
    "health_router",
    "auth_router",
    "workers_router",
    "jobs_router",
    "artifacts_router",
]
