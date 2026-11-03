"""
Configuration settings for the Decentralized AI Cloud Coordinator.
Powered by Pydantic Settings v2.
"""

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # General Application Settings
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")
    SECRET_KEY: str = Field(
        default="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        description="Master secret key for coordinator cryptography",
    )
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    DEBUG: bool = Field(default=False)

    # CORS
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"]
    )

    # PostgreSQL Database
    POSTGRES_USER: str = Field(default="cloudai_user")
    POSTGRES_PASSWORD: str = Field(default="cloudai_secure_password_replace_in_prod")
    POSTGRES_DB: str = Field(default="cloudai_db")
    POSTGRES_HOST: str = Field(default="postgres")
    POSTGRES_PORT: int = Field(default=5432)
    DATABASE_URL: str | None = None
    DATABASE_POOL_SIZE: int = Field(default=20)
    DATABASE_MAX_OVERFLOW: int = Field(default=10)
    DATABASE_POOL_TIMEOUT: int = Field(default=30)

    # Redis
    REDIS_HOST: str = Field(default="redis")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASSWORD: str = Field(default="cloudai_redis_secure_pass")
    REDIS_DB: int = Field(default=0)
    REDIS_URL: str | None = None

    # MinIO / S3 Object Storage
    MINIO_ENDPOINT: str = Field(default="minio:9000")
    MINIO_PUBLIC_ENDPOINT: str = Field(default="http://localhost:9000")
    MINIO_ROOT_USER: str = Field(default="cloudai_minio_admin")
    MINIO_ROOT_PASSWORD: str = Field(default="cloudai_minio_secret_key_change_me")
    MINIO_SECURE: bool = Field(default=False)
    MINIO_BUCKET_MODELS: str = Field(default="cloudai-models")
    MINIO_BUCKET_DATASETS: str = Field(default="cloudai-datasets")
    MINIO_BUCKET_ARTIFACTS: str = Field(default="cloudai-artifacts")
    MINIO_PRESIGNED_URL_EXPIRY_SECONDS: int = Field(default=3600)

    # Authentication & JWT
    JWT_SECRET_KEY: str = Field(
        default="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    )
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # Worker Protocol & Security
    WORKER_AUTH_TOKEN_SALT: str = Field(default="worker_token_hmac_salt_change_for_prod")
    WORKER_HEARTBEAT_INTERVAL_SECONDS: int = Field(default=15)
    WORKER_HEARTBEAT_TIMEOUT_SECONDS: int = Field(default=60)
    WORKER_MAX_MISSED_HEARTBEATS: int = Field(default=3)

    # Celery Task Queue
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # Limits
    RATE_LIMIT_PER_MINUTE: int = Field(default=120)
    MAX_JOB_EXECUTION_TIME_SECONDS: int = Field(default=86400)
    MAX_UPLOAD_SIZE_BYTES: int = Field(default=107374182400)  # 100 GB

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None, info: Any) -> str:
        if v:
            return v
        data = info.data
        user = data.get("POSTGRES_USER", "cloudai_user")
        pwd = data.get("POSTGRES_PASSWORD", "cloudai_secure_password_replace_in_prod")
        host = data.get("POSTGRES_HOST", "postgres")
        port = data.get("POSTGRES_PORT", 5432)
        db = data.get("POSTGRES_DB", "cloudai_db")
        return f"postgresql+asyncpg://{user}:{pwd}@{host}:{port}/{db}"

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_connection(cls, v: str | None, info: Any) -> str:
        if v:
            return v
        data = info.data
        pwd = data.get("REDIS_PASSWORD", "cloudai_redis_secure_pass")
        host = data.get("REDIS_HOST", "redis")
        port = data.get("REDIS_PORT", 6379)
        db = data.get("REDIS_DB", 0)
        if pwd:
            return f"redis://:{pwd}@{host}:{port}/{db}"
        return f"redis://{host}:{port}/{db}"

    @field_validator("CELERY_BROKER_URL", mode="before")
    @classmethod
    def assemble_celery_broker(cls, v: str | None, info: Any) -> str:
        if v:
            return v
        data = info.data
        pwd = data.get("REDIS_PASSWORD", "cloudai_redis_secure_pass")
        host = data.get("REDIS_HOST", "redis")
        port = data.get("REDIS_PORT", 6379)
        if pwd:
            return f"redis://:{pwd}@{host}:{port}/1"
        return f"redis://{host}:{port}/1"

    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def assemble_celery_backend(cls, v: str | None, info: Any) -> str:
        if v:
            return v
        data = info.data
        pwd = data.get("REDIS_PASSWORD", "cloudai_redis_secure_pass")
        host = data.get("REDIS_HOST", "redis")
        port = data.get("REDIS_PORT", 6379)
        if pwd:
            return f"redis://:{pwd}@{host}:{port}/2"
        return f"redis://{host}:{port}/2"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
