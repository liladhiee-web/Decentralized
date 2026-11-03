"""Initial database schema with core models

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-11-03 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("balance_credits", sa.Numeric(precision=14, scale=4), nullable=False, server_default="0.0000"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 2. api_keys
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("prefix", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_api_keys_id", "api_keys", ["id"], unique=False)
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"], unique=False)
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)

    # 3. workers
    op.create_table(
        "workers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="offline"),
        sa.Column("auth_token_hash", sa.String(length=255), nullable=False),
        sa.Column("public_key", sa.String(length=1024), nullable=True),
        sa.Column("client_version", sa.String(length=64), nullable=False, server_default="0.1.0"),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_jobs_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_jobs_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_workers_id", "workers", ["id"], unique=False)
    op.create_index("ix_workers_provider_id", "workers", ["provider_id"], unique=False)
    op.create_index("ix_workers_status", "workers", ["status"], unique=False)
    op.create_index("ix_workers_last_heartbeat_at", "workers", ["last_heartbeat_at"], unique=False)

    # 4. gpu_devices
    op.create_table(
        "gpu_devices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gpu_index", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("pci_bus_id", sa.String(length=64), nullable=False),
        sa.Column("total_vram_mb", sa.Integer(), nullable=False),
        sa.Column("free_vram_mb", sa.Integer(), nullable=False),
        sa.Column("cuda_compute_capability", sa.String(length=16), nullable=False),
        sa.Column("driver_version", sa.String(length=64), nullable=False),
        sa.Column("cuda_version", sa.String(length=32), nullable=False),
        sa.Column("temperature_celsius", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("power_draw_watts", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("utilization_gpu_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("utilization_mem_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_gpu_devices_id", "gpu_devices", ["id"], unique=False)
    op.create_index("ix_gpu_devices_worker_id", "gpu_devices", ["worker_id"], unique=False)

    # 5. worker_heartbeats
    op.create_table(
        "worker_heartbeats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cpu_utilization_percent", sa.Float(), nullable=False),
        sa.Column("ram_total_mb", sa.Integer(), nullable=False),
        sa.Column("ram_free_mb", sa.Integer(), nullable=False),
        sa.Column("disk_free_mb", sa.Integer(), nullable=False),
        sa.Column("gpu_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_worker_heartbeats_id", "worker_heartbeats", ["id"], unique=False)
    op.create_index("ix_worker_heartbeats_worker_id", "worker_heartbeats", ["worker_id"], unique=False)
    op.create_index("ix_worker_heartbeats_timestamp", "worker_heartbeats", ["timestamp"], unique=False)

    # 6. model_manifests
    op.create_table(
        "model_manifests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("architecture", sa.String(length=64), nullable=False),
        sa.Column("framework", sa.String(length=32), nullable=False, server_default="transformers"),
        sa.Column("format", sa.String(length=32), nullable=False, server_default="safetensors"),
        sa.Column("parameter_count", sa.BigInteger(), nullable=True),
        sa.Column("default_vram_required_mb", sa.Integer(), nullable=False, server_default="16384"),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_model_manifests_id", "model_manifests", ["id"], unique=False)
    op.create_index("ix_model_manifests_user_id", "model_manifests", ["user_id"], unique=False)
    op.create_index("ix_model_manifests_name", "model_manifests", ["name"], unique=True)

    # 7. model_versions
    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_manifests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_tag", sa.String(length=32), nullable=False, server_default="v1.0.0"),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("tensor_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("is_ready", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_model_versions_id", "model_versions", ["id"], unique=False)
    op.create_index("ix_model_versions_model_id", "model_versions", ["model_id"], unique=False)

    # 8. datasets
    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("format", sa.String(length=32), nullable=False, server_default="jsonl"),
        sa.Column("num_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("is_validated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_datasets_id", "datasets", ["id"], unique=False)
    op.create_index("ix_datasets_user_id", "datasets", ["user_id"], unique=False)
    op.create_index("ix_datasets_name", "datasets", ["name"], unique=False)

    # 9. jobs
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_worker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False, server_default="inference_text"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_manifests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("input_parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("resource_requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("execution_cost_credits", sa.Numeric(precision=14, scale=4), nullable=False, server_default="0.0000"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_jobs_id", "jobs", ["id"], unique=False)
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"], unique=False)
    op.create_index("ix_jobs_assigned_worker_id", "jobs", ["assigned_worker_id"], unique=False)
    op.create_index("ix_jobs_type", "jobs", ["type"], unique=False)
    op.create_index("ix_jobs_status", "jobs", ["status"], unique=False)
    op.create_index("ix_jobs_priority", "jobs", ["priority"], unique=False)
    op.create_index("ix_jobs_model_id", "jobs", ["model_id"], unique=False)
    op.create_index("ix_jobs_dataset_id", "jobs", ["dataset_id"], unique=False)

    # 10. job_attempts
    op.create_table(
        "job_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_job_attempts_id", "job_attempts", ["id"], unique=False)
    op.create_index("ix_job_attempts_job_id", "job_attempts", ["job_id"], unique=False)
    op.create_index("ix_job_attempts_worker_id", "job_attempts", ["worker_id"], unique=False)

    # 11. job_events
    op.create_table(
        "job_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_job_events_id", "job_events", ["id"], unique=False)
    op.create_index("ix_job_events_job_id", "job_events", ["job_id"], unique=False)
    op.create_index("ix_job_events_event_type", "job_events", ["event_type"], unique=False)
    op.create_index("ix_job_events_timestamp", "job_events", ["timestamp"], unique=False)

    # 12. artifacts
    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_type", sa.String(length=32), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False, server_default="application/octet-stream"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_artifacts_id", "artifacts", ["id"], unique=False)
    op.create_index("ix_artifacts_job_id", "artifacts", ["job_id"], unique=False)
    op.create_index("ix_artifacts_user_id", "artifacts", ["user_id"], unique=False)
    op.create_index("ix_artifacts_artifact_type", "artifacts", ["artifact_type"], unique=False)

    # 13. training_rounds
    op.create_table(
        "training_rounds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("target_loss", sa.Float(), nullable=True),
        sa.Column("achieved_loss", sa.Float(), nullable=True),
        sa.Column("aggregate_storage_path", sa.String(length=512), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_training_rounds_id", "training_rounds", ["id"], unique=False)
    op.create_index("ix_training_rounds_job_id", "training_rounds", ["job_id"], unique=False)

    # 14. worker_contributions
    op.create_table(
        "worker_contributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("round_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("training_rounds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("num_samples_processed", sa.Integer(), nullable=False),
        sa.Column("delta_weight_storage_path", sa.String(length=512), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("is_accepted", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("validation_loss", sa.Float(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_worker_contributions_id", "worker_contributions", ["id"], unique=False)
    op.create_index("ix_worker_contributions_round_id", "worker_contributions", ["round_id"], unique=False)
    op.create_index("ix_worker_contributions_worker_id", "worker_contributions", ["worker_id"], unique=False)

    # 15. usage_records
    op.create_table(
        "usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gpu_seconds", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("vram_allocated_mb", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("billed_amount", sa.Numeric(precision=14, scale=4), nullable=False, server_default="0.0000"),
        sa.Column("provider_payout_amount", sa.Numeric(precision=14, scale=4), nullable=False, server_default="0.0000"),
        sa.Column("billing_status", sa.String(length=32), nullable=False, server_default="settled"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_usage_records_id", "usage_records", ["id"], unique=False)
    op.create_index("ix_usage_records_user_id", "usage_records", ["user_id"], unique=False)
    op.create_index("ix_usage_records_worker_id", "usage_records", ["worker_id"], unique=False)
    op.create_index("ix_usage_records_job_id", "usage_records", ["job_id"], unique=False)
    op.create_index("ix_usage_records_recorded_at", "usage_records", ["recorded_at"], unique=False)


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("usage_records")
    op.drop_table("worker_contributions")
    op.drop_table("training_rounds")
    op.drop_table("artifacts")
    op.drop_table("job_events")
    op.drop_table("job_attempts")
    op.drop_table("jobs")
    op.drop_table("datasets")
    op.drop_table("model_versions")
    op.drop_table("model_manifests")
    op.drop_table("worker_heartbeats")
    op.drop_table("gpu_devices")
    op.drop_table("workers")
    op.drop_table("api_keys")
    op.drop_table("users")

