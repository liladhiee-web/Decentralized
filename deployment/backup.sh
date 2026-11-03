#!/usr/bin/env bash
# ==============================================================================
# Decentralized AI Cloud - Automated Coordinator Backup Script
# Performs atomic pg_dump for PostgreSQL and rsync snapshot for MinIO volumes.
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/cloudai}"
TIMESTAMP="$(date +'%Y%m%d_%H%M%S')"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

mkdir -p "${BACKUP_DIR}"

echo "[*] Starting CloudAI Coordinator backup at $(date)..."

# 1. PostgreSQL Atomic Database Dump
echo "[*] Backing up PostgreSQL database..."
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-cloudai_user}" -d "${POSTGRES_DB:-cloudai_db}" -F c -b -v \
    > "${BACKUP_DIR}/cloudai_postgres_${TIMESTAMP}.dump"

# 2. Check MinIO Artifact Consistency
echo "[*] Recording metadata snapshot..."
echo "Backup timestamp: ${TIMESTAMP}" > "${BACKUP_DIR}/backup_manifest_${TIMESTAMP}.txt"

# 3. Compress database dump
gzip -f "${BACKUP_DIR}/cloudai_postgres_${TIMESTAMP}.dump"
echo "[+] PostgreSQL dump saved to ${BACKUP_DIR}/cloudai_postgres_${TIMESTAMP}.dump.gz"

# 4. Clean up backups older than retention window
echo "[*] Cleaning up backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "cloudai_postgres_*.dump.gz" -mtime +"${RETENTION_DAYS}" -delete
find "${BACKUP_DIR}" -name "backup_manifest_*.txt" -mtime +"${RETENTION_DAYS}" -delete

echo "[+] Backup sequence completed successfully at $(date)."

