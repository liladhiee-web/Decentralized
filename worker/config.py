"""
Worker daemon configuration.
Supports environment variables and local configuration files.
"""

from functools import lru_cache
from pathlib import Path
from uuid import UUID

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Coordinator Connection
    COORDINATOR_URL: str = Field(default="http://localhost:8000")
    COORDINATOR_WS_URL: str | None = None

    # Worker Identity & Credentials
    WORKER_ID: UUID | None = None
    WORKER_TOKEN: str = Field(default="dev_worker_token")
    WORKER_NAME: str = Field(default="community-gpu-node-01")
    CLIENT_VERSION: str = Field(default="0.1.0")

    # Storage & Local Workspaces
    WORK_DIR: Path = Field(default=Path("./workload_tmp"))
    HEARTBEAT_INTERVAL_SECONDS: int = Field(default=15)
    MAX_RECONNECT_DELAY_SECONDS: int = Field(default=60)
    PURGE_MODEL_AFTER_TASK: bool = Field(
        default=True,
        description="Completely delete model weights from GPU VRAM and local disk cache after each task",
    )

    # Docker Sandboxing
    DOCKER_IMAGE: str = Field(default="nvidia/cuda:12.4.1-runtime-ubuntu22.04")
    DOCKER_NETWORK_MODE: str = Field(default="none")  # Strict network isolation for workloads
    SIMULATE_GPU: bool = Field(default=False)  # For test suites / CPU validation

    def get_ws_url(self) -> str:
        """Derive WebSocket endpoint URL from HTTP coordinator URL if not explicitly configured."""
        if self.COORDINATOR_WS_URL:
            return self.COORDINATOR_WS_URL
        base = self.COORDINATOR_URL.rstrip("/")
        if base.startswith("https://"):
            return base.replace("https://", "wss://") + "/ws/workers"
        elif base.startswith("http://"):
            return base.replace("http://", "ws://") + "/ws/workers"
        return f"ws://{base}/ws/workers"


@lru_cache
def get_worker_settings() -> WorkerSettings:
    """Return cached worker daemon settings singleton."""
    return WorkerSettings()
