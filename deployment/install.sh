#!/usr/bin/env bash
# ==============================================================================
# Decentralized AI Compute Cloud - Community GPU Worker Installation Script
# ==============================================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

COORDINATOR_URL="http://localhost:8000"
WORKER_TOKEN=""
INSTALL_DIR="/opt/cloudai-worker"
SERVICE_NAME="cloudai-worker"
SOURCE_DIR=""
REPO_URL="https://github.com/liladhiee-web/Decentralized.git"

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --token)
            WORKER_TOKEN="$2"
            shift 2
            ;;
        --coordinator)
            COORDINATOR_URL="$2"
            shift 2
            ;;
        --dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --source)
            SOURCE_DIR="$2"
            shift 2
            ;;
        --repo)
            REPO_URL="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Usage: $0 --token <WORKER_REGISTRATION_TOKEN> [--coordinator <URL>] [--dir <PATH>] [--source <PATH>] [--repo <GIT_URL>]"
            exit 1
            ;;
    esac
done

if [[ -z "$WORKER_TOKEN" ]]; then
    log_error "Missing required argument: --token <WORKER_REGISTRATION_TOKEN>"
    exit 1
fi

log_info "Verifying hardware and software prerequisites..."

# 1. Verify NVIDIA Driver & GPU presence
if ! command -v nvidia-smi &> /dev/null; then
    log_error "NVIDIA GPU driver ('nvidia-smi') not found. Please install NVIDIA proprietary drivers first."
    exit 1
fi

GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1)
log_info "Detected GPU: ${GPU_NAME}"

# 2. Verify Docker Engine
if ! command -v docker &> /dev/null; then
    log_error "Docker Engine is not installed. Please install Docker Engine before continuing."
    exit 1
fi

# 3. Verify NVIDIA Container Toolkit
if ! docker info 2>/dev/null | grep -i "Runtimes:.*nvidia" &> /dev/null; then
    log_warn "NVIDIA Container Toolkit runtime not explicitly listed in docker info."
    log_warn "Ensure 'nvidia-container-toolkit' is installed and configured in /etc/docker/daemon.json."
fi

# 4. Verify Python 3.11+
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is required. Please install python3 (>=3.11)."
    exit 1
fi

log_info "Creating worker daemon directory at ${INSTALL_DIR}..."
sudo mkdir -p "${INSTALL_DIR}"
sudo chown -R "$(id -u):$(id -g)" "${INSTALL_DIR}"

log_info "Setting up isolated Python virtual environment..."
python3 -m venv "${INSTALL_DIR}/venv"
"${INSTALL_DIR}/venv/bin/pip" install --no-cache-dir --upgrade pip setuptools wheel
"${INSTALL_DIR}/venv/bin/pip" install --no-cache-dir \
    "pynvml>=11.5.0" \
    "docker>=7.1.0" \
    "httpx>=0.27.0" \
    "websockets>=12.0" \
    "pydantic>=2.8.0" \
    "rich>=13.7.0" \
    "typer>=0.12.0"

log_info "Installing worker package and modules..."
if [[ -n "${SOURCE_DIR}" && -d "${SOURCE_DIR}/worker" ]]; then
    log_info "Copying modules from specified source directory: ${SOURCE_DIR}"
    cp -r "${SOURCE_DIR}/worker" "${INSTALL_DIR}/"
    cp -r "${SOURCE_DIR}/shared" "${INSTALL_DIR}/"
elif [[ -d "./worker" && -d "./shared" ]]; then
    log_info "Copying modules from current working directory..."
    cp -r "./worker" "${INSTALL_DIR}/"
    cp -r "./shared" "${INSTALL_DIR}/"
else
    log_info "Fetching latest codebase from repository: ${REPO_URL}..."
    TEMP_CLONE=$(mktemp -d)
    git clone --depth 1 "${REPO_URL}" "${TEMP_CLONE}"
    cp -r "${TEMP_CLONE}/worker" "${INSTALL_DIR}/"
    cp -r "${TEMP_CLONE}/shared" "${INSTALL_DIR}/"
    rm -rf "${TEMP_CLONE}"
fi

# Generate local worker configuration file
log_info "Writing worker daemon configuration..."
cat <<EOF > "${INSTALL_DIR}/worker.conf"
COORDINATOR_URL=${COORDINATOR_URL}
WORKER_TOKEN=${WORKER_TOKEN}
LOG_LEVEL=INFO
HEARTBEAT_INTERVAL=15
EOF

chmod 600 "${INSTALL_DIR}/worker.conf"

# Generate systemd service unit
log_info "Configuring systemd service '${SERVICE_NAME}'..."
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null <<EOF
[Unit]
Description=Decentralized AI Cloud Community Worker Daemon
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=${INSTALL_DIR}
EnvironmentFile=${INSTALL_DIR}/worker.conf
ExecStart=${INSTALL_DIR}/venv/bin/python -m worker.agent
Restart=always
RestartSec=10
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}"

log_info "Worker installation completed successfully."
log_info "To start the worker daemon immediately, run:"
log_info "  sudo systemctl start ${SERVICE_NAME}"
log_info "To inspect logs:"
log_info "  journalctl -u ${SERVICE_NAME} -f"

