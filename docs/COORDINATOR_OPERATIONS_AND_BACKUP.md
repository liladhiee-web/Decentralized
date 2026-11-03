# Central Coordinator Operations, Backup & Disaster Recovery Runbook

This document details production operations for the Central Coordinator VPS, including cluster lifecycle, database migrations, automated backup scheduling, disaster recovery, and operational monitoring.

---

## 1. Coordinator Production Architecture

The Coordinator is deployed on a dedicated Linux VPS with the following specifications:
- **Processor:** 8 vCPU (AMD EPYC or Intel Xeon)
- **RAM:** 32 GB DDR4/DDR5 ECC RAM
- **Storage:** 1 TB NVMe SSD (high IOPS for PostgreSQL and MinIO metadata)
- **Network:** 1 Gbps port with public IPv4 address
- **OS:** Ubuntu 22.04 / 24.04 LTS or Debian 12

```text
Host VPS (8 vCPU / 32 GB RAM)
├── Caddy (Edge Proxy: 80/443, Automatic TLS)
├── FastAPI Coordinator (4 uvicorn workers, :8000)
├── Celery Worker & Beat (Background dispatch & heartbeat sweep)
├── PostgreSQL 16 (State Store, 4 GB shared buffers)
├── Redis 7 (Queues, rate limiting, and ephemeral state, 1 GB cache)
└── MinIO S3 (Model weight storage & pre-signed URL generator)
```

> **Invariant:** The coordinator has no GPU and never loads model weight tensors into memory. All large file transfers stream directly between MinIO and workers.

---

## 2. Cluster Lifecycle & Deployment

### Initial Launch:

```bash
# 1. Clone repository and set up environment
cp .env.example .env
# Edit .env with strong production passwords and secrets

# 2. Build and launch containers
docker compose up -d --build

# 3. Apply database migrations
docker compose exec coordinator alembic upgrade head
```

### Applying Schema Migrations:

When updating models or deploying new schema versions:

```bash
# Check current migration revision
docker compose exec coordinator alembic current

# Upgrade to latest revision
docker compose exec coordinator alembic upgrade head
```

---

## 3. Automated Backups (`deployment/backup.sh`)

The platform includes an automated backup script that captures:
1. **PostgreSQL Database:** Atomic `pg_dump` in custom binary format, compressed with gzip.
2. **MinIO Object Storage:** A tarball snapshot of the `minio_data` volume containing model manifests, datasets, and LoRA adapters.
3. **Manifest:** Timestamped audit file recording backup metadata.

### Manual Backup Run:

```bash
sudo bash deployment/backup.sh
```

### Scheduled Daily Cron:

Add a cron entry under `/etc/cron.d/cloudai-backup`:

```cron
# Run daily coordinator backup at 02:00 UTC
0 2 * * * root /path/to/decentralized-ai-cloud/deployment/backup.sh >> /var/log/cloudai_backup.log 2>&1
```

By default, backups are stored in `/var/backups/cloudai` with a 14-day rolling retention policy.

---

## 4. Disaster Recovery & Restoration (`deployment/restore.sh`)

In the event of database corruption, hardware failure, or migration rollback, restore the coordinator using `deployment/restore.sh`:

```bash
# Syntax:
# sudo bash deployment/restore.sh <PG_DUMP_GZ> [MINIO_TAR_GZ]

# Example:
sudo bash deployment/restore.sh \
  /var/backups/cloudai/cloudai_postgres_20261103_020000.dump.gz \
  /var/backups/cloudai/cloudai_minio_20261103_020000.tar.gz
```

The restore script:
1. Prompts for confirmation before modifying state.
2. Uncompresses and pipes the SQL dump to `pg_restore --clean --if-exists`.
3. Pauses Coordinator and MinIO services temporarily.
4. Restores the MinIO data volume and restarts the stack cleanly.

---

## 5. Health Monitoring & Observability

The coordinator exposes three standardized HTTP health endpoints:

### Liveness Probe (`GET /health/live`)
- **Purpose:** Verifies that the FastAPI process is responsive.
- **Used by:** Docker Compose healthcheck and Kubernetes liveness probes.
- **Response:** HTTP 200 `{"status": "alive"}`.

### Readiness Probe (`GET /health/ready`)
- **Purpose:** Verifies that dependent upstream systems (PostgreSQL, Redis, MinIO) are accepting connections.
- **Used by:** Load balancers and Caddy reverse proxy before routing user traffic.
- **Response:** HTTP 200 `{"status": "ready"}` or HTTP 503 if any dependency is degraded.

### Deep Subsystem Diagnostic (`GET /health`)
- **Purpose:** Detailed latency and operational metrics for each subsystem.
- **Response Example:**
  ```json
  {
    "status": "healthy",
    "service": "decentralized-ai-cloud-coordinator",
    "environment": "production",
    "subsystems": {
      "postgresql": { "status": "healthy", "connected": true, "latency_ms": 1.12 },
      "redis": { "status": "healthy", "connected": true, "latency_ms": 0.65 },
      "minio": { "status": "healthy", "connected": true, "latency_ms": 2.40 }
    }
  }
  ```

