"""
Decentralized Community AI Compute Cloud - Central Coordinator Application.
Main FastAPI entrypoint providing REST endpoints, WebSocket gateways, and lifecycle orchestration.
"""

import logging
import sys
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from coordinator.api.artifacts import router as artifacts_router
from coordinator.api.auth import router as auth_router
from coordinator.api.health import router as health_router
from coordinator.api.jobs import router as jobs_router
from coordinator.api.workers import router as workers_router
from coordinator.config import get_settings
from coordinator.database import close_db_connections
from coordinator.storage import get_storage_service
from coordinator.websocket.router import router as ws_router

settings = get_settings()

# Configure structured application logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("coordinator")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifecycle manager. Initializes connections, verifies storage
    buckets, and disposes of resources gracefully on shutdown.
    """
    logger.info("Initializing Decentralized AI Cloud Coordinator...")
    logger.info("Operating Environment: %s", settings.ENVIRONMENT)

    # Initialize MinIO Storage Buckets
    try:
        storage = get_storage_service()
        storage.ensure_buckets_exist()
        logger.info("MinIO storage buckets verified.")
    except Exception as exc:
        logger.warning(
            "MinIO bucket initialization deferred (storage offline during startup): %s", exc
        )

    logger.info("Coordinator startup sequence complete. Ready for traffic.")

    yield

    # Teardown
    logger.info("Shutting down Coordinator, releasing database and network pools...")
    await close_db_connections()
    logger.info("Coordinator shutdown complete.")


# Initialize FastAPI Application
app = FastAPI(
    title="Decentralized AI Cloud Coordinator API",
    description=(
        "Central coordinator orchestrating community-powered third-party GPU compute "
        "for secure AI inference and distributed LoRA fine-tuning."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Cross-Origin Resource Sharing (CORS) Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request Processing Timing Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next) -> Response:
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
    return response


# Global Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Unprocessable Entity",
            "message": "Input validation failed",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled server exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred while processing your request.",
        },
    )


# Include API & WebSocket Routers
app.include_router(health_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(workers_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(artifacts_router, prefix="/api/v1")
app.include_router(ws_router)


@app.get("/", tags=["Root"])
async def root_info() -> dict[str, str]:
    """Root platform discovery endpoint."""
    return {
        "platform": "Decentralized Community AI Compute Cloud",
        "role": "Central Coordinator",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
        "api_v1": "/api/v1",
        "ws_workers": "/ws/workers",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "coordinator.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
