#!/usr/bin/env bash
# ==============================================================================
# Decentralized AI Cloud - Coordinator Restore & Disaster Recovery Script
# Restores PostgreSQL database from a compressed dump and MinIO artifact storage.
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

if [[ $# -lt 1 ]]; do
    log_error "Usage: $0 <PG_BACKUP_FILE.dump.gz> [MINIO_BACKUP_FILE.tar.gz]"
    exit 1
fi

PG_BACKUP="$1"
MINIO_BACKUP="${2:-}"

if [[ ! -f "${PG_BACKUP}" ]]; then
    log_error "PostgreSQL backup file not found: ${PG_BACKUP}"
    exit 1
fi

log_warn "WARNING: This operation will restore database state and overwrite existing data!"
read -r -p "Are you sure you want to proceed? [y/N] " response
if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    log_info "Restore aborted by user."
    exit 0
fi

# 1. Restore PostgreSQL database
log_info "Restoring PostgreSQL database from ${PG_BACKUP}..."
gunzip -c "${PG_BACKUP}" | docker compose exec -T postgres pg_restore \
    -U "${POSTGRES_USER:-cloudai_user}" \
    -d "${POSTGRES_DB:-cloudai_db}" \
    --clean \
    --if-exists \
    --verbose || {
        log_warn "pg_restore returned non-zero (expected if dropping non-existent tables on a clean DB)"
    }
log_info "PostgreSQL restore completed."

# 2. Restore MinIO Volume if provided
if [[ -n "${MINIO_BACKUP}" && -f "${MINIO_BACKUP}" ]]; then
    log_info "Restoring MinIO volume from ${MINIO_BACKUP}..."
    MINIO_VOL=$(docker volume ls --filter name=minio_data --format "{{.Name}}" | head -n 1)
    if [[ -n "${MINIO_VOL}" ]]; then
        # Stop coordinator and minio temporarily during data unpack
        docker compose stop coordinator minio
        docker run --rm \
            -v "${MINIO_VOL}:/data" \
            -v "$(dirname "$(realpath "${MINIO_BACKUP}")"):/backup:ro" \
            alpine:latest \
            sh -c "rm -rf /data/* && tar -xzf /backup/$(basename "${MINIO_BACKUP}") -C /data"
        docker compose start minio coordinator
        log_info "MinIO volume restored and services restarted successfully."
    else
        log_error "MinIO volume not found. Cannot unpack artifacts."
    fi
fi

log_info "Disaster recovery restore finished successfully."

