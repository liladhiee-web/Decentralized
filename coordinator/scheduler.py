"""
Resource-Aware GPU Scheduler.
Evaluates hardware specifications, memory headroom, compute capabilities,
and historical reliability scores to match workloads to optimal community compute nodes.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from coordinator.config import get_settings
from coordinator.models.worker import GPUDevice, Worker
from shared.constants import WorkerStatus

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class SchedulingDecision:
    """Represents the scheduling result matching a job to an optimal worker and GPU."""

    worker_id: UUID
    gpu_device_id: UUID
    worker_name: str
    gpu_name: str
    allocated_vram_mb: int
    score: float
    estimated_cost_credits: float
    metadata: dict[str, Any] = field(default_factory=dict)


class GPUScheduler:
    """
    Intelligent scheduler routing inference and fine-tuning workloads
    across third-party community GPU providers.
    """

    def __init__(self) -> None:
        self.heartbeat_timeout = settings.WORKER_HEARTBEAT_TIMEOUT_SECONDS

    def _parse_compute_capability(self, cap_str: str) -> tuple[int, int]:
        """Convert '8.9' into (8, 9) for numerical comparison."""
        try:
            parts = cap_str.strip().split(".")
            return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        except Exception:
            return (0, 0)

    def _calculate_candidate_score(
        self,
        worker: Worker,
        gpu: GPUDevice,
        min_vram_mb: int,
        model_name: str | None = None,
    ) -> float:
        """
        Calculate composite suitability score for a worker-GPU candidate:
        Score = w_vram * (free_vram / total_vram)
              + w_util * (1.0 - gpu_utilization / 100)
              + w_rel * reliability_ratio
              + w_temp * (1.0 - temp / 100)
        """
        # 1. VRAM headroom ratio
        vram_ratio = min(1.0, max(0.0, gpu.free_vram_mb / max(1, gpu.total_vram_mb)))

        # 2. GPU core utilization (lower is better)
        util_ratio = 1.0 - min(1.0, max(0.0, gpu.utilization_gpu_percent / 100.0))

        # 3. Historical reliability: completed / (completed + failed + 1)
        total_attempts = worker.total_jobs_completed + worker.total_jobs_failed
        reliability = (worker.total_jobs_completed + 1.0) / (total_attempts + 2.0)

        # 4. Thermal headroom (penalize GPUs running above 80°C)
        temp_ratio = 1.0 - min(1.0, max(0.0, gpu.temperature_celsius / 100.0))

        # 5. Strong preference for completely free (IDLE) nodes over busy ones
        status_bonus = 50.0 if worker.status == WorkerStatus.IDLE.value else 0.0

        # Composite weighted sum
        score = (
            (0.35 * vram_ratio) + (0.30 * util_ratio) + (0.25 * reliability) + (0.10 * temp_ratio)
        ) * 100.0 + status_bonus

        return round(score, 2)

    async def select_worker_for_inference(
        self,
        db: AsyncSession,
        min_vram_mb: int = 8192,
        min_cuda_compute: str = "7.0",
        model_name: str | None = None,
    ) -> SchedulingDecision | None:
        """
        Match an inference request to a single optimal GPU worker.
        Filters by:
        - Worker status (IDLE or BUSY with multi-GPU capacity)
        - Active heartbeat within threshold
        - Free VRAM >= required VRAM
        - CUDA compute capability >= required capability
        """
        now = datetime.now(UTC)
        liveness_threshold = now - timedelta(seconds=self.heartbeat_timeout)
        target_compute = self._parse_compute_capability(min_cuda_compute)

        # Query all live workers with their GPU devices eager-loaded
        query = (
            select(Worker)
            .where(
                Worker.status.in_([WorkerStatus.IDLE.value, WorkerStatus.BUSY.value]),
                Worker.last_heartbeat_at >= liveness_threshold,
            )
            .options(selectinload(Worker.gpu_devices))
        )

        result = await db.execute(query)
        candidates = result.scalars().all()

        # Always prioritize free/idle workers over busy ones.
        # Single-GPU nodes currently in a work job are excluded if a free node is ready.
        idle_candidates = [w for w in candidates if w.status == WorkerStatus.IDLE.value]
        candidate_pool = (
            idle_candidates
            if idle_candidates
            else [w for w in candidates if len(w.gpu_devices) > 1]
        )

        best_decision: SchedulingDecision | None = None
        highest_score = -1.0

        for worker in candidate_pool:
            for gpu in worker.gpu_devices:
                if not gpu.is_available:
                    continue

                if gpu.free_vram_mb < min_vram_mb:
                    continue

                gpu_compute = self._parse_compute_capability(gpu.cuda_compute_capability)
                if gpu_compute < target_compute:
                    continue

                score = self._calculate_candidate_score(worker, gpu, min_vram_mb, model_name)

                if score > highest_score:
                    highest_score = score
                    # Estimated execution cost: base 0.05 credits + 0.01 per GB VRAM allocated
                    estimated_cost = round(0.05 + (min_vram_mb / 1024.0) * 0.005, 4)
                    best_decision = SchedulingDecision(
                        worker_id=worker.id,
                        gpu_device_id=gpu.id,
                        worker_name=worker.name,
                        gpu_name=gpu.name,
                        allocated_vram_mb=min_vram_mb,
                        score=score,
                        estimated_cost_credits=estimated_cost,
                        metadata={
                            "total_vram_mb": gpu.total_vram_mb,
                            "free_vram_mb": gpu.free_vram_mb,
                            "temperature_celsius": gpu.temperature_celsius,
                            "cuda_compute_capability": gpu.cuda_compute_capability,
                        },
                    )

        if best_decision:
            logger.info(
                "Scheduled job to worker '%s' (GPU %s) with score %.2f",
                best_decision.worker_name,
                best_decision.gpu_name,
                best_decision.score,
            )
        else:
            logger.warning(
                "No eligible worker found for requirements: min_vram=%d MB, min_compute=%s",
                min_vram_mb,
                min_cuda_compute,
            )

        return best_decision

    async def select_cohort_for_federated_training(
        self,
        db: AsyncSession,
        target_count: int = 3,
        min_vram_mb: int = 16384,
        min_cuda_compute: str = "7.5",
    ) -> list[SchedulingDecision]:
        """
        Select a cohort of compatible, heterogeneous workers for a federated LoRA round.
        Ensures hardware capability compatibility without requiring low-latency synchronous networking.
        """
        now = datetime.now(UTC)
        liveness_threshold = now - timedelta(seconds=self.heartbeat_timeout)
        target_compute = self._parse_compute_capability(min_cuda_compute)

        query = (
            select(Worker)
            .where(
                Worker.status.in_([WorkerStatus.IDLE.value, WorkerStatus.BUSY.value]),
                Worker.last_heartbeat_at >= liveness_threshold,
            )
            .options(selectinload(Worker.gpu_devices))
        )

        result = await db.execute(query)
        candidates = result.scalars().all()

        scored_candidates: list[SchedulingDecision] = []

        for worker in candidates:
            # Pick the best GPU on each worker
            best_gpu_on_worker: GPUDevice | None = None
            best_score_on_worker = -1.0

            for gpu in worker.gpu_devices:
                if not gpu.is_available or gpu.free_vram_mb < min_vram_mb:
                    continue
                if self._parse_compute_capability(gpu.cuda_compute_capability) < target_compute:
                    continue

                score = self._calculate_candidate_score(worker, gpu, min_vram_mb)
                if score > best_score_on_worker:
                    best_score_on_worker = score
                    best_gpu_on_worker = gpu

            if best_gpu_on_worker:
                decision = SchedulingDecision(
                    worker_id=worker.id,
                    gpu_device_id=best_gpu_on_worker.id,
                    worker_name=worker.name,
                    gpu_name=best_gpu_on_worker.name,
                    allocated_vram_mb=min_vram_mb,
                    score=best_score_on_worker,
                    estimated_cost_credits=round(0.20 + (min_vram_mb / 1024.0) * 0.01, 4),
                    metadata={
                        "cuda_capability": best_gpu_on_worker.cuda_compute_capability,
                        "free_vram_mb": best_gpu_on_worker.free_vram_mb,
                    },
                )
                scored_candidates.append(decision)

        # Sort descending by score and pick top K
        scored_candidates.sort(key=lambda d: d.score, reverse=True)
        return scored_candidates[:target_count]


# Scheduler singleton
scheduler = GPUScheduler()


def get_scheduler() -> GPUScheduler:
    """Return scheduler singleton instance."""
    return scheduler
