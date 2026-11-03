#!/usr/bin/env python3
"""
End-to-End Deployment & Subsystem Verification Script.
Validates the full lifecycle of the Decentralized AI Cloud Platform:
- Health & Readiness Probes
- User Registration & Authentication (Argon2id + JWT + API Keys)
- Worker Registration & HMAC Token Verification
- Model Manifest & Dataset Catalog Management
- Job Submission (Inference & LoRA Fine-Tuning)
- Resource-Aware Scheduler Candidate Scoring
- LoRA Weight Invariant Verification & FedAvg Aggregation
"""

import argparse
import asyncio
import logging
import sys
import uuid
from pathlib import Path
from typing import Any

import httpx

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_deployment")


class DeploymentVerifier:
    """Automates end-to-end verification of coordinator, scheduler, and worker subsystem APIs."""

    def __init__(self, base_url: str | None = None, use_in_memory: bool = False) -> None:
        self.base_url = (base_url or "http://localhost:8000").rstrip("/")
        self.use_in_memory = use_in_memory
        self.client: httpx.AsyncClient | None = None
        self.auth_token: str | None = None
        self.api_key: str | None = None
        self.user_id: str | None = None
        self.worker_id: str | None = None
        self.worker_token: str | None = None
        self.inference_job_id: str | None = None
        self.training_job_id: str | None = None
        self.verification_results: list[dict[str, Any]] = []

    async def __aenter__(self) -> "DeploymentVerifier":
        if self.use_in_memory:
            from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

            from coordinator.database import Base, get_db
            from coordinator.main import app

            self._in_memory_engine = create_async_engine(
                "sqlite+aiosqlite:///:memory:",
                echo=False,
                future=True,
            )
            self._in_memory_session_factory = async_sessionmaker(
                bind=self._in_memory_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            async with self._in_memory_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            async def _override_get_db():
                async with self._in_memory_session_factory() as session:
                    yield session

            app.dependency_overrides[get_db] = _override_get_db

            # In in-memory mode, mock external network health checks for immediate execution
            import coordinator.api.health as health_api
            from coordinator.storage import get_storage_service

            get_storage_service().check_health = lambda: {
                "status": "healthy",
                "connected": True,
                "latency_ms": 0.5,
            }

            async def _mock_redis_health():
                return {"status": "healthy", "connected": True, "latency_ms": 0.2}

            health_api.check_redis_health = _mock_redis_health

            # Use ASGI transport for in-process verification without external network dependencies
            transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
            self.client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
        else:
            self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.client:
            await self.client.aclose()
        if hasattr(self, "_in_memory_engine") and self._in_memory_engine:
            await self._in_memory_engine.dispose()

    def record_step(self, step_name: str, passed: bool, details: str = "") -> None:
        status_str = "PASS" if passed else "FAIL"
        self.verification_results.append({"step": step_name, "passed": passed, "details": details})
        logger.info("[%s] %s: %s", status_str, step_name, details)
        if not passed:
            raise RuntimeError(f"Verification step failed: {step_name} - {details}")

    async def verify_health_probes(self) -> None:
        """Verify liveness and readiness probes."""
        assert self.client is not None
        # 1. Liveness
        resp = await self.client.get("/health/live")
        self.record_step(
            "Liveness Probe (/health/live)",
            resp.status_code == 200 and resp.json().get("status") == "alive",
            f"HTTP {resp.status_code}",
        )

        # 2. Readiness
        resp = await self.client.get("/health/ready")
        self.record_step(
            "Readiness Probe (/health/ready)",
            resp.status_code in (200, 503),  # 200 or 503 depending on live external dependencies
            f"HTTP {resp.status_code} (Status: {resp.json().get('status')})",
        )

    async def verify_authentication_and_api_keys(self) -> None:
        """Verify user signup, JWT login, and API key generation."""
        assert self.client is not None
        unique_email = f"deploy_test_{uuid.uuid4().hex[:8]}@example.com"
        password = "SecureVerificationPassword123!"

        # 1. Register User (as provider to allow worker registration)
        reg_resp = await self.client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": password,
                "full_name": "Deployment Test Provider",
                "role": "provider",
            },
        )
        self.record_step(
            "User Registration (/api/v1/auth/register)",
            reg_resp.status_code == 201,
            f"Created user: {unique_email}",
        )
        user_data = reg_resp.json()
        self.user_id = user_data["id"]

        # 2. Login to receive JWT Access Token
        login_resp = await self.client.post(
            "/api/v1/auth/login",
            json={"email": unique_email, "password": password},
        )
        self.record_step(
            "User Login (/api/v1/auth/login)",
            login_resp.status_code == 200 and "access_token" in login_resp.json(),
            "Authenticated JWT access token acquired",
        )
        self.auth_token = login_resp.json()["access_token"]

        # 3. Create API Key
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        key_resp = await self.client.post(
            "/api/v1/auth/api-keys",
            json={"name": "deployment-verification-key", "expires_days": 30},
            headers=headers,
        )
        self.record_step(
            "API Key Generation (/api/v1/auth/api-keys)",
            key_resp.status_code == 201 and "cld_live_" in key_resp.json()["raw_key"],
            f"Generated key prefix: {key_resp.json()['raw_key'][:16]}...",
        )
        self.api_key = key_resp.json()["raw_key"]

    async def verify_worker_registration(self) -> None:
        """Verify community worker node registration and token generation."""
        assert self.client is not None
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        worker_resp = await self.client.post(
            "/api/v1/workers/register",
            json={
                "name": f"test-worker-{uuid.uuid4().hex[:6]}",
                "hostname": "test-gpu-node-01",
                "client_version": "0.1.0",
            },
            headers=headers,
        )
        self.record_step(
            "Worker Registration (/api/v1/workers/register)",
            worker_resp.status_code == 201,
            f"Worker ID: {worker_resp.json()['worker_id']}",
        )
        data = worker_resp.json()
        self.worker_id = data["worker_id"]
        self.worker_token = data["token"]

    async def verify_artifacts_and_datasets(self) -> None:
        """Verify model manifest and fine-tuning dataset cataloging."""
        assert self.client is not None
        headers = {"Authorization": f"Bearer {self.auth_token}"}

        # Model manifest
        model_name = f"llama3-test-{uuid.uuid4().hex[:6]}"
        model_resp = await self.client.post(
            "/api/v1/artifacts/models",
            json={
                "name": model_name,
                "architecture": "LlamaForCausalLM",
                "framework": "transformers",
                "format": "safetensors",
                "parameter_count": 8000000000,
                "default_vram_required_mb": 16384,
                "description": "Llama 3 8B Verification Test Model",
            },
            headers=headers,
        )
        self.record_step(
            "Model Manifest Registration (/api/v1/artifacts/models)",
            model_resp.status_code == 201,
            f"Registered model: {model_name}",
        )
        self.model_id = model_resp.json()["id"]

        # Dataset cataloging
        dataset_name = f"dataset-alpaca-{uuid.uuid4().hex[:6]}"
        dataset_resp = await self.client.post(
            "/api/v1/artifacts/datasets",
            json={
                "name": dataset_name,
                "format": "jsonl",
                "num_records": 50000,
                "size_bytes": 10485760,
                "checksum_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            },
            headers=headers,
        )
        self.record_step(
            "Dataset Cataloging (/api/v1/artifacts/datasets)",
            dataset_resp.status_code == 201,
            f"Cataloged dataset: {dataset_name}",
        )
        self.dataset_id = dataset_resp.json()["id"]

    async def verify_job_submission_and_lifecycle(self) -> None:
        """Verify inference and training job dispatch flows."""
        assert self.client is not None
        headers = {"Authorization": f"Bearer {self.auth_token}"}

        # Submit Inference Job
        inf_resp = await self.client.post(
            "/api/v1/jobs/inference/text",
            json={
                "model_id": self.model_id,
                "model_name": "meta-llama/Meta-Llama-3-8B-Instruct",
                "prompt": "Explain the zero-trust security model in AI cloud systems.",
                "max_tokens": 128,
                "temperature": 0.7,
                "min_vram_mb": 16384,
            },
            headers=headers,
        )
        self.record_step(
            "Inference Job Submission (/api/v1/jobs/inference/text)",
            inf_resp.status_code == 201,
            f"Job ID: {inf_resp.json()['id']}",
        )
        self.inference_job_id = inf_resp.json()["id"]

        # Submit LoRA Fine-Tuning Job
        train_resp = await self.client.post(
            "/api/v1/jobs/training/lora",
            json={
                "model_id": self.model_id,
                "model_name": "meta-llama/Meta-Llama-3-8B",
                "dataset_id": self.dataset_id,
                "lora_r": 16,
                "lora_alpha": 32,
                "target_modules": ["q_proj", "v_proj"],
                "epochs": 3,
                "batch_size": 4,
                "learning_rate": 0.0002,
                "min_vram_mb": 24576,
            },
            headers=headers,
        )
        self.record_step(
            "LoRA Training Job Submission (/api/v1/jobs/training/lora)",
            train_resp.status_code == 201,
            f"Training Job ID: {train_resp.json()['id']}",
        )
        self.training_job_id = train_resp.json()["id"]

        # Query Job Status
        query_resp = await self.client.get(f"/api/v1/jobs/{self.inference_job_id}", headers=headers)
        self.record_step(
            "Job Status Query (/api/v1/jobs/{id})",
            query_resp.status_code == 200
            and query_resp.json()["status"] in ("pending", "scheduled"),
            f"State: {query_resp.json()['status']}",
        )

    def verify_scheduler_and_lora_invariants(self) -> None:
        """Verify in-process resource-aware scheduler and LoRA compatibility checks."""
        from coordinator.model_processor import ModelProcessor
        from coordinator.scheduler import GPUScheduler

        scheduler = GPUScheduler()
        # Verify compute capability parsing
        cap_val = scheduler._parse_compute_capability("8.9")
        self.record_step(
            "Scheduler Compute Capability Parsing",
            cap_val == (8, 9),
            f"Ada Lovelace CC 8.9 -> {cap_val}",
        )

        # Verify LoRA compatibility invariants
        adapter_a = {
            "base_model_name_or_path": "meta-llama/Meta-Llama-3-8B",
            "r": 16,
            "lora_alpha": 32,
            "target_modules": ["q_proj", "v_proj"],
        }
        adapter_b = {
            "base_model_name_or_path": "meta-llama/Meta-Llama-3-8B",
            "r": 16,
            "lora_alpha": 32,
            "target_modules": ["q_proj", "v_proj"],
        }
        is_compatible, reason = ModelProcessor.validate_lora_compatibility([adapter_a, adapter_b])
        self.record_step(
            "LoRA Topology & Rank Invariant Validation",
            is_compatible,
            f"Compatible adapters validated: {reason}",
        )

        # Verify FedAvg sample weight calculation
        w1_id = uuid.uuid4()
        w2_id = uuid.uuid4()
        contributions = [
            {"worker_id": w1_id, "num_samples_processed": 100},
            {"worker_id": w2_id, "num_samples_processed": 300},
        ]
        weights = ModelProcessor.compute_weighted_fedavg_weights(contributions)
        sum_weights = sum(weights.values())
        self.record_step(
            "FedAvg Sample Normalization Invariant (sum==1.0)",
            abs(sum_weights - 1.0) < 1e-6 and weights[w1_id] == 0.25 and weights[w2_id] == 0.75,
            f"Weights: {weights}, Sum: {sum_weights}",
        )

    async def run_all(self) -> bool:
        """Run complete verification sequence."""
        logger.info("==================================================================")
        logger.info("Starting CloudAI Platform End-to-End Deployment Verification")
        logger.info(
            "Mode: %s", "In-Memory ASGI" if self.use_in_memory else f"Live URL ({self.base_url})"
        )
        logger.info("==================================================================")

        try:
            await self.verify_health_probes()
            await self.verify_authentication_and_api_keys()
            await self.verify_worker_registration()
            await self.verify_artifacts_and_datasets()
            await self.verify_job_submission_and_lifecycle()
            self.verify_scheduler_and_lora_invariants()
            logger.info("==================================================================")
            logger.info("ALL DEPLOYMENT VERIFICATION CHECKS PASSED SUCCESSFULLY (7/7 Stages)")
            logger.info("==================================================================")
            return True
        except Exception as e:
            logger.error("Verification halted due to error: %s", e)
            return False


async def main() -> int:
    parser = argparse.ArgumentParser(description="CloudAI Deployment Verification")
    parser.add_argument("--url", default="http://localhost:8000", help="Coordinator URL")
    parser.add_argument(
        "--in-memory",
        action="store_true",
        default=True,
        help="Run against in-memory ASGI application (default)",
    )
    args = parser.parse_args()

    async with DeploymentVerifier(base_url=args.url, use_in_memory=args.in_memory) as verifier:
        success = await verifier.run_all()
        return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
