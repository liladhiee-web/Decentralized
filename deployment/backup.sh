#!/usr/bin/env bash
# ==============================================================================
# Decentralized AI Cloud - Automated Coordinator Backup Script
# Performs atomic pg_dump for PostgreSQL and tar snapshot for MinIO object storage.
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/cloudai}"
TIMESTAMP="$(date +'%Y%m%d_%H%M%S')"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
COMPOSE_PROJECT="${COMPOSE_PROJECT:-gooys}"

mkdir -p "${BACKUP_DIR}"

echo "[*] Starting CloudAI Coordinator backup at $(date)..."

# 1. PostgreSQL Atomic Database Dump
echo "[*] Backing up PostgreSQL database..."
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-cloudai_user}" -d "${POSTGRES_DB:-cloudai_db}" -F c -b -v \
    > "${BACKUP_DIR}/cloudai_postgres_${TIMESTAMP}.dump"
gzip -f "${BACKUP_DIR}/cloudai_postgres_${TIMESTAMP}.dump"
echo "[+] PostgreSQL dump saved to ${BACKUP_DIR}/cloudai_postgres_${TIMESTAMP}.dump.gz"

# 2. MinIO S3 Object Storage Snapshot
echo "[*] Creating snapshot of MinIO storage volume..."
# Determine volume name (project_minio_data or minio_data)
MINIO_VOL=$(docker volume ls --filter name=minio_data --format "{{.Name}}" | head -n 1)
if [[ -n "${MINIO_VOL}" ]]; then
    docker run --rm \
        -v "${MINIO_VOL}:/data:ro" \
        -v "${BACKUP_DIR}:/backup" \
        alpine:latest \
        tar -czf "/backup/cloudai_minio_${TIMESTAMP}.tar.gz" -C /data .
    echo "[+] MinIO storage snapshot saved to ${BACKUP_DIR}/cloudai_minio_${TIMESTAMP}.tar.gz"
else
    echo "[!] MinIO volume not found; skipping MinIO storage snapshot"
fi

# 3. Write metadata snapshot manifest
echo "[*] Recording metadata snapshot manifest..."
cat <<EOF > "${BACKUP_DIR}/backup_manifest_${TIMESTAMP}.txt"
CloudAI Backup Manifest
Timestamp: ${TIMESTAMP}
PostgreSQL Backup: cloudai_postgres_${TIMESTAMP}.dump.gz
MinIO Volume Backup: cloudai_minio_${TIMESTAMP}.tar.gz
Docker Compose Project: ${COMPOSE_PROJECT}
PostgreSQL Database: ${POSTGRES_DB:-cloudai_db}
EOF

# 4. Clean up backups older than retention window
echo "[*] Cleaning up backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "cloudai_postgres_*.dump.gz" -mtime +"${RETENTION_DAYS}" -delete
find "${BACKUP_DIR}" -name "cloudai_minio_*.tar.gz" -mtime +"${RETENTION_DAYS}" -delete
find "${BACKUP_DIR}" -name "backup_manifest_*.txt" -mtime +"${RETENTION_DAYS}" -delete

echo "[+] Backup sequence completed successfully at $(date)."

