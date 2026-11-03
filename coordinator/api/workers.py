"""
GPU Compute Worker Management and Marketplace Endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from coordinator.auth.dependencies import (
    get_api_key_or_user,
    get_current_active_user,
    get_optional_user,
    get_user_or_demo,
)
from coordinator.auth.security import generate_worker_token
from coordinator.config import get_settings
from coordinator.database import get_db
from coordinator.models.user import User
from coordinator.models.worker import Worker
from coordinator.schemas.workers import (
    WorkerRegisterRequest,
    WorkerRegisterResponse,
    WorkerResponse,
    WorkerStatusUpdateRequest,
)
from shared.constants import UserRole, WorkerStatus

router = APIRouter(prefix="/workers", tags=["GPU Workers & Compute Marketplace"])
settings = get_settings()


@router.post(
    "/register",
    response_model=WorkerRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new GPU Worker node",
)
async def register_worker(
    payload: WorkerRegisterRequest,
    request: Request,
    current_user: User = Depends(get_user_or_demo),
    db: AsyncSession = Depends(get_db),
) -> WorkerRegisterResponse:
    """Register a new community compute worker.

    Generates a cryptographically secure worker secret token.
    The raw token is returned exactly once and must be configured on the worker daemon.
    """
    raw_token, token_hash = generate_worker_token()

    worker = Worker(
        provider_id=current_user.id,
        name=payload.name,
        hostname=payload.hostname,
        status=WorkerStatus.OFFLINE.value,
        auth_token_hash=token_hash,
        public_key=payload.public_key,
        client_version=payload.client_version,
    )
    db.add(worker)
    await db.commit()
    await db.refresh(worker)

    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    forwarded_proto = request.headers.get("x-forwarded-proto") or request.url.scheme
    if forwarded_host:
        ws_proto = "wss" if forwarded_proto == "https" else "ws"
        ws_url = f"{ws_proto}://{forwarded_host}/ws/workers"
        base_url = f"{forwarded_proto}://{forwarded_host}"
    else:
        ws_scheme = "wss" if settings.ENVIRONMENT == "production" else "ws"
        ws_url = f"{ws_scheme}://{settings.HOST}:{settings.PORT}/ws/workers"
        base_url = f"http://{settings.HOST}:{settings.PORT}"

    install_cmd = (
        f"curl -fsSL {base_url}/deployment/install.sh | "
        f"bash -s -- --token {raw_token} --coordinator {base_url}"
    )

    return WorkerRegisterResponse(
        worker_id=worker.id,
        name=worker.name,
        token=raw_token,
        websocket_url=ws_url,
        install_command=install_cmd,
    )


@router.get("", response_model=list[WorkerResponse], summary="List GPU Workers")
async def list_workers(
    status_filter: WorkerStatus | None = Query(default=None, alias="status"),
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> list[Worker]:
    """List all registered GPU workers and their hardware specifications."""
    query = (
        select(Worker).options(selectinload(Worker.gpu_devices)).order_by(Worker.created_at.desc())
    )
    if status_filter:
        query = query.where(Worker.status == status_filter.value)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{worker_id}", response_model=WorkerResponse, summary="Get Worker Details")
async def get_worker_details(
    worker_id: UUID,
    current_user: User = Depends(get_api_key_or_user),
    db: AsyncSession = Depends(get_db),
) -> Worker:
    """Retrieve detailed hardware telemetry and GPU metrics for a specific worker."""
    result = await db.execute(
        select(Worker).where(Worker.id == worker_id).options(selectinload(Worker.gpu_devices))
    )
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")
    return worker


@router.put("/{worker_id}/status", response_model=WorkerResponse, summary="Update Worker Status")
async def update_worker_status(
    worker_id: UUID,
    payload: WorkerStatusUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Worker:
    """Change worker status (e.g. set to 'draining' to gracefully complete existing jobs without new dispatches)."""
    result = await db.execute(
        select(Worker).where(Worker.id == worker_id).options(selectinload(Worker.gpu_devices))
    )
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")

    # Only worker provider or admin can alter state
    if worker.provider_id != current_user.id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage this worker",
        )

    worker.status = payload.status.value
    await db.commit()
    await db.refresh(worker)
    return worker


@router.delete("/{worker_id}", status_code=status.HTTP_204_NO_CONTENT, summary="De-register Worker")
async def delete_worker(
    worker_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke worker authorization and remove from cluster inventory."""
    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")

    if worker.provider_id != current_user.id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    await db.delete(worker)
    await db.commit()
